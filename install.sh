#!/bin/bash

C_RESET='\e[0m'
C_RED='\e[1;31m'
C_GREEN='\e[1;32m'
C_YELLOW='\e[1;33m'
C_CYAN='\e[1;36m'

print_msg() {
    local color=$1
    local text=$2
    echo -e "${color}${text}${C_RESET}"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$C_RED" "âŒ This script must be run as root. Please use 'sudo'."
        exit 1
    }
}

install_docker() {
    if ! command -v docker &>/dev/null; then
        print_msg "$C_YELLOW" "â–¶ Installing Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker
        systemctl start docker
        print_msg "$C_GREEN" "âœ” Docker installed."
    fi
}

install_system_deps() {
    print_msg "$C_YELLOW" "â–¶ Installing system dependencies..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y python3 python3-pip python3-venv curl
    elif command -v dnf &>/dev/null; then
        dnf install -y python3 python3-pip python3-virtualenv curl
    else
        print_msg "$C_RED" "âŒ Unsupported OS."
        exit 1
    fi
    print_msg "$C_GREEN" "âœ” System dependencies installed."
}

install_python_deps() {
    print_msg "$C_YELLOW" "â–¶ Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
    print_msg "$C_GREEN" "âœ” Python dependencies installed."
}

setup_service() {
    print_msg "$C_YELLOW" "â–¶ Setting up systemd service..."
    cat << EOF > /etc/systemd/system/marzban-unified-bot.service
[Unit]
Description=Marzban Unified Bot
After=network.target

[Service]
ExecStart=/usr/bin/env bash -c 'source /opt/marzban_unified_bot/venv/bin/activate && python3 /opt/marzban_unified_bot/src/bot.py'
WorkingDirectory=/opt/marzban_unified_bot
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable marzban-unified-bot.service
    systemctl start marzban-unified-bot.service
    print_msg "$C_GREEN" "âœ” Service setup complete."
}

install() {
    print_msg "$C_CYAN" "============================================"
    print_msg "$C_GREEN" "  Marzban Unified Bot Installer"
    print_msg "$C_CYAN" "============================================"
    
    read -p "Install with Docker? (y/n): " use_docker
    if [ "$use_docker" = "y" ]; then
        install_docker
        docker-compose up -d --build
        print_msg "$C_GREEN" "âœ… Installation complete with Docker!"
        print_msg "$C_CYAN" "Run 'docker-compose -f /opt/marzban_unified_bot/docker-compose.yml logs -f' to view logs."
    else
        install_system_deps
        mkdir -p /opt/marzban_unified_bot
        cp -r . /opt/marzban_unified_bot
        cd /opt/marzban_unified_bot
        install_python_deps
        setup_service
        print_msg "$C_GREEN" "âœ… Installation complete!"
        print_msg "$C_CYAN" "Run 'systemctl status marzban-unified-bot' to check status."
    fi

    print_msg "$C_YELLOW" "Please configure your .env file at /opt/marzban_unified_bot/.env"
}

uninstall() {
    print_msg "$C_YELLOW" "â–¶ Uninstalling..."
    systemctl stop marzban-unified-bot.service || true
    systemctl disable marzban-unified-bot.service || true
    rm -f /etc/systemd/system/marzban-unified-bot.service
    docker-compose down || true
    rm -rf /opt/marzban_unified_bot
    print_msg "$C_GREEN" "âœ… Uninstallation complete!"
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
