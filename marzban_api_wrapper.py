import requests
import logging
from typing import Optional, Dict, Any
from config_manager import get_config_value

# --- Setup Logging ---
logger = logging.getLogger(__name__)

class MarzbanAPI:
    """A wrapper for the Marzban Panel API for administrative tasks.

    This class handles authentication and communication with the Marzban API.
    It requires configuration values from config.json under the 'marzban_api' key.
    """

    def __init__(self):
        """Initializes the API wrapper, loading credentials and setting up a session."""
        self.base_url = get_config_value('marzban_api.base_url')
        self.username = get_config_value('marzban_api.username')
        self.password = get_config_value('marzban_api.password')
        
        if not all([self.base_url, self.username, self.password]):
            logger.critical("Marzban API credentials (base_url, username, password) are not fully configured in config.json.")
            raise ValueError("Marzban API credentials are incomplete. Please check config.json.")

        # Ensure base_url ends with a slash for consistent endpoint construction
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        self._authenticate()

    def _authenticate(self):
        """Authenticates with the API and stores the access token in the session headers."""
        url = f"{self.base_url}api/admin/token"
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            response = self.session.post(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=10)
            response.raise_for_status()
            token = response.json().get('access_token')
            if not token:
                raise ValueError("No access token received from Marzban API.")
            self.session.headers['Authorization'] = f"Bearer {token}"
            logger.info("Successfully authenticated with Marzban API.")
        except requests.RequestException as e:
            error_msg = f"Marzban API authentication failed: {e}"
            if e.response is not None:
                error_msg += f" | Response: {e.response.text}"
            logger.critical(error_msg)
            raise ConnectionError(error_msg)

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Makes a request to the API, re-authenticating if the token has expired."""
        url = f"{self.base_url}api/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(method, url, json=data, params=params, timeout=10)
            if response.status_code == 401:
                logger.warning("Token expired or invalid. Re-authenticating...")
                self._authenticate()
                response = self.session.request(method, url, json=data, params=params, timeout=10)
            
            response.raise_for_status()
            return response.json() if response.content else {"detail": "Success"}
        except requests.RequestException as e:
            error_message = f"API request to '{endpoint}' failed: {e}"
            if e.response is not None:
                error_message += f" | Response: {e.response.text}"
            logger.error(error_message)
            return {"detail": error_message}

    def test_connection(self) -> bool:
        """Tests connectivity to the Marzban API."""
        try:
            response = self._request('GET', 'system')
            return 'detail' not in response or 'error' not in response.lower()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_users(self, username: Optional[str] = None, offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        """Fetches users, optionally filtered by username or admin."""
        params = {"offset": offset, "limit": limit}
        if username:
            params['username'] = username
        return self._request('GET', 'users', params=params)

    def create_user(self, username: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new user with the specified attributes."""
        return self._request('POST', 'user', data=data)

    def modify_user(self, username: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modifies a user's attributes (e.g., status, data_limit)."""
        return self._request('PUT', f"user/{username}", data=modifications)

    def delete_user(self, username: str) -> Dict[str, Any]:
        """Deletes a user by username."""
        return self._request('DELETE', f"user/{username}")

    def get_admin_users(self, admin_username: str) -> list:
        """Fetches all users created by a specific admin."""
        try:
            params = {"admin": admin_username}
            response = self._request('GET', 'users', params=params)
            if 'users' in response:
                return response['users']
            logger.warning(f"No users found for admin '{admin_username}'.")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch users for admin '{admin_username}': {e}")
            return []

    def disable_all_active_users(self, admin_username: str) -> Dict[str, Any]:
        """Disables all active users for a given admin."""
        users = self.get_admin_users(admin_username)
        if not users:
            logger.info(f"No users found for admin '{admin_username}'.")
            return {"detail": "No users found for this admin."}
        
        success_count = 0
        fail_count = 0
        for user in users:
            if user.get('status') == 'active':
                response = self.modify_user(user['username'], {"status": "disabled"})
                if 'username' in response and response['username'] == user['username']:
                    success_count += 1
                else:
                    fail_count += 1
                    logger.error(f"Failed to disable user '{user['username']}': {response.get('detail', 'Unknown error')}")
        
        result = {"detail": f"Operation complete. Successfully disabled: {success_count}, Failed: {fail_count}."}
        logger.info(result["detail"])
        return result

    def activate_all_disabled_users(self, admin_username: str) -> Dict[str, Any]:
        """Activates all disabled users for a given admin."""
        users = self.get_admin_users(admin_username)
        if not users:
            logger.info(f"No users found for admin '{admin_username}'.")
            return {"detail": "No users found for this admin."}

        success_count = 0
        fail_count = 0
        for user in users:
            if user.get('status') == 'disabled':
                response = self.modify_user(user['username'], {"status": "active"})
                if 'username' in response and response['username'] == user['username']:
                    success_count += 1
                else:
                    fail_count += 1
                    logger.error(f"Failed to activate user '{user['username']}': {response.get('detail', 'Unknown error')}")
        
        result = {"detail": f"Operation complete. Successfully activated: {success_count}, Failed: {fail_count}."}
        logger.info(result["detail"])
        return result

    def get_system_status(self) -> Dict[str, Any]:
        """Fetches the system status from the Marzban API."""
        return self._request('GET', 'system')

    def create_admin(self, username: str, password: str, is_sudo: bool = False) -> Dict[str, Any]:
        """Creates a new admin user."""
        data = {
            'username': username,
            'password': password,
            'is_sudo': is_sudo
        }
        return self._request('POST', 'admin', data=data)

    def delete_admin(self, username: str) -> Dict[str, Any]:
        """Deletes an admin user."""
        return self._request('DELETE', f"admin/{username}")

    def set_user_traffic_limit(self, username: str, data_limit: Optional[int]) -> Dict[str, Any]:
        """Sets or removes the traffic limit for a user."""
        modifications = {"data_limit": data_limit}
        return self.modify_user(username, modifications)

    def set_user_expiry(self, username: str, expiry_date: Optional[str]) -> Dict[str, Any]:
        """Sets or removes the expiry date for a user."""
        modifications = {"expire": expiry_date}
        return self.modify_user(username, modifications)