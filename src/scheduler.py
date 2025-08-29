import asyncio
import json
from datetime import datetime
from typing import List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import config
from database import db
from marzban_api import marzban_api
from backup_manager import BackupManager
from models.schemas import UsageReportModel, LogModel, LimitCheckResult
from utils.notify import notify_limit_warning, notify_limit_exceeded

class MonitoringScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.backup_manager = BackupManager()

    async def check_admin_limits(self, admin_user_id: int) -> LimitCheckResult:
        admin = await db.get_admin(admin_user_id)
        if not admin:
            return LimitCheckResult(admin_user_id=admin_user_id)
        return await self.check_admin_limits_by_id(admin.id)

    async def check_admin_limits_by_id(self, admin_id: int) -> LimitCheckResult:
        try:
            admin = await db.get_admin_by_id(admin_id)
            if not admin or not admin.is_active:
                return LimitCheckResult(admin_user_id=admin.user_id if admin else 0)

            admin_username = admin.marzban_username or admin.username or str(admin.user_id)
            admin_stats = await marzban_api.get_admin_stats(admin_username)

            created_at = admin.created_at
            now = datetime.utcnow()
            elapsed_seconds = (now - created_at).total_seconds()

            time_percentage = elapsed_seconds / admin.max_total_time if admin.max_total_time > 0 else 0
            user_percentage = (admin_stats.total_users / admin.max_users) if admin.max_users > 0 else 0
            traffic_percentage = (admin_stats.total_traffic_used / admin.max_total_traffic) if admin.max_total_traffic > 0 else 0

            limits_exceeded = (
                time_percentage >= 1.0 or
                user_percentage >= 1.0 or
                traffic_percentage >= 1.0
            )
            warning_levels = [0.6, 0.7, 0.8, 0.9]
            warning_needed = any([
                any(level <= time_percentage < 1.0 for level in warning_levels),
                any(level <= user_percentage < 1.0 for level in warning_levels),
                any(level <= traffic_percentage < 1.0 for level in warning_levels)
            ])

            report = UsageReportModel(
                admin_user_id=admin.user_id,
                check_time=now,
                current_users=admin_stats.total_users,
                current_total_time=int(elapsed_seconds),
                current_total_traffic=int(admin_stats.total_traffic_used),
                users_data=json.dumps([], ensure_ascii=False)
            )
            await db.add_usage_report(report)

            return LimitCheckResult(
                admin_user_id=admin.user_id,
                admin_id=admin.id,
                exceeded=limits_exceeded,
                warning=warning_needed,
                limits_data={
                    "user_percentage": user_percentage,
                    "traffic_percentage": traffic_percentage,
                    "time_percentage": time_percentage,
                    "current_users": admin_stats.total_users,
                    "max_users": admin.max_users,
                    "current_traffic": 0,
                    "max_traffic": admin.max_total_traffic,
                    "current_time": elapsed_seconds,
                    "max_time": admin.max_total_time
                }
            )
        except Exception as e:
            print(f"Error checking admin limits: {e}")
            return LimitCheckResult(admin_user_id=admin.user_id if admin else 0)

    async def cleanup_expired_users(self):
        try:
            total_cleaned = 0
            admins = await db.get_all_admins()
            for admin in admins:
                if not admin.is_active:
                    continue
                admin_username = admin.marzban_username or admin.username or str(admin.user_id)
                try:
                    users = await marzban_api.get_users(admin_username)
                    for user in users:
                        try:
                            success = await marzban_api.remove_user(user.username)
                            if success:
                                total_cleaned += 1
                                print(f"Removed expired user: {user.username} (admin: {admin_username})")
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"Error removing expired user {user.username}: {e}")
                            continue
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Error cleaning expired users for admin {admin.user_id}: {e}")
                    continue

            if total_cleaned > 0:
                log = LogModel(
                    admin_user_id=None,
                    action="expired_users_cleanup",
                    details=f"Automatically cleaned up {total_cleaned} expired users",
                    timestamp=datetime.now()
                )
                await db.add_log(log)

            print(f"Expired users cleanup completed. Removed {total_cleaned} users at {datetime.now()}")
        except Exception as e:
            print(f"Error in cleanup_expired_users: {e}")

    async def run_auto_backup(self):
        """Run automatic backup based on BACKUP_INTERVAL."""
        try:
            print(f"Running auto backup at {datetime.now()}")
            success, message = self.backup_manager.create_backup(is_cron=True)
            if success:
                log = LogModel(
                    admin_user_id=None,
                    action="auto_backup",
                    details=f"Auto backup created: {message}",
                    timestamp=datetime.now()
                )
                await db.add_log(log)
                if config.TELEGRAM_ADMIN_CHAT_ID:
                    await self.bot.send_message(
                        config.TELEGRAM_ADMIN_CHAT_ID,
                        config.MESSAGES["backup_success"].format(filename=message)
                    )
            else:
                print(f"Auto backup failed: {message}")
        except Exception as e:
            print(f"Error in auto backup: {e}")

    async def monitor_all_admins(self):
        try:
            print(f"Starting monitoring check at {datetime.now()}")
            if config.AUTO_DELETE_EXPIRED_USERS:
                await self.cleanup_expired_users()
            admins = await db.get_all_admins()
            active_admins = [admin for admin in admins if admin.is_active]

            if not active_admins:
                print("No active admins to monitor")
                return

            print(f"Monitoring {len(active_admins)} active admins")
            for admin in admins:
                try:
                    result = await self.check_admin_limits_by_id(admin.id)
                    if result.exceeded:
                        await self.handle_limit_exceeded(result)
                    elif result.warning:
                        await self.handle_limit_warning(result)
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"Error monitoring admin panel {admin.id} (user {admin.user_id}): {e}")
                    continue

            print(f"Monitoring check completed at {datetime.now()}")
        except Exception as e:
            print(f"Error in monitor_all_admins: {e}")

    async def handle_limit_warning(self, result: LimitCheckResult):
        try:
            admin = await db.get_admin_by_id(result.admin_id)
            if not admin:
                return
            message = config.MESSAGES["limit_warning"].format(
                percent=int(max(result.limits_data["user_percentage"], result.limits_data["traffic_percentage"], result.limits_data["time_percentage"]) * 100)
            )
            await self.bot.send_message(admin.user_id, message)
        except Exception as e:
            print(f"Error sending limit warning: {e}")

    async def handle_limit_exceeded(self, result: LimitCheckResult):
        try:
            admin = await db.get_admin_by_id(result.admin_id)
            if not admin:
                return
            await self.bot.send_message(admin.user_id, config.MESSAGES["limit_exceeded"])
        except Exception as e:
            print(f"Error sending limit exceeded message: {e}")

    async def start(self):
        if self.is_running:
            print("Scheduler is already running")
            return

        print("Starting monitoring scheduler...")

        self.scheduler.add_job(
            self.monitor_all_admins,
            trigger=IntervalTrigger(seconds=config.MONITORING_INTERVAL),
            id="admin_monitor",
            name="Admin Limit Monitor",
            replace_existing=True,
            max_instances=1
        )

        # Add auto backup job based on BACKUP_INTERVAL
        cron_expression = {
            "daily": "0 0 * * *",  # Every day at midnight
            "weekly": "0 0 * * 0",  # Every Sunday at midnight
            "monthly": "0 0 1 * *"  # First day of every month at midnight
        }.get(config.BACKUP_INTERVAL, "0 0 * * *")

        self.scheduler.add_job(
            self.run_auto_backup,
            trigger=CronTrigger.from_crontab(cron_expression),
            id="auto_backup",
            name="Auto Backup",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        self.is_running = True
        print(f"Scheduler started. Monitoring every {config.MONITORING_INTERVAL} seconds, Backup: {config.BACKUP_INTERVAL}.")

        await self.monitor_all_admins()
        await self.run_auto_backup()

    async def stop(self):
        if not self.is_running:
            return
        print("Stopping scheduler...")
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        print("Scheduler stopped.")

    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "jobs": len(self.scheduler.get_jobs()) if self.is_running else 0,
            "next_monitor_run": str(self.scheduler.get_job("admin_monitor").next_run_time) if self.is_running else None,
            "next_backup_run": str(self.scheduler.get_job("auto_backup").next_run_time) if self.is_running else None
        }

def init_scheduler(bot):
    global scheduler
    scheduler = MonitoringScheduler(bot)
    return scheduler
