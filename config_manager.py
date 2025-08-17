import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)
CONFIG_FILE = Path("/opt/marzban-control-bot/config.json")

def load_config() -> Optional[Dict[str, Any]]:
    """Loads the configuration from config.json.

    Returns:
        Optional[Dict[str, Any]]: The configuration dictionary, or None if the file doesn't exist or is corrupted.

    Raises:
        PermissionError: If the config file cannot be read due to insufficient permissions.
    """
    if not CONFIG_FILE.exists():
        logger.warning(f"Configuration file '{CONFIG_FILE}' does not exist.")
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # Validate essential keys
            required_keys = {'telegram': ['bot_token', 'admin_chat_id'], 'database': ['user', 'password'], 'marzban_api': ['base_url', 'username', 'password']}
            for section, keys in required_keys.items():
                if section not in config:
                    logger.error(f"Missing required section '{section}' in config.json.")
                    return None
                for key in keys:
                    if key not in config[section]:
                        logger.error(f"Missing required key '{key}' in section '{section}' of config.json.")
                        return None
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Configuration file '{CONFIG_FILE}' is corrupted: {e}")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied while reading configuration file '{CONFIG_FILE}': {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration from '{CONFIG_FILE}': {e}")
        return None

def save_config(config: Dict[str, Any]) -> bool:
    """Saves the provided configuration to config.json with secure permissions.

    Args:
        config (Dict[str, Any]): The configuration dictionary to save.

    Returns:
        bool: True if the save was successful, False otherwise.

    Raises:
        PermissionError: If the config file cannot be written due to insufficient permissions.
    """
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        os.chmod(CONFIG_FILE, 0o600)  # Restrict access to root only
        logger.info(f"Configuration saved successfully to '{CONFIG_FILE}'.")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied while writing configuration file '{CONFIG_FILE}': {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to save configuration to '{CONFIG_FILE}': {e}")
        return False

def get_config_value(key_path: str, default: Any = None) -> Any:
    """Retrieves a nested value from the config using a dot-separated path.

    Args:
        key_path (str): The dot-separated path to the desired value (e.g., 'telegram.bot_token').
        default (Any, optional): The default value to return if the key is not found. Defaults to None.

    Returns:
        Any: The value from the configuration, or the default value if not found.

    Example:
        value = get_config_value('telegram.bot_token')
    """
    config = load_config()
    if not config:
        logger.warning(f"Configuration not loaded. Returning default value for '{key_path}'.")
        return default
    
    keys = key_path.split('.')
    value = config
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        logger.warning(f"Key '{key_path}' not found in configuration. Returning default value.")
        return default