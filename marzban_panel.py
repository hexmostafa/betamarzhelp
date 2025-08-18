#!/usr/bin/env python3
# =================================================================
# Marzban Professional Control Panel - Refactored Version
# Creator: @HEXMOSTAFA
# Optimized and Refactored by Gemini
# Version: 5.2 (Validation Fix)
# Last Updated: August 18, 2025
# =================================================================

import os
import sys
import subprocess
import json
import shutil
import tarfile
from time import sleep
from datetime import datetime
import requests
from subprocess import Popen, PIPE
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional
from pathlib import Path

# --- Third-party Library Check ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.theme import Theme
except ImportError:
    print("FATAL ERROR: 'rich' library is not installed. Please run 'pip3 install rich'.")
    sys.exit(1)

try:
    from marzban_api_wrapper import MarzbanAPI
except ImportError:
    print("FATAL ERROR: 'marzban_api_wrapper' module not found. Ensure it is in the project directory.")
    sys.exit(1)

# --- Global Configuration ---
INSTALL_DIR = Path("/opt/marzban-control-bot")
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = INSTALL_DIR / "config.json"
LOG_FILE = INSTALL_DIR / "marzban_panel.log"
PATHS_TO_BACKUP = {
    "var_lib_marzban": Path("/var/lib/marzban"),
    "opt_marzban": Path("/opt/marzban")
}
EXCLUDED_DATABASES = ['information_schema', 'mysql', 'performance_schema', 'sys']
CRON_JOB_IDENTIFIER = "# MARZBAN_CONTROL_BACKUP_JOB"
MARZBAN_SERVICE_PATH = Path("/opt/marzban")
DOTENV_PATH = MARZBAN_SERVICE_PATH / ".env"
TG_BOT_FILE_NAME = "marzban_bot.py"

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Rich Console Setup ---
custom_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "danger": "bold red",
    "header": "bold white on blue",
    "menu": "bold yellow",
    "prompt": "bold magenta"
})
console = Console(theme=custom_theme)

# =================================================================
# HELPER FUNCTIONS
# =================================================================

def log_message(message: str, style: str = "info"):
    """Logs a message to the console and file with appropriate styling."""
    level = logging.INFO
    if style == "danger":
        level = logging.ERROR
    elif style == "warning":
        level = logging.WARNING
    
    logger.log(level, message)
    
    if sys.stdout.isatty():
        console.print(f"[{style}]{message}[/{style}]")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def load_config() -> Optional[Dict[str, Any]]:
    """Loads the configuration from config.json."""
    if not CONFIG_FILE.exists():
        log_message(f"Config file '{CONFIG_FILE}' not found.", "warning")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        log_message("Config file is corrupted. It will be recreated.", "danger")
        return None

