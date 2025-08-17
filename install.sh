#!/bin/bash

# =================================================================
# Marzban Control Bot Installer/Uninstaller
# Creator: @HEXMOSTAFA
# Optimized and Refactored by Gemini
# Version: 2.3.9 (Robust & Interactive)
# Last Updated: August 18, 2025
# =================================================================

set -e

# Change to a safe directory to avoid getcwd errors during uninstall
cd /tmp || cd /

# --- Configuration ---
INSTALL_DIR="/opt/marzban-control-bot"
VENV_DIR="venv"
LAUNCHER_NAME="marzban-panel"
BOT_LAUNCHER_NAME="marzban-bot"
SERVICE_NAME="marzban_bot.service"
GITHUB_USER="hexmostafa"
REPO_NAME="betamarzhelp"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/refs/heads/${BRANCH}"
REQUIREMENTS_URL="${BASE_URL}/requirements.txt"
CONFIG_FILE="${INSTALL_DIR}/config.json"

# --- Colors & Utilities ---
C_RESET='\e[0m'
C_RED='\e[1;31m'
C_GREEN='\e[1;32m'
C_YELLOW='\e[1;33m'
C_BLUE='\e[1;34m'
C_CYAN='\e[1;36m'
C_WHITE='\e[1;37m'

print_msg() {
    local color=$1
    local text=$2
    if [ -t 1 ]; then
        echo -e "${color}${text}${C_RESET}"
    else
        echo "${text}"
    fi
}

ask_for_input() {
    local prompt=$1
    local var_name=$2
    local default_value=$3
    print_msg "$C_CYAN" "$prompt"
    read -rp "↳ " input
    if [[ -z "$input" ]]; then
        eval "$var_name=\"$default_value\""
    else
        eval "$var_name=\"$input\""
    fi
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$C_RED" "❌ Error: This script must be run as root. Please use 'sudo'."
        exit 1
    fi
}

check_connectivity() {
    print_msg "$C_YELLOW" "▶ Checking internet connectivity..."
    if ! ping -c 1 google.com &>/dev/null; then
        print_msg "$C_RED" "❌ No internet connection. Please check your network."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ Internet connection confirmed."
}

check_url_access() {
    local url=$1
    local file_name=$2
    print_msg "$C_YELLOW" "▶ Checking availability of ${file_name}..."
    if ! curl -s --head --fail "$url" | grep -q "200"; then
        print_msg "$C_RED" "❌ Failed to access ${file_name} at ${url}. Please check the URL or repository."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ ${file_name} is accessible."
}

uninstall() {
    print_msg "$C_YELLOW" "▶ Starting uninstallation..."
    if systemctl list-units --full -all | grep -q "${SERVICE_NAME}"; then
        print_msg "$C_YELLOW" "  - Stopping and removing systemd service..."
        systemctl stop "$SERVICE_NAME" || true
        systemctl disable "$SERVICE_NAME" || true
        rm -f "/etc/systemd/system/${SERVICE_NAME}"
        systemctl daemon-reload
        print_msg "$C_GREEN" "  ✔ Service removed."
    fi
    for launcher in "$LAUNCHER_NAME" "$BOT_LAUNCHER_NAME"; do
        if [ -f "/usr/local/bin/${launcher}" ]; then
            print_msg "$C_YELLOW" "  - Removing launcher command ${launcher}..."
            rm -f "/usr/local/bin/${launcher}"
            print_msg "$C_GREEN" "  ✔ Launcher removed."
        fi
    done
    if [ -d "$INSTALL_DIR" ]; then
        print_msg "$C_YELLOW" "  - Removing installation directory..."
        rm -rf "$INSTALL_DIR"
        print_msg "$C_GREEN" "  ✔ Directory removed."
    fi
    print_msg "$C_GREEN" "✅ Uninstallation complete!"
}

create_config_file() {
    print_msg "$C_YELLOW" "▶ Collecting configuration details..."
    ask_for_input "Enter Telegram Bot Token:" "BOT_TOKEN" ""
    ask_for_input "Enter Telegram Admin Chat ID:" "ADMIN_CHAT_ID" ""
    ask_for_input "Enter Marzban Panel URL (e.g., https://panel.example.com):" "MARZBAN_URL" ""
    ask_for_input "Enter Marzban Admin Username:" "MARZBAN_USER" "admin"
    ask_for_input "Enter Marzban Admin Password:" "MARZBAN_PASS" ""
    
    # You can add more questions for database if needed, but keeping it simple for now.
    
    print_msg "$C_YELLOW" "▶ Creating config.json file..."
    cat << EOF > "$CONFIG_FILE"
{
    "telegram": {
        "bot_token": "${BOT_TOKEN}",
        "admin_chat_id": "${ADMIN_CHAT_ID}",
        "backup_interval": "10"
    },
    "database": {
        "user": "root",
        "password": "",
        "host": "127.0.0.1"
    },
    "marzban": {
        "url": "${MARZBAN_URL}",
        "admin_username": "${MARZBAN_USER}",
        "admin_password": "${MARZBAN_PASS}"
    }
}
EOF
    print_msg "$C_GREEN" "✔ config.json created successfully."
}

