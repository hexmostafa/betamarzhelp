import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUDO_ADMINS: List[int] = [
    int(x) for x in os.getenv("SUDO_ADMINS", "").split(",") if x.strip()
]

# Marzban Configuration
MARZBAN_URL = os.getenv("MARZBAN_URL", "https://your-marzban-panel.com")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "admin")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "admin_password")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot_database.db")

# Monitoring Configuration
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "600"))
WARNING_THRESHOLD = float(os.getenv("WARNING_THRESHOLD", "0.8"))
AUTO_DELETE_EXPIRED_USERS = os.getenv("AUTO_DELETE_EXPIRED_USERS", "false").lower() in ["1", "true", "yes"]

# Backup Configuration
BACKUP_DIR = os.getenv("BACKUP_DIR", "/opt/marzban_backups")
# کد جدید برای خواندن بازه زمانی بکاپ
raw_backup_interval = os.getenv("BACKUP_INTERVAL", "daily")
try:
    # تلاش برای تبدیل مقدار به عدد (برای بازه‌های ساعتی)
    BACKUP_INTERVAL = int(raw_backup_interval)
except ValueError:
    # اگر عدد نبود، همان مقدار رشته‌ای باقی بماند
    BACKUP_INTERVAL = raw_backup_interval

DB_SERVICE_NAME = os.getenv("DB_SERVICE_NAME", "mysql")
EXCLUDED_DATABASES = ['information_schema', 'mysql', 'performance_schema', 'sys']
MARZBAN_SERVICE_PATH = os.getenv("MARZBAN_SERVICE_PATH", "/opt/marzban")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

# API Configuration
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Messages in Persian
MESSAGES = {
    "welcome_sudo": "ðŸ” Ø³Ù„Ø§Ù…! Ø´Ù…Ø§ Ø¨Ù‡ Ø¹Ù†ÙˆØ§Ù† Ø³ÙˆØ¯Ùˆ Ø§Ø¯Ù…ÛŒÙ† ÙˆØ§Ø±Ø¯ Ø´Ø¯Ù‡â€ŒØ§ÛŒØ¯.\n\nÚ©Ù„ÛŒØ¯Ù‡Ø§ÛŒ Ø¯Ø³ØªÙˆØ±:",
    "welcome_admin": "ðŸ‘‹ Ø³Ù„Ø§Ù…! Ø´Ù…Ø§ Ø¨Ù‡ Ø¹Ù†ÙˆØ§Ù† Ø§Ø¯Ù…ÛŒÙ† Ù…Ø¹Ù…ÙˆÙ„ÛŒ ÙˆØ§Ø±Ø¯ Ø´Ø¯Ù‡â€ŒØ§ÛŒØ¯.\n\nÚ©Ù„ÛŒØ¯Ù‡Ø§ÛŒ Ø¯Ø³ØªÙˆØ±:",
    "unauthorized": "â›” Ø´Ù…Ø§ Ù…Ø¬Ø§Ø² Ø¨Ù‡ Ø§Ø³ØªÙØ§Ø¯Ù‡ Ø§Ø² Ø§ÛŒÙ† Ø±Ø¨Ø§Øª Ù†ÛŒØ³ØªÛŒØ¯.",
    "admin_added": "âœ… Ø§Ø¯Ù…ÛŒÙ† Ø¬Ø¯ÛŒØ¯ Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ø§Ø¶Ø§ÙÙ‡ Ø´Ø¯:",
    "admin_removed": "âŒ Ù¾Ù†Ù„ Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª ØºÛŒØ±ÙØ¹Ø§Ù„ Ø´Ø¯.",
    "backup_success": "âœ… Ø¨Ú©Ø§Ù¾ Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ø§ÛŒØ¬Ø§Ø¯ Ø´Ø¯: {filename}",
    "restore_success": "âœ… Ø±ÛŒØ³ØªÙˆØ± Ø¨Ø§ Ù…ÙˆÙÙ‚ÛŒØª Ø§Ù†Ø¬Ø§Ù… Ø´Ø¯.",
    "backup_error": "âŒ Ø®Ø·Ø§ Ø¯Ø± Ø§ÛŒØ¬Ø§Ø¯ Ø¨Ú©Ø§Ù¾: {error}",
    "restore_error": "âŒ Ø®Ø·Ø§ Ø¯Ø± Ø±ÛŒØ³ØªÙˆØ±: {error}",
    # ... Ø³Ø§ÛŒØ± Ù¾ÛŒØ§Ù…â€ŒÙ‡Ø§ Ù…Ø´Ø§Ø¨Ù‡ config.py Ø§ØµÙ„ÛŒ
}

# Button Labels
BUTTONS = {
    "add_admin": "âž• Ø§ÙØ²ÙˆØ¯Ù† Ø§Ø¯Ù…ÛŒÙ†",
    "remove_admin": "ðŸ—‘ï¸ Ø­Ø°Ù Ù¾Ù†Ù„",
    "backup_create": "ðŸ“¦ Ø§ÛŒØ¬Ø§Ø¯ Ø¨Ú©Ø§Ù¾",
    "backup_restore": "ðŸ”„ Ø±ÛŒØ³ØªÙˆØ± Ø¨Ú©Ø§Ù¾",
    "backup_schedule": "âš™ï¸ ØªÙ†Ø¸ÛŒÙ… Ø¨Ú©Ø§Ù¾ Ø®ÙˆØ¯Ú©Ø§Ø±",
    # ... Ø³Ø§ÛŒØ± Ø¯Ú©Ù…Ù‡â€ŒÙ‡Ø§ Ù…Ø´Ø§Ø¨Ù‡ config.py Ø§ØµÙ„ÛŒ
}
