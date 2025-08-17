Marzban Control Bot
A professional Telegram bot for managing Marzban VPN panel admins, created by @HEXMOSTAFA and optimized by xAI.
Features

Admin management (create, delete, edit)
Traffic and expiry management for admins and their users
Backup and restore functionality
Automatic backup scheduling
Secure API integration with Marzban
User-friendly interface with inline keyboards

Prerequisites

Python 3.8+
Required Python packages: telebot, bcrypt, requests
A running Marzban VPN panel with API access
Sudo privileges on the server
A Telegram bot token from BotFather

Installation

Clone the repository:
git clone https://github.com/yourusername/marzban-control-bot.git
cd marzban-control-bot


Install dependencies:
pip install -r requirements.txt


Run the setup script:
sudo python3 marzban_panel.py setup

Follow the prompts to enter:

Telegram bot token
Admin chat ID
Marzban API base URL, username, and password
Backup directory path


Start the bot:
python3 marzban_bot.py



Usage

Start the bot with /start in Telegram.
Use the inline keyboard to navigate through admin management, server status, and settings.
Follow on-screen instructions for creating/deleting admins, managing traffic/expiry, and handling backups.

Project Structure
marzban-control-bot/
├── marzban_bot.py          # Main bot script
├── marzban_panel.py        # Panel management script
├── keyboards.py            # Inline keyboard definitions
├── config_manager.py       # Configuration management
├── database_manager.py     # Database operations
├── marzban_api_wrapper.py  # Marzban API wrapper
├── config.json             # Configuration file (generated)
├── marzban.db              # SQLite database (generated)
├── requirements.txt        # Python dependencies
├── README.md               # This file

Configuration
The config.json file is generated during setup and contains:
{
    "telegram": {
        "bot_token": "your_bot_token",
        "admin_chat_id": "your_admin_chat_id",
        "backup_interval": "60"
    },
    "marzban_api": {
        "base_url": "http://localhost:8000",
        "username": "admin_username",
        "password": "admin_password"
    },
    "backup": {
        "backup_dir": "/path/to/backups"
    }
}

Contributing
Contributions are welcome! Please open an issue or pull request on GitHub.
License
MIT License
