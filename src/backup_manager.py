import os
import subprocess
import tarfile
from pathlib import Path
from datetime import datetime
import logging
import config

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.backup_dir = Path(config.BACKUP_DIR)
        self.marzban_service_path = Path(config.MARZBAN_SERVICE_PATH)
        self.db_service_name = config.DB_SERVICE_NAME
        self.excluded_databases = config.EXCLUDED_DATABASES

    def ensure_backup_dir(self):
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, is_cron: bool = False) -> tuple[bool, str]:
        try:
            self.ensure_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"marzban_backup_{timestamp}.tar.gz"
            backup_path = self.backup_dir / backup_filename

            with tarfile.open(backup_path, "w:gz") as tar:
                # Backup Marzban service files
                for path in [config.MARZBAN_SERVICE_PATH, "/var/lib/marzban"]:
                    if Path(path).exists():
                        tar.add(path, arcname=Path(path).name)

                # Backup database
                db_backup_file = self.backup_dir / f"marzban_db_{timestamp}.sql"
                try:
                    cmd = f"mysqldump --all-databases --skip-databases {' '.join(self.excluded_databases)} > {db_backup_file}"
                    subprocess.run(cmd, shell=True, check=True)
                    tar.add(db_backup_file, arcname=db_backup_file.name)
                    db_backup_file.unlink()
                except subprocess.CalledProcessError as e:
                    logger.error(f"Database backup failed: {e}")
                    return False, str(e)

            logger.info(f"Backup created: {backup_filename}")
            return True, backup_filename
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False, str(e)

    def restore_backup(self, backup_filename: str) -> tuple[bool, str]:
        try:
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                return False, "ÙØ§ÛŒÙ„ Ø¨Ú©Ø§Ù¾ ÛŒØ§ÙØª Ù†Ø´Ø¯."

            with tarfile.open(backup_path, "r:gz") as tar:
                # Restore files
                tar.extractall(path="/")
                
                # Restore database
                for member in tar.getmembers():
                    if member.name.endswith(".sql"):
                        temp_sql = self.backup_dir / member.name
                        tar.extract(member, path=self.backup_dir)
                        cmd = f"mysql < {temp_sql}"
                        subprocess.run(cmd, shell=True, check=True)
                        temp_sql.unlink()

            logger.info(f"Backup restored: {backup_filename}")
            return True, "Ø±ÛŒØ³ØªÙˆØ± Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ø§Ù†Ø¬Ø§Ù… Ø´Ø¯."
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False, str(e)

    def list_backups(self) -> list[str]:
        self.ensure_backup_dir()
        return [f.name for f in self.backup_dir.glob("marzban_backup_*.tar.gz")]
