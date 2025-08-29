import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import db
from marzban_api import marzban_api
from scheduler import init_scheduler
from handlers.sudo_handlers import sudo_router
from handlers.admin_handlers import admin_router
from handlers.public_handlers import public_router
from handlers.backup_handlers import backup_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MarzbanUnifiedBot:
    def __init__(self):
        self.bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.scheduler = None

    async def setup(self):
        """Setup bot components."""
        logger.info("Setting up Marzban Unified Bot...")
        
        # Initialize database
        try:
            await db.init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
        # Test Marzban API connection
        try:
            if await marzban_api.test_connection():
                logger.info("Marzban API connection successful")
            else:
                logger.warning("Marzban API connection failed - some features may not work")
        except Exception as e:
            logger.warning(f"Error testing Marzban API: {e}")
        
        # Register routers
        self.dp.include_router(sudo_router)
        self.dp.include_router(admin_router)
        self.dp.include_router(public_router)
        self.dp.include_router(backup_router)
        
        # Initialize scheduler
        self.scheduler = init_scheduler(self.bot)
        logger.info("Scheduler initialized")

    async def start_polling(self):
        """Start bot polling."""
        logger.info("Starting bot polling...")
        
        try:
            await self.scheduler.start()
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error during polling: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up bot resources...")
        try:
            if self.scheduler:
                await self.scheduler.stop()
            await db.close()
            await self.bot.session.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def send_startup_message(self):
        """Send startup notification to sudo admins."""
        startup_message = (
            "ðŸš€ Ø±Ø¨Ø§Øª ÛŒÚ©Ù¾Ø§Ø±Ú†Ù‡ Ù…Ø¯ÛŒØ±ÛŒØª Ùˆ Ø¨Ú©Ø§Ù¾ Ù…Ø±Ø²Ø¨Ø§Ù† Ø±Ø§Ù‡â€ŒØ§Ù†Ø¯Ø§Ø²ÛŒ Ø´Ø¯!\n\n"
            f"â° Ø¯ÙˆØ±Ù‡ Ù…Ø§Ù†ÛŒØªÙˆØ±ÛŒÙ†Ú¯: {config.MONITORING_INTERVAL} Ø«Ø§Ù†ÛŒÙ‡\n"
            f"ðŸ“Š Ø¢Ø³ØªØ§Ù†Ù‡ Ù‡Ø´Ø¯Ø§Ø±: {int(config.WARNING_THRESHOLD * 100)}%\n"
            f"ðŸ”— Ø¢Ø¯Ø±Ø³ Ù…Ø±Ø²Ø¨Ø§Ù†: {config.MARZBAN_URL}"
        )
        for sudo_id in config.SUDO_ADMINS:
            try:
                await self.bot.send_message(sudo_id, startup_message)
            except Exception as e:
                logger.warning(f"Failed to send startup message to sudo {sudo_id}: {e}")

async def main():
    try:
        if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN":
            logger.error("BOT_TOKEN is not set in config!")
            return
        if not config.SUDO_ADMINS:
            logger.error("No SUDO_ADMINS configured!")
            return
        bot = MarzbanUnifiedBot()
        await bot.setup()
        await bot.send_startup_message()
        await bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
