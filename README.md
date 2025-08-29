# Marzban Unified Bot

A unified Telegram bot for managing Marzban panels and performing backup/restore operations.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/hexmostafa/betamarzhelp.git
   cd marzban_unified_bot
   ```

2. Run the installer:
   ```bash
   sudo ./install.sh
   ```

3. Configure the `.env` file at `/opt/marzban_unified_bot/.env`:
   ```plaintext
BOT_TOKEN=your_bot_token
SUDO_ADMINS=123456789
MARZBAN_URL=https://your-marzban-panel.com
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=admin_password
BACKUP_INTERVAL=6
BACKUP_DIR=/var/backups/marzban
MARZBAN_SERVICE_PATH=/opt/marzban
TELEGRAM_ADMIN_CHAT_ID=your_admin_chat_id
MONITORING_INTERVAL=600
   ```

4. For Docker installation:
   ```bash
   docker-compose up -d
   ```

## Usage

- Start the bot with `systemctl start marzban-unified-bot` (non-Docker) or `docker-compose up -d` (Docker).
- Use Telegram commands to manage admins, users, payments, backups, and restores.

## Directory Structure

- `src/`: Python source code
- `data/`: Database and backup storage
- `logs/`: Log files
- `Dockerfile` and `docker-compose.yml`: For Docker deployment
- `install.sh`: Installation script
- `requirements.txt`: Python dependencies
