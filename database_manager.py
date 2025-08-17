import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import logging
from typing import Optional, List, Dict, Any
from datetime import date, timedelta
import json

from config_manager import get_config_value

logger = logging.getLogger(__name__)

BOT_DATABASE_NAME = "hexcontrol"

# Initialize database connection pool
try:
    db_config = get_config_value('database')
    if not db_config:
        raise ValueError("Database configuration is missing in config.json.")

    connection_pool = pooling.MySQLConnectionPool(
        pool_name="marzban_pool",
        pool_size=5,
        host=db_config.get('host', '127.0.0.1'),
        user=db_config.get('user', 'root'),
        password=db_config.get('password'),
        database=None  # Database is selected dynamically
    )
    logger.info("Database connection pool created successfully.")
except Exception as e:
    logger.critical(f"Failed to create database connection pool: {e}")
    connection_pool = None

@contextmanager
def get_db_connection(db_name: str):
    """Provides a database connection from the pool and selects the specified database.

    Args:
        db_name (str): The name of the database to use.

    Yields:
        mysql.connector.connection.MySQLConnection: A database connection.

    Raises:
        ConnectionError: If the connection pool is unavailable or the database cannot be selected.
    """
    if not connection_pool:
        raise ConnectionError("Database pool is not available.")
    connection = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(f"USE `{db_name}`")
        cursor.close()
        yield connection
    except mysql.connector.Error as err:
        logger.error(f"Error connecting to database '{db_name}': {err}")
        raise ConnectionError(f"Failed to connect to database '{db_name}': {err}")
    finally:
        if connection and connection.is_connected():
            connection.close()

def execute_query(db_name: str, query: str, params: tuple = (), fetch: Optional[str] = None) -> Any:
    """Executes a database query with optional fetch mode.

    Args:
        db_name (str): The name of the database to query.
        query (str): The SQL query to execute.
        params (tuple): Parameters for the query to prevent SQL injection.
        fetch (str, optional): Fetch mode ('one' for single row, 'all' for multiple rows).

    Returns:
        Any: The result of the query (rowcount for modifications, dict for fetches, None for errors).

    Raises:
        ConnectionError: If the query fails due to connection issues.
    """
    try:
        with get_db_connection(db_name) as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
                return cursor.rowcount
            
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            return None
    except (mysql.connector.Error, ConnectionError) as err:
        logger.error(f"Database query failed: {err}\nQuery: {query}\nParams: {params}")
        return None

