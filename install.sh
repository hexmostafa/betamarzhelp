#!/bin/bash

# =================================================================
# Marzban Control Bot Installer/Uninstaller
# Creator: @HEXMOSTAFA
# Optimized and Refactored by xAI
# Version: 2.3.5 (Stable & Robust, Auto-Download from GitHub)
# Last Updated: August 17, 2025
# =================================================================

set -e

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

# --- Colors ---
C_RESET='\e[0m'
C_RED='\e[1;31m'
C_GREEN='\e[1;32m'
C_YELLOW='\e[1;33m'
C_BLUE='\e[1;34m'
C_CYAN='\e[1;36m'
C_WHITE='\e[1;37m'

# --- Utility Functions ---
print_msg() {
    local color=$1
    local text=$2
    if [ -t 1 ]; then
        echo -e "${color}${text}${C_RESET}"
    else
        echo "${text}"
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

check_file_content() {
    local file_path=$1
    local file_name=$2
    if grep -q "404: Not Found" "$file_path" 2>/dev/null; then
        print_msg "$C_RED" "❌ Downloaded ${file_name} contains '404: Not Found'. Please verify the file in the repository."
        rm -f "$file_path"
        exit 1
    fi
}

detect_package_manager() {
    if command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v zypper &>/dev/null; then
        echo "zypper"
    else
        print_msg "$C_RED" "❌ Unsupported OS. No compatible package manager found."
        exit 1
    fi
}

install_dependencies() {
    local pm
    pm=$(detect_package_manager)
    print_msg "$C_YELLOW" "▶ Installing system dependencies..."
    
    local debian_pkgs="python3 python3-pip python3-venv curl git build-essential python3-dev"
    local rhel_pkgs="python3 python3-pip python3-virtualenv curl git python3-devel gcc make"
    local arch_pkgs="python python-pip python-virtualenv curl git base-devel"
    local suse_pkgs="python3 python3-pip python3-virtualenv curl git patterns-devel-base-devel_basis"

    case "$pm" in
        "apt")
            apt-get update -qq && apt-get install -y $debian_pkgs >/dev/null
            ;;
        "dnf")
            dnf install -y $rhel_pkgs >/dev/null
            ;;
        "yum")
            yum install -y $rhel_pkgs >/dev/null
            ;;
        "pacman")
            pacman -Syu --noconfirm $arch_pkgs >/dev/null
            ;;
        "zypper")
            zypper install -y $suse_pkgs >/dev/null
            ;;
    esac

    if ! command -v python3 &>/dev/null || ! command -v pip3 &>/dev/null || ! command -v git &>/dev/null; then
        print_msg "$C_RED" "❌ Dependency installation failed."
        exit 1
    fi

    print_msg "$C_GREEN" "✔ System dependencies installed."
}

create_systemd_service() {
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
}

uninstall() {
    print_msg "$C_YELLOW" "▶ Starting uninstallation..."
    
    # Stop and remove systemd service
    if systemctl list-units --full -all | grep -q "${SERVICE_NAME}"; then
        print_msg "$C_YELLOW" "  - Stopping and removing systemd service..."
        systemctl stop "$SERVICE_NAME" || true
        systemctl disable "$SERVICE_NAME" || true
        rm -f "/etc/systemd/system/${SERVICE_NAME}"
        systemctl daemon-reload
        print_msg "$C_GREEN" "  ✔ Service removed."
    fi

    # Remove launcher commands
    for launcher in "$LAUNCHER_NAME" "$BOT_LAUNCHER_NAME"; do
        if [ -f "/usr/local/bin/${launcher}" ]; then
            print_msg "$C_YELLOW" "  - Removing launcher command ${launcher}..."
            rm -f "/usr/local/bin/${launcher}"
            print_msg "$C_GREEN" "  ✔ Launcher removed."
        fi
    done

    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        print_msg "$C_YELLOW" "  - Removing installation directory..."
        rm -rf "$INSTALL_DIR"
        print_msg "$C_GREEN" "  ✔ Directory removed."
    fi

    print_msg "$C_GREEN" "✅ Uninstallation complete!"
}

install() {
    print_msg "$C_BLUE" "============================================"
    print_msg "$C_GREEN" "  Marzban Control Bot Installer "
    print_msg "$C_BLUE" "============================================"
    echo
    if [ -d "$INSTALL_DIR" ] || [ -f "/usr/local/bin/${LAUNCHER_NAME}" ] || [ -f "/usr/local/bin/${BOT_LAUNCHER_NAME}" ]; then
        print_msg "$C_YELLOW" "ℹ Previous installation detected. Running uninstaller first..."
        uninstall
        echo
    fi
    check_connectivity
    check_requirements_url
    echo
    install_dependencies
    echo
    print_msg "$C_YELLOW" "▶ Creating installation directory at ${INSTALL_DIR}..."
    mkdir -p "$INSTALL_DIR"
    chown root:root "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    print_msg "$C_GREEN" "✔ Directory created."
    echo
    print_msg "$C_YELLOW" "▶ Downloading scripts from GitHub..."
    
    local files_to_download=(
        "marzban_bot.py"
        "marzban_panel.py"
        "keyboards.py"
        "config_manager.py"
        "database_manager.py"
        "marzban_api_wrapper.py"
    )
    for file in "${files_to_download[@]}"; do
        local file_url="${BASE_URL}/${file}"
        check_url_access "$file_url" "$file"
        print_msg "$C_CYAN" "  - Downloading ${file}..."
        if ! curl -sSL --fail -o "${INSTALL_DIR}/${file}" "$file_url"; then
            print_msg "$C_RED" "❌ Failed to download ${file} from ${file_url}."
            exit 1
        fi
        check_file_content "${INSTALL_DIR}/${file}" "$file"
    done

    chmod +x "${INSTALL_DIR}"/*.py
    print_msg "$C_GREEN" "✔ Scripts downloaded successfully."
    echo
    print_msg "$C_YELLOW" "▶ Setting up Python virtual environment..."
    python3 -m venv "${INSTALL_DIR}/${VENV_DIR}"
    if ! "${INSTALL_DIR}/${VENV_DIR}/bin/pip" install -r "${REQUIREMENTS_URL}" >/dev/null; then
        print_msg "$C_RED" "❌ Failed to install Python libraries from ${REQUIREMENTS_URL}. Please check the URL or try again."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ Python libraries installed."
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
    create_systemd_service
    echo
    print_msg "$C_YELLOW" "▶ Running initial setup..."
    if ! "${INSTALL_DIR}/${VENV_DIR}/bin/python3" "${INSTALL_DIR}/marzban_panel.py" setup; then
        print_msg "$C_RED" "❌ Failed to run initial setup. Please check ${INSTALL_DIR}/marzban_panel.py for errors."
        exit 1
    fi
    print_msg "$C_GREEN" "✔ Setup complete."
    echo
    print_msg "$C_BLUE" "============================================"
    print_msg "$C_GREEN" "✅ Installation is complete!"
    print_msg "$C_WHITE" "To configure the panel, run:"
    print_msg "$C_CYAN" "    sudo ${LAUNCHER_NAME} setup"
    print_msg "$C_WHITE" "To start the bot manually, run:"
    print_msg "$C_CYAN" "    sudo ${BOT_LAUNCHER_NAME}"
    print_msg "$C_WHITE" "The bot is already running as a service. To check status:"
    print_msg "$C_CYAN" "    sudo systemctl status ${SERVICE_NAME}"
    print_msg "$C_WHITE" "To uninstall the tool later, run:"
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