install() {
    print_msg "$C_BLUE" "============================================"
    print_msg "$C_GREEN" "  Marzban Control Bot Installer "
    print_msg "$C_BLUE" "============================================"
    echo
    if [ -d "$INSTALL_DIR" ]; then
        print_msg "$C_YELLOW" "ℹ Previous installation detected. Running uninstaller first..."
        uninstall
        echo
    fi
    check_connectivity
    check_url_access "$REQUIREMENTS_URL" "requirements.txt"
    echo
    print_msg "$C_YELLOW" "▶ Installing system dependencies..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y python3 python3-pip python3-venv curl git build-essential python3-dev >/dev/null
    elif command -v dnf &>/dev/null; then
        dnf install -y python3 python3-pip python3-virtualenv curl git python3-devel gcc make >/dev/null
    else
        print_msg "$C_RED" "❌ Unsupported OS. Only Debian/Ubuntu and Fedora/CentOS are supported."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ System dependencies installed."
    echo
    print_msg "$C_YELLOW" "▶ Creating installation directory at ${INSTALL_DIR}..."
    mkdir -p "$INSTALL_DIR"
    chown root:root "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    print_msg "$C_GREEN" "✔ Directory created."
    echo
    print_msg "$C_YELLOW" "▶ Downloading scripts from GitHub..."
    for file in marzban_bot.py marzban_panel.py keyboards.py config_manager.py database_manager.py marzban_api_wrapper.py; do
        print_msg "$C_CYAN" "  - Downloading ${file}..."
        curl -sSL --fail -o "${INSTALL_DIR}/${file}" "${BASE_URL}/${file}" || { print_msg "$C_RED" "❌ Failed to download ${file}."; exit 1; }
    done
    chmod +x "${INSTALL_DIR}"/*.py
    print_msg "$C_GREEN" "✔ Scripts downloaded successfully."
    echo
    print_msg "$C_YELLOW" "▶ Setting up Python virtual environment..."
    python3 -m venv "${INSTALL_DIR}/${VENV_DIR}"
    if ! "${INSTALL_DIR}/${VENV_DIR}/bin/pip" install -r "${REQUIREMENTS_URL}" >/dev/null; then
        print_msg "$C_RED" "❌ Failed to install Python libraries. Please check requirements.txt."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ Python libraries installed."
    echo
    create_config_file
    echo
    print_msg "$C_YELLOW" "▶ Creating launcher commands..."
    cat << EOF > "/usr/local/bin/${LAUNCHER_NAME}"
#!/bin/bash
exec "${INSTALL_DIR}/${VENV_DIR}/bin/python3" "${INSTALL_DIR}/marzban_panel.py" "\$@"
EOF
    chmod +x "/usr/local/bin/${LAUNCHER_NAME}"
    print_msg "$C_GREEN" "✔ Panel launcher command created."
    cat << EOF > "/usr/local/bin/${BOT_LAUNCHER_NAME}"
#!/bin/bash
exec "${INSTALL_DIR}/${VENV_DIR}/bin/python3" "${INSTALL_DIR}/marzban_bot.py" "\$@"
EOF
    chmod +x "/usr/local/bin/${BOT_LAUNCHER_NAME}"
    print_msg "$C_GREEN" "✔ Bot launcher command created."
    echo
    print_msg "$C_YELLOW" "▶ Initializing database..."
    if ! "${INSTALL_DIR}/${VENV_DIR}/bin/python3" "${INSTALL_DIR}/database_manager.py"; then
        print_msg "$C_RED" "❌ Failed to initialize database. Please check ${INSTALL_DIR}/database_manager.py for errors."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ Database initialized."
    echo
    print_msg "$C_YELLOW" "▶ Creating systemd service for Marzban Control Bot..."
    cat << EOF > "/etc/systemd/system/${SERVICE_NAME}"
[Unit]
Description=Marzban Control Bot Service
After=network.target

[Service]
ExecStart=${INSTALL_DIR}/${VENV_DIR}/bin/python3 ${INSTALL_DIR}/marzban_bot.py
WorkingDirectory=${INSTALL_DIR}
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" >/dev/null
    systemctl start "$SERVICE_NAME" >/dev/null
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_msg "$C_GREEN" "✔ Systemd service created and started."
    else
        print_msg "$C_RED" "❌ Failed to start systemd service."
        exit 1
    fi
    echo
    print_msg "$C_BLUE" "============================================"
    print_msg "$C_GREEN" "✅ Installation is complete!"
    print_msg "$C_WHITE" "The bot is now running as a service. To check its status, run:"
    print_msg "$C_CYAN" "    sudo systemctl status ${SERVICE_NAME}"
    print_msg "$C_WHITE" "To uninstall the bot, run:"
    print_msg "$C_CYAN" "    sudo $0 uninstall"
    print_msg "$C_BLUE" "============================================"
}

main() {
    check_root
    case "$1" in
        "uninstall")
            uninstall
            ;;
        *)
            install
            ;;
    esac
}

main "$@"