def initialize_database():
    """Initializes the 'hexcontrol' database and necessary tables if they don't exist."""
    try:
        with get_db_connection('mysql') as conn:
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {BOT_DATABASE_NAME}")
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {BOT_DATABASE_NAME}.admin_settings (
                    admin_id INT PRIMARY KEY,
                    total_traffic BIGINT,
                    expiry_date DATE,
                    user_limit INT,
                    status JSON,
                    calculate_volume ENUM('used_traffic', 'created_traffic') DEFAULT 'used_traffic'
                )
            """)
            conn.commit()
            logger.info(f"Database '{BOT_DATABASE_NAME}' and tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        raise

def get_admin_info(admin_id: int) -> Optional[Dict[str, Any]]:
    """Fetches comprehensive information for a given admin, including total user count.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with admin details or None if not found.
    """
    admin_query = "SELECT id, username, is_sudo, telegram_id FROM admins WHERE id = %s"
    admin_data = execute_query('marzban', admin_query, (admin_id,), fetch='one')
    if not admin_data:
        logger.warning(f"No admin found with ID {admin_id}")
        return None

    settings_query = "SELECT total_traffic, expiry_date, user_limit, status, calculate_volume FROM admin_settings WHERE admin_id = %s"
    settings_data = execute_query(BOT_DATABASE_NAME, settings_query, (admin_id,), fetch='one') or {}

    calc_method = settings_data.get('calculate_volume', 'used_traffic')

    if calc_method == 'created_traffic':
        traffic_query = """
            SELECT (
                IFNULL((SELECT SUM(CASE WHEN u.data_limit IS NOT NULL THEN u.data_limit ELSE u.used_traffic END) 
                        FROM users u WHERE u.admin_id = a.id), 0)
            ) / (1024*1024*1024) AS total_usage_gb
            FROM admins a
            WHERE a.id = %s
        """
    else:
        traffic_query = """
            SELECT (
                IFNULL((SELECT SUM(u.used_traffic) FROM users u WHERE u.admin_id = a.id), 0)
            ) / (1024*1024*1024) AS total_usage_gb
            FROM admins a
            WHERE a.id = %s
        """
    
    traffic_data = execute_query('marzban', traffic_query, (admin_id,), fetch='one') or {'total_usage_gb': 0}
    
    users_query = """
        SELECT
            COUNT(*) AS total_users,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_users,
            SUM(CASE WHEN TIMESTAMPDIFF(MINUTE, online_at, NOW()) <= 5 THEN 1 ELSE 0 END) AS online_users
        FROM users WHERE admin_id = %s
    """
    user_stats = execute_query('marzban', users_query, (admin_id,), fetch='one') or \
                 {'total_users': 0, 'active_users': 0, 'online_users': 0}

    # Safety checks for None values
    total_users = user_stats.get('total_users', 0) or 0
    active_users = user_stats.get('active_users', 0) or 0
    online_users = user_stats.get('online_users', 0) or 0
    used_traffic_gb = round(float(traffic_data.get('total_usage_gb', 0)), 2)
    
    total_traffic_bytes = settings_data.get('total_traffic')
    total_traffic_gb = "Unlimited" if total_traffic_bytes is None else round(float(total_traffic_bytes) / (1024**3), 2)
    remaining_traffic_gb = "Unlimited" if total_traffic_bytes is None else round(total_traffic_gb - used_traffic_gb, 2)
    
    expiry_date = settings_data.get('expiry_date')
    days_left = "Unlimited" if expiry_date is None else max(0, (expiry_date - date.today()).days)

    status_json = settings_data.get('status', '{}')
    try:
        status_dict = json.loads(status_json)
    except (json.JSONDecodeError, TypeError):
        status_dict = {}
    admin_status = status_dict.get('users', 'active')

    user_limit = settings_data.get('user_limit', "Unlimited") if settings_data.get('user_limit') is not None else "Unlimited"

    return {
        "id": admin_data['id'],
        "username": admin_data['username'],
        "is_sudo": bool(admin_data.get('is_sudo', 0)),
        "telegram_id": admin_data.get('telegram_id'),
        "used_traffic_gb": used_traffic_gb,
        "total_traffic_gb": total_traffic_gb,
        "remaining_traffic_gb": remaining_traffic_gb,
        "days_left": days_left,
        "user_limit": user_limit,
        "status": admin_status,
        "calculate_volume": calc_method,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "online_users": online_users
    }

def get_blocked_admin_ids() -> List[int]:
    """Fetches a list of admin IDs that have reached or exceeded their user limit based on total users.

    Returns:
        List[int]: A list of admin IDs that are blocked from creating new users.
    """
    query = """
        SELECT a.id
        FROM marzban.admins a
        JOIN hexcontrol.admin_settings s ON a.id = s.admin_id
        JOIN (
            SELECT admin_id, COUNT(*) as total_users
            FROM marzban.users
            GROUP BY admin_id
        ) u ON a.id = u.admin_id
        WHERE s.user_limit IS NOT NULL AND u.total_users >= s.user_limit
    """
    result = execute_query('marzban', query, fetch='all') or []
    blocked_ids = [row['id'] for row in result]
    logger.info(f"Blocked admin IDs based on total users: {blocked_ids}")
    return blocked_ids

def update_user_creation_trigger(blocked_admin_ids: List[int]) -> bool:
    """Creates or updates a trigger to block user creation for admins who have reached their user limit.

    Args:
        blocked_admin_ids (List[int]): List of admin IDs that are blocked.

    Returns:
        bool: True if the trigger was updated successfully, False otherwise.
    """
    trigger_name = 'enforce_user_limit_before_insert'
    
    try:
        with get_db_connection('marzban') as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            conn.commit()

            if not blocked_admin_ids:
                logger.info("No admins are over the total user limit. Trigger removed.")
                return True

            admin_ids_str = ", ".join(map(str, blocked_admin_ids))
            logger.info(f"Updating trigger to block user creation for admin IDs: {admin_ids_str}")

            trigger_query = f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT ON `users`
            FOR EACH ROW
            BEGIN
                DECLARE current_user_count INT;
                DECLARE max_user_limit INT;
                IF NEW.admin_id IN ({admin_ids_str}) THEN
                    SELECT COUNT(*) INTO current_user_count FROM `users` WHERE admin_id = NEW.admin_id;
                    SELECT user_limit INTO max_user_limit FROM {BOT_DATABASE_NAME}.admin_settings WHERE admin_id = NEW.admin_id;
                    IF current_user_count >= max_user_limit THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Admin has reached the user creation limit.';
                    END IF;
                END IF;
            END
            """
            cursor.execute(trigger_query)
            conn.commit()
            logger.info("Successfully updated the user creation trigger.")
            return True
    except Exception as e:
        logger.error(f"Failed to create user creation trigger: {e}")
        return False