def save_config(config: Dict[str, Any]):
    """Saves the configuration to config.json."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        os.chmod(CONFIG_FILE, 0o600)
        log_message(f"Settings saved to '{CONFIG_FILE}'", "success")
    except Exception as e:
        log_message(f"Failed to save config file: {e}", "danger")
        raise

def find_dotenv_password() -> Optional[str]:
    """Finds the MySQL/MariaDB root password from the .env file in the Marzban directory."""
    if not DOTENV_PATH.exists():
        log_message(f".env file not found at '{DOTENV_PATH}'", "warning")
        return None
    try:
        with open(DOTENV_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line.startswith(('MYSQL_ROOT_PASSWORD=', 'MARIADB_ROOT_PASSWORD=')):
                    return stripped_line.split('=', 1)[1].strip()
        return None
    except Exception as e:
        log_message(f"Error reading .env file: {e}", "danger")
        return None

def find_database_container() -> Optional[str]:
    """Finds the most likely Marzban database container."""
    try:
        cmd = "docker ps -a --format '{{.Names}} {{.Image}}' | grep -E 'mysql|mariadb'"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'marzban' in line.lower():
                return line.split()[0]
        if lines and lines[0]:
            return lines[0].split()[0]
        return None
    except subprocess.CalledProcessError:
        log_message("No MySQL/MariaDB container found.", "warning")
        return None

def validate_telegram_config(bot_token: str, admin_chat_id: str) -> bool:
    """Validates Telegram bot token and admin chat ID with the correct format."""
    # A valid token is numeric_id:string_token
    if not bot_token or ':' not in bot_token:
        log_message("Invalid Telegram bot token format. It should be in the format 'NUMERIC_ID:TOKEN_STRING'.", "danger")
        return False
    
    parts = bot_token.split(':', 1)
    if not parts[0].isdigit():
        log_message("Invalid Telegram bot token. The part before the colon must be a numeric bot ID.", "danger")
        return False

    try:
        int(admin_chat_id)
    except ValueError:
        log_message("Admin Chat ID must be a valid integer.", "danger")
        return False
    return True

def get_interactive_config(ask_telegram: bool = False, ask_database: bool = False, ask_interval: bool = False) -> Dict[str, Any]:
    """Interactively prompts the user for configuration details."""
    config = load_config() or {"telegram": {}, "database": {}, "marzban_api": {}}
    
    if ask_telegram:
        console.print(Panel("Telegram Bot Credentials", style="info"))
        while True:
            bot_token = Prompt.ask("[prompt]Enter your Telegram Bot Token[/prompt]", default=config.get("telegram", {}).get('bot_token', ''))
            admin_chat_id = Prompt.ask("[prompt]Enter your Admin Chat ID[/prompt]", default=config.get("telegram", {}).get('admin_chat_id', ''))
            if validate_telegram_config(bot_token, admin_chat_id):
                config["telegram"]['bot_token'] = bot_token
                config["telegram"]['admin_chat_id'] = admin_chat_id
                break

    if ask_database:
        console.print(Panel("Database Credentials", style="info"))
        config.setdefault('database', {})
        found_password = find_dotenv_password()
        
        if found_password:
            console.print("[info]Password found in .env file: [bold]...hidden...[/bold][/info]")
            if Confirm.ask("[prompt]Do you want to use this password?[/prompt]", default=True):
                config["database"]['password'] = found_password
            else:
                config["database"]['password'] = Prompt.ask("[prompt]Enter the database password[/prompt]", password=True)
        else:
            log_message("Could not find password in .env file. Please enter manually.", "warning")
            config["database"]['password'] = Prompt.ask("[prompt]Enter the database password[/prompt]", password=True)
        
        config["database"]['user'] = Prompt.ask("[prompt]Enter the Database Username[/prompt]", default=config.get("database", {}).get('user', 'root'))

    if ask_interval:
        config.setdefault('telegram', {})
        while True:
            interval = Prompt.ask(
                "[prompt]Enter auto backup interval in minutes (e.g., 60)[/prompt]",
                default=str(config.get("telegram", {}).get('backup_interval', '60'))
            )
            if interval.isdigit() and int(interval) > 0:
                config["telegram"]['backup_interval'] = interval
                break
            log_message("Backup interval must be a positive integer.", "danger")

    # Marzban API configuration
    console.print(Panel("Marzban API Configuration", style="info"))
    config.setdefault('marzban_api', {})
    default_url = config.get("marzban_api", {}).get('base_url', 'http://localhost:8000')
    config["marzban_api"]['base_url'] = Prompt.ask("[prompt]Enter Marzban API base URL[/prompt]", default=default_url)
    config["marzban_api"]['username'] = Prompt.ask("[prompt]Enter Marzban API username[/prompt]", default=config.get("marzban_api", {}).get('username', 'admin'))
    config["marzban_api"]['password'] = Prompt.ask("[prompt]Enter Marzban API password[/prompt]", password=True, default=config.get("marzban_api", {}).get('password', ''))

    save_config(config)
    return config

def test_marzban_api(config: Dict[str, Any]) -> bool:
    """Tests connectivity to Marzban API."""
    try:
        api = MarzbanAPI()
        # Simple API call to verify connectivity
        response = requests.get(f"{config['marzban_api']['base_url']}/api/system", headers={'Authorization': f'Bearer {api.token}'}, timeout=5)
        response.raise_for_status()
        log_message("Marzban API connection successful.", "success")
        return True
    except Exception as e:
        log_message(f"Failed to connect to Marzban API: {e}", "danger")
        return False

def run_marzban_command(action: str) -> bool:
    """Runs a docker compose command for Marzban."""
    if not MARZBAN_SERVICE_PATH.is_dir():
        log_message(f"Marzban path '{MARZBAN_SERVICE_PATH}' not found. Is Marzban installed?", "danger")
        return False

    commands_to_try = [
        f"cd {MARZBAN_SERVICE_PATH} && docker compose {action}",
        f"cd {MARZBAN_SERVICE_PATH} && docker-compose {action}"
    ]
    
    for command in commands_to_try:
        try:
            log_message(f"Running command: {command.split('&&')[1].strip()}", "info")
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True, executable='/bin/bash')
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            stderr = getattr(e, 'stderr', str(e))
            log_message(f"Command failed: {stderr.strip()}", "warning")
    
    log_message("Both 'docker compose' and 'docker-compose' commands failed.", "danger")
    return False

def show_header():
    console.clear()
    header_text = Text("Marzban Professional Control Panel\nCreator: @HEXMOSTAFA | Refactored Version 5.2", justify="center", style="header")
    console.print(Panel(header_text, style="blue", border_style="info"))
    console.print()

def show_main_menu() -> str:
    console.print(Panel(
        "[menu]1[/menu]. [bold]Create Full Backup[/bold]\n"
        "[menu]2[/menu]. [bold]Restore from Backup[/bold]\n"
        "[menu]3[/menu]. [bold]Setup Telegram Bot[/bold]\n"
        "[menu]4[/menu]. [bold]Setup Auto Backup (Cronjob)[/bold]\n"
        "[menu]5[/menu]. [bold]Exit[/bold]",
        title="Main Menu", title_align="left", border_style="info"
    ))
    return Prompt.ask("[prompt]Enter your choice[/prompt]", choices=["1", "2", "3", "4", "5"], default="5")

# =================================================================
# CORE LOGIC: BACKUP, RESTORE, SETUP
# =================================================================

def run_full_backup(config: Dict[str, Any], is_cron: bool = False):
    """Creates a full backup of Marzban (filesystem and database) as a .tar.gz archive."""
    log_message("Starting full backup process...", "info")
    if not test_marzban_api(config):
        log_message("Cannot proceed with backup due to API connection failure.", "danger")
        return

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_temp_dir = Path(tempfile.mkdtemp(prefix="marzban_backup_"))
    final_archive_path = Path(f"/root/marzban_backup_{timestamp}.tar.gz")
    final_archive_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # --- Database Backup ---
        container_name = find_database_container()
        db_config = config.get('database', {})
        if container_name and db_config.get('user') and db_config.get('password'):
            log_message(f"Found database container '{container_name}'. Backing up databases...", "info")
            db_backup_path = backup_temp_dir / "db_dumps"
            db_backup_path.mkdir()
            try:
                list_dbs_cmd = f"docker exec -i {container_name} mysql -u{db_config['user']} -p'{db_config['password']}' -e 'SHOW DATABASES;'"
                result = subprocess.run(list_dbs_cmd, shell=True, check=True, capture_output=True, text=True)
                databases = [db for db in result.stdout.strip().split('\n') if db not in EXCLUDED_DATABASES and db != 'Database']
                
                for db in databases:
                    log_message(f"Dumping database: {db}", "info")
                    dump_cmd = f"docker exec -i {container_name} mysqldump -u{db_config['user']} -p'{db_config['password']}' --databases {db} > {str(db_backup_path / f'{db}.sql')}"
                    subprocess.run(dump_cmd, shell=True, check=True, executable='/bin/bash')
                log_message("Database backup complete.", "success")
            except subprocess.CalledProcessError as e:
                log_message(f"Database backup failed: {e.stderr.strip()}", "danger")
                log_message("Hint: Check if the database container is running and the credentials are correct.", "warning")
        else:
            log_message("No database container found or credentials missing. Skipping database backup.", "warning")

        # --- Filesystem Backup ---
        log_message("Backing up filesystem...", "info")
        fs_backup_path = backup_temp_dir / "filesystem"
        fs_backup_path.mkdir()
        for unique_name, path in PATHS_TO_BACKUP.items():
            if path.exists():
                log_message(f"Copying '{path}' to backup directory...", "info")
                destination = fs_backup_path / unique_name
                ignore_func = shutil.ignore_patterns('mysql', 'logs', '*.sock', '*.sock.lock')
                shutil.copytree(path, destination, dirs_exist_ok=True, ignore=ignore_func, symlinks=False)
            else:
                log_message(f"Path not found, skipping: {path}", "warning")
        
        # --- Compression ---
        log_message(f"Compressing backup into '{final_archive_path}'...", "info")
        with tarfile.open(final_archive_path, "w:gz") as tar:
            tar.add(str(backup_temp_dir), arcname=".")
        os.chmod(final_archive_path, 0o600)
        log_message(f"Backup created successfully: {final_archive_path}", "success")
        
        # --- Telegram Upload ---
        tg_config = config.get('telegram', {})
        if tg_config.get('bot_token') and tg_config.get('admin_chat_id'):
            log_message("Sending backup to Telegram...", "info")
            url = f"https://api.telegram.org/bot{tg_config['bot_token']}/sendDocument"
            caption = f"✅ Marzban Backup ({'Auto' if is_cron else 'Manual'})\n📅 {timestamp}"
            with open(final_archive_path, 'rb') as f:
                response = requests.post(url, data={'chat_id': tg_config['admin_chat_id'], 'caption': caption}, files={'document': f}, timeout=300)
                response.raise_for_status()
            log_message("Backup sent to Telegram!", "success")
            if is_cron:
                os.remove(final_archive_path)
                log_message("Removed local cron backup file.", "info")

    except Exception as e:
        log_message(f"A critical error occurred during backup: {e}", "danger")
        logger.exception("Backup process failed")
    finally:
        log_message("Cleaning up temporary files...", "info")
        shutil.rmtree(backup_temp_dir, ignore_errors=True)

def _perform_restore(archive_path: Path, config: Dict[str, Any]):
    """The core, non-interactive restore logic."""
    if not test_marzban_api(config):
        log_message("Cannot proceed with restore due to API connection failure.", "danger")
        return

    temp_dir = Path(tempfile.mkdtemp(prefix="marzban_restore_"))
    try:
        log_message("Verifying and extracting backup file...", "info")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)
        log_message("Backup extracted successfully.", "success")

        with console.status("[info]Stopping all Marzban services...[/info]", spinner="dots"):
            if not run_marzban_command("down"):
                raise Exception("Could not stop Marzban services. Restore cannot continue.")
        log_message("All Marzban services stopped.", "success")

        # --- Filesystem Restore ---
        fs_restore_path = temp_dir / "filesystem"
        if fs_restore_path.is_dir():
            log_message("Restoring configuration files...", "info")
            if (fs_restore_path / "opt_marzban").is_dir():
                shutil.copytree(fs_restore_path / "opt_marzban", MARZBAN_SERVICE_PATH, dirs_exist_ok=True)
                log_message(f"Restored '{MARZBAN_SERVICE_PATH}'.", "success")
            if (fs_restore_path / "var_lib_marzban").is_dir():
                shutil.copytree(fs_restore_path / "var_lib_marzban", Path("/var/lib/marzban"), dirs_exist_ok=True)
                log_message("Restored '/var/lib/marzban'.", "success")

        # --- Update DB Password from Restored .env ---
        log_message("Reading database password from restored .env file...", "info")
        new_password = find_dotenv_password()
        if new_password:
            log_message("Password found in backup. Updating session for restore.", "success")
            config['database']['password'] = new_password
            save_config(config)
        else:
            log_message("Could not find password in restored .env. Using password from config.json.", "warning")

        # --- Database Restore ---
        db_restore_path = temp_dir / "db_dumps"
        sql_files = list(db_restore_path.glob("*.sql"))
        if not sql_files:
            log_message("No .sql files found in backup. Skipping database restore.", "info")
        else:
            mysql_data_dir = Path("/var/lib/marzban/mysql")
            log_message(f"Clearing MySQL data directory ({mysql_data_dir}) for a clean restore...", "info")
            if mysql_data_dir.exists():
                shutil.rmtree(mysql_data_dir)
            mysql_data_dir.mkdir(parents=True, exist_ok=True)
            
            with console.status("[info]Starting services to initialize database...[/info]", spinner="dots"):
                if not run_marzban_command("up -d"):
                    raise Exception("Could not start Marzban services for DB initialization.")
            log_message("Services started. Waiting 30 seconds for MySQL to stabilize...", "info")
            sleep(30)
            
            container_name = find_database_container()
            if not container_name:
                raise Exception("Could not find database container after restart.")
                
            db_user = config['database']['user']
            db_pass = config['database']['password']

            for sql_file in sql_files:
                db_name_to_restore = sql_file.stem
                log_message(f"Importing data into database '{db_name_to_restore}'...", "info")
                restore_cmd = f"cat {sql_file} | docker exec -i {container_name} mysql -u{db_user} -p'{db_pass}' {db_name_to_restore}"
                
                result = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True, executable='/bin/bash')
                if result.returncode == 0:
                    log_message(f"Database '{db_name_to_restore}' imported successfully.", "success")
                else:
                    raise Exception(f"Database import for '{db_name_to_restore}' failed: {result.stderr.strip()}")

        console.print(Panel("[bold green]✅ Restore process finished. Marzban should be running with the restored data.[/bold green]"))

    except Exception as e:
        log_message(f"A critical error occurred during restore: {e}", "danger")
        logger.exception("Restore process failed")
        log_message("Attempting to bring Marzban service back up as a safety measure...", "info")
        run_marzban_command("up -d")
    finally:
        log_message("Cleaning up temporary restore files...", "info")
        shutil.rmtree(temp_dir, ignore_errors=True)

def restore_flow():
    """Interactive flow for restoring a backup from a local file."""
    show_header()
    console.print(Panel(
        "[bold]This is a highly destructive operation.[/bold]\nIt will [danger]STOP[/danger] services and "
        "[danger]OVERWRITE[/danger] all current Marzban data with the backup's content.",
        title="[warning]CRITICAL WARNING[/warning]", border_style="danger"
    ))
    if not Confirm.ask("[danger]Do you understand the risks and wish to continue?[/danger]"):
        log_message("Restore operation cancelled by user.", "warning")
        return
    
    config = get_interactive_config(ask_database=True)
    if not config.get('database', {}).get('password'):
        log_message("Database credentials are required to proceed with the restore. Aborting.", "danger")
        return

    archive_path_str = Prompt.ask("[prompt]Enter the full path to your .tar.gz backup file[/prompt]")
    archive_path = Path(archive_path_str.strip())
    
    if not archive_path.is_file():
        log_message(f"Error: The file '{archive_path}' was not found. Aborting.", "danger")
        return
        
    _perform_restore(archive_path, config)

def setup_bot_flow():
    """Interactive flow to set up the Telegram bot as a systemd service."""
    show_header()
    console.print(Panel("Telegram Bot Setup", style="info"))
    console.print("[info]This will configure the bot and run it as a background service.[/info]")
    
    config = get_interactive_config(ask_telegram=True, ask_database=True)
    
    if not all([config.get('telegram', {}).get('bot_token'), config.get('telegram', {}).get('admin_chat_id'), config.get('database', {}).get('password')]):
        log_message("Bot Token, Admin Chat ID, and Database Password are all required. Setup aborted.", "danger")
        return
        
    bot_script_path = INSTALL_DIR / TG_BOT_FILE_NAME
    if not bot_script_path.exists():
        log_message(f"Bot script '{TG_BOT_FILE_NAME}' not found in '{INSTALL_DIR}'. Aborting.", "danger")
        return
        
    try:
        service_file_path = Path("/etc/systemd/system/marzban_bot.service")
        python_executable = INSTALL_DIR / "venv" / "bin" / "python3"

        service_content = f"""[Unit]