def _update_admin_setting(admin_id: int, column: str, value: Any) -> bool:
    """Updates a single admin setting in the admin_settings table.

    Args:
        admin_id (int): The ID of the admin.
        column (str): The column to update.
        value (Any): The value to set.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    query = f"INSERT INTO admin_settings (admin_id, {column}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {column} = %s"
    result = execute_query(BOT_DATABASE_NAME, query, (admin_id, value, value))
    return result is not None

def update_admin_traffic(admin_id: int, amount_gb: float) -> bool:
    """Updates the total traffic limit for an admin.

    Args:
        admin_id (int): The ID of the admin.
        amount_gb (float): The amount of traffic to add or subtract (in GB).

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    amount_bytes = int(amount_gb * (1024**3))
    query = "INSERT INTO admin_settings (admin_id, total_traffic) VALUES (%s, %s) ON DUPLICATE KEY UPDATE total_traffic = GREATEST(0, COALESCE(total_traffic, 0) + %s)"
    result = execute_query(BOT_DATABASE_NAME, query, (admin_id, amount_bytes, amount_bytes))
    return result is not None

def set_admin_traffic_unlimited(admin_id: int) -> bool:
    """Sets an admin's traffic limit to unlimited.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    return _update_admin_setting(admin_id, 'total_traffic', None)

def update_admin_expiry(admin_id: int, days: int) -> bool:
    """Updates the expiry date for an admin by adding or subtracting days.

    Args:
        admin_id (int): The ID of the admin.
        days (int): The number of days to add or subtract.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    current_info_query = "SELECT expiry_date FROM admin_settings WHERE admin_id = %s"
    current_info = execute_query(BOT_DATABASE_NAME, current_info_query, (admin_id,), fetch='one') or {}
    
    current_date = current_info.get('expiry_date', date.today())
    if current_info.get('expiry_date') and current_info['expiry_date'] > date.today():
        current_date = current_info['expiry_date']
    
    new_date = current_date + timedelta(days=days)
    return _update_admin_setting(admin_id, 'expiry_date', new_date)

def set_admin_expiry_unlimited(admin_id: int) -> bool:
    """Sets an admin's expiry date to unlimited.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    return _update_admin_setting(admin_id, 'expiry_date', None)

def set_admin_user_limit(admin_id: int, limit: Optional[int]) -> bool:
    """Sets the user creation limit for an admin.

    Args:
        admin_id (int): The ID of the admin.
        limit (Optional[int]): The user limit or None for unlimited.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    return _update_admin_setting(admin_id, 'user_limit', limit)

def set_admin_traffic_calculation(admin_id: int, method: str) -> bool:
    """Sets the traffic calculation method for an admin.

    Args:
        admin_id (int): The ID of the admin.
        method (str): The calculation method ('used_traffic' or 'created_traffic').

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    if method not in ['used_traffic', 'created_traffic']:
        logger.error(f"Invalid traffic calculation method: {method}")
        return False
    return _update_admin_setting(admin_id, 'calculate_volume', method)

def set_admin_users_status(admin_id: int, status_str: str) -> bool:
    """Sets the status of users created by an admin.

    Args:
        admin_id (int): The ID of the admin.
        status_str (str): The status to set ('active' or 'disabled').

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    if status_str not in ['active', 'disabled']:
        logger.error(f"Invalid status: {status_str}")
        return False
    current_status_raw = execute_query(BOT_DATABASE_NAME, "SELECT status FROM admin_settings WHERE admin_id = %s", (admin_id,), fetch='one') or {}
    status_dict = {}
    if current_status_raw.get('status'):
        try:
            status_dict = json.loads(current_status_raw['status'])
        except (json.JSONDecodeError, TypeError):
            status_dict = {}
    status_dict['users'] = status_str
    return _update_admin_setting(admin_id, 'status', json.dumps(status_dict))

def update_admin_sudo(admin_id: int, is_sudo: bool) -> bool:
    """Updates the sudo status of an admin.

    Args:
        admin_id (int): The ID of the admin.
        is_sudo (bool): Whether the admin should have sudo privileges.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    query = "UPDATE admins SET is_sudo = %s WHERE id = %s"
    result = execute_query('marzban', query, (1 if is_sudo else 0, admin_id))
    return result is not None

def update_admin_password(admin_id: int, hashed_password: str) -> bool:
    """Updates the hashed password of an admin.

    Args:
        admin_id (int): The ID of the admin.
        hashed_password (str): The hashed password to set.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    query = "UPDATE admins SET password = %s WHERE id = %s"
    result = execute_query('marzban', query, (hashed_password, admin_id))
    return result is not None

def get_all_admins() -> List[Dict[str, Any]]:
    """Fetches all admins from the database.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing admin IDs and usernames.
    """
    result = execute_query('marzban', "SELECT id, username FROM admins ORDER BY id", fetch='all') or []
    return result

def update_users_of_admin_traffic(admin_id: int, amount_gb: float) -> bool:
    """Updates the traffic limit for all users of an admin.

    Args:
        admin_id (int): The ID of the admin.
        amount_gb (float): The amount of traffic to add or subtract (in GB).

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    amount_bytes = int(amount_gb * (1024**3))
    query = "UPDATE users SET data_limit = GREATEST(0, COALESCE(data_limit, 0) + %s) WHERE admin_id = %s AND data_limit IS NOT NULL"
    result = execute_query('marzban', query, (amount_bytes, admin_id))
    return result is not None

def update_users_of_admin_expiry(admin_id: int, days: int) -> bool:
    """Updates the expiry date for all users of an admin.

    Args:
        admin_id (int): The ID of the admin.
        days (int): The number of days to add or subtract.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    seconds = int(days * 86400)
    query = "UPDATE users SET expire = GREATEST(0, COALESCE(expire, 0) + %s) WHERE admin_id = %s AND expire IS NOT NULL"
    result = execute_query('marzban', query, (seconds, admin_id))
    return result is not None

def set_inbound_access(admin_id: int, enabled: bool) -> bool:
    """Sets the inbound access permission for an admin.

    Args:
        admin_id (int): The ID of the admin.
        enabled (bool): Whether inbound access is enabled.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    current_status_raw = execute_query(BOT_DATABASE_NAME, "SELECT status FROM admin_settings WHERE admin_id = %s", (admin_id,), fetch='one') or {}
    status_dict = {}
    if current_status_raw.get('status'):
        try:
            status_dict = json.loads(current_status_raw['status'])
        except (json.JSONDecodeError, TypeError):
            status_dict = {}
    status_dict['inbound_access'] = 'enabled' if enabled else 'disabled'
    return _update_admin_setting(admin_id, 'status', json.dumps(status_dict))

def set_advanced_restrictions(admin_id: int, restrictions: Dict[str, Any]) -> bool:
    """Sets advanced restrictions for an admin.

    Args:
        admin_id (int): The ID of the admin.
        restrictions (Dict[str, Any]): A dictionary of advanced restrictions.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    current_status_raw = execute_query(BOT_DATABASE_NAME, "SELECT status FROM admin_settings WHERE admin_id = %s", (admin_id,), fetch='one') or {}
    status_dict = {}
    if current_status_raw.get('status'):
        try:
            status_dict = json.loads(current_status_raw['status'])
        except (json.JSONDecodeError, TypeError):
            status_dict = {}
    status_dict['advanced_restrictions'] = restrictions
    return _update_admin_setting(admin_id, 'status', json.dumps(status_dict))