Description=Marzban Professional Control Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={INSTALL_DIR}
ExecStart={python_executable} {str(bot_script_path)}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        with open(service_file_path, "w", encoding='utf-8') as f:
            f.write(service_content)
        os.chmod(service_file_path, 0o644)
        
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        with console.status("[bold green]Enabling and starting Telegram bot service...[/bold green]"):
            subprocess.run(['systemctl', 'enable', '--now', 'marzban_bot.service'], check=True)
        sleep(3)
        
        result = subprocess.run(['systemctl', 'is-active', 'marzban_bot.service'], capture_output=True, text=True)
        if result.stdout.strip() == "active":
            console.print("[bold green]✅ Telegram bot service is now running successfully.[/bold green]")
            console.print("[info]Check logs with 'journalctl -u marzban_bot -n 100'[/info]")
        else:
            console.print("[bold red]❌ The bot service failed to start. Check logs with 'journalctl -u marzban_bot -n 100'.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ An unexpected error occurred during service setup: {e}[/bold red]")

def setup_cronjob_flow(interactive: bool = True):
    """Sets up a cronjob for automatic backups."""
    if interactive:
        show_header()
        console.print(Panel("Automatic Backup Setup (Cronjob)", style="info"))

    config = load_config()
    if not config:
        log_message("Configuration file not found. Please run setup first.", "danger")
        return

    if not all([config.get("telegram", {}).get('bot_token'), config.get("telegram", {}).get('admin_chat_id'), config.get("database", {}).get('password')]):
        log_message("Telegram Bot and Database must be fully configured first. Please run Option 3.", "danger")
        return

    if interactive:
        config = get_interactive_config(ask_interval=True)

    interval = config.get("telegram", {}).get('backup_interval')
    if not interval or not str(interval).isdigit() or int(interval) <= 0:
        log_message("Invalid or missing backup interval in config.json. Cannot set up cronjob.", "danger")
        return

    python_executable = INSTALL_DIR / "venv" / "bin" / "python3"
    script_path = INSTALL_DIR / "marzban_panel.py"
    cron_command = f"*/{interval} * * * * {python_executable} {str(script_path)} run-backup > /dev/null 2>&1"
    
    if interactive:
        console.print(Panel(f"The following command will be added to crontab:\n\n[info]{cron_command}[/info]", title="Cronjob Command"))
        if not Confirm.ask("[prompt]Do you authorize this action?[/prompt]"):
            log_message("Crontab setup cancelled.", "warning")
            return

    try:
        current_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False).stdout
        new_lines = [line for line in current_crontab.splitlines() if CRON_JOB_IDENTIFIER not in line]
        new_lines.append(f"{cron_command} {CRON_JOB_IDENTIFIER}")
        
        p = Popen(['crontab', '-'], stdin=PIPE)
        p.communicate(input=("\n".join(new_lines) + "\n").encode())
        if p.returncode != 0:
            raise Exception("The 'crontab' command failed.")
        
        log_message("✅ Crontab updated successfully!", "success")
        
        if interactive:
            log_message("Performing an initial backup to test the new schedule...", "info")
            run_full_backup(config, is_cron=False)

    except Exception as e:
        log_message(f"An error occurred while updating crontab: {e}", "danger")

def main():
    """Main function to dispatch tasks based on arguments or run interactively."""
    if os.geteuid() != 0:
        log_message("This script requires root privileges. Please run it with 'sudo'.", "danger")
        sys.exit(1)

    # --- NON-INTERACTIVE MODE (for Bot and Cron) ---
    if len(sys.argv) > 1:
        command = sys.argv[1]
        config = load_config()
        if not config:
            log_message("Configuration file not found. Cannot run non-interactively.", "danger")
            sys.exit(1)
        
        if command == 'run-backup':
            run_full_backup(config, is_cron=True)
        elif command == 'do-restore':
            if len(sys.argv) > 2:
                archive_path = Path(sys.argv[2])
                if archive_path.is_file():
                    _perform_restore(archive_path, config)
                else:
                    log_message(f"Backup file not found: {archive_path}", "danger")
                    sys.exit(1)
            else:
                log_message("Error: Restore command requires a file path argument.", "danger")
                sys.exit(1)
        elif command == 'setup':
            get_interactive_config(ask_telegram=True, ask_database=True, ask_interval=True)
        sys.exit(0)

    # --- INTERACTIVE MODE (for human users) ---
    while True:
        show_header()
        choice = show_main_menu()
        if choice == "1":
            config = get_interactive_config(ask_telegram=True, ask_database=True)
            run_full_backup(config)
        elif choice == "2":
            restore_flow()
        elif choice == "3":
            setup_bot_flow()
        elif choice == "4":
            setup_cronjob_flow()
        elif choice == "5":
            log_message("Goodbye!", "info")
            break
        Prompt.ask("\n[prompt]Press Enter to return to the main menu...[/prompt]")

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
        log_message("Application exited by user.", "warning")
        sys.exit(0)
    except Exception as e:
        log_message(f"An unexpected fatal error occurred: {str(e)}", "danger")
        logger.critical("Unexpected fatal error", exc_info=True)
        sys.exit(1)
