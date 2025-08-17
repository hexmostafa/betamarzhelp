from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Constants for callback data to avoid typos and improve maintainability
CALLBACK_MAIN_MENU = "main_menu"
CALLBACK_MANAGE_ADMINS = "manage_admins"
CALLBACK_SHOW_STATUS = "show_status"
CALLBACK_SETTINGS = "settings"
CALLBACK_NOOP = "noop"
CALLBACK_CREATE_BACKUP = "create_backup"
CALLBACK_START_RESTORE = "start_restore"
CALLBACK_START_AUTO_BACKUP = "start_auto_backup"

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates the main menu inline keyboard for the Telegram bot.

    Returns:
        InlineKeyboardMarkup: The main menu keyboard with options for admin management, server status, and settings.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧸 مدیریت ادمین‌ها", callback_data=CALLBACK_MANAGE_ADMINS),
        InlineKeyboardButton("📊 وضعیت سرور", callback_data=CALLBACK_SHOW_STATUS),
        InlineKeyboardButton("⚙️ تنظیمات و پشتیبان‌گیری", callback_data=CALLBACK_SETTINGS)
    )
    return markup

def admin_detail_keyboard(admin_id: int, status: str) -> InlineKeyboardMarkup:
    """Creates a comprehensive keyboard for managing a specific admin.

    Args:
        admin_id (int): The ID of the admin to manage.
        status (str): The current status of the admin ('active' or 'disabled').

    Returns:
        InlineKeyboardMarkup: A keyboard with options to manage admin settings, restrictions, and users.
    """
    if status not in ['active', 'disabled']:
        raise ValueError(f"Invalid admin status: {status}. Expected 'active' or 'disabled'.")

    markup = InlineKeyboardMarkup(row_width=2)
    
    # Admin Profile Settings
    markup.add(InlineKeyboardButton("📊 نحوه محاسبه حجم", callback_data=f"calc_method_menu_{admin_id}"))
    markup.add(InlineKeyboardButton("⬇️ تنظیمات مشخصات ادمین ⬇️", callback_data=CALLBACK_NOOP))
    markup.add(
        InlineKeyboardButton("♾️ حجم ادمین", callback_data=f"traffic_menu_{admin_id}"),
        InlineKeyboardButton("⏳ انقضا ادمین", callback_data=f"expiry_menu_{admin_id}")
    )
    markup.add(
        InlineKeyboardButton("🔒 امنیت", callback_data=f"security_menu_{admin_id}"),
        InlineKeyboardButton("🧸 محدودیت ساخت کاربر", callback_data=f"user_limit_menu_{admin_id}")
    )
    
    # Admin Restrictions
    markup.add(InlineKeyboardButton("⬇️ تنظیمات محدودیت‌های ادمین ⬇️", callback_data=CALLBACK_NOOP))
    status_text = "🚫 غیرفعال‌سازی کاربران" if status == 'active' else "✅ فعال‌سازی کاربران"
    status_callback = f"deactivate_users_{admin_id}" if status == 'active' else f"activate_users_{admin_id}"
    markup.add(
        InlineKeyboardButton(status_text, callback_data=status_callback),
        InlineKeyboardButton("⛔️ مدیریت دسترسی اینباند", callback_data=f"inbound_access_{admin_id}")
    )
    markup.add(
        InlineKeyboardButton("⚙️ تنظیمات اینباند", callback_data=f"inbound_settings_{admin_id}"),
        InlineKeyboardButton("🛡️ محدودیت‌های پیشرفته", callback_data=f"advanced_restrictions_{admin_id}")
    )

    # User Management
    markup.add(InlineKeyboardButton("⬇️ تنظیمات کاربران ⬇️", callback_data=CALLBACK_NOOP))
    markup.add(
        InlineKeyboardButton("➕ افزودن زمان", callback_data=f"add_time_to_users_{admin_id}"),
        InlineKeyboardButton("➖ کسر زمان", callback_data=f"subtract_time_from_users_{admin_id}")
    )
    markup.add(
        InlineKeyboardButton("➕ افزودن حجم", callback_data=f"add_traffic_to_users_{admin_id}"),
        InlineKeyboardButton("➖ کسر حجم", callback_data=f"subtract_traffic_from_users_{admin_id}")
    )
    
    # Navigation
    markup.add(
        InlineKeyboardButton("⬅️ بازگشت به لیست ادمین‌ها", callback_data=CALLBACK_MANAGE_ADMINS),
        InlineKeyboardButton("🔄 رفرش", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def calculation_method_menu_keyboard(admin_id: int, current_method: str) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting the traffic calculation method for an admin.

    Args:
        admin_id (int): The ID of the admin.
        current_method (str): The current calculation method ('used_traffic' or 'created_traffic').

    Returns:
        InlineKeyboardMarkup: A keyboard with options to set the traffic calculation method.
    """
    if current_method not in ['used_traffic', 'created_traffic']:
        raise ValueError(f"Invalid calculation method: {current_method}. Expected 'used_traffic' or 'created_traffic'.")

    markup = InlineKeyboardMarkup(row_width=1)
    used_text = "بر اساس حجم مصرفی" + (" ✅" if current_method == 'used_traffic' else "")
    created_text = "بر اساس حجم ساخته شده" + (" ✅" if current_method == 'created_traffic' else "")
    
    markup.add(
        InlineKeyboardButton(used_text, callback_data=f"set_calc_method_{admin_id}_used_traffic"),
        InlineKeyboardButton(created_text, callback_data=f"set_calc_method_{admin_id}_created_traffic"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def traffic_menu_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing an admin's traffic limits.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to add, subtract, or set unlimited traffic.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ افزودن", callback_data=f"admin_add_traffic_{admin_id}"),
        InlineKeyboardButton("➖ کسر کردن", callback_data=f"admin_subtract_traffic_{admin_id}"),
        InlineKeyboardButton("♾️ نامحدود کردن", callback_data=f"set_unlimited_traffic_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def expiry_menu_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing an admin's expiry settings.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to add, subtract, or set unlimited expiry.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ افزودن", callback_data=f"admin_add_expiry_{admin_id}"),
        InlineKeyboardButton("➖ کسر کردن", callback_data=f"admin_subtract_expiry_{admin_id}"),
        InlineKeyboardButton("♾️ نامحدود کردن", callback_data=f"set_unlimited_expiry_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def user_limit_menu_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing an admin's user creation limit.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to set or remove user creation limits.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✏️ ثبت محدودیت", callback_data=f"admin_set_user_limit_{admin_id}"),
        InlineKeyboardButton("♾️ نامحدود کردن", callback_data=f"set_unlimited_user_limit_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def security_menu_keyboard(admin_id: int, is_sudo: bool) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing an admin's security settings.

    Args:
        admin_id (int): The ID of the admin.
        is_sudo (bool): Whether the admin has sudo privileges.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to change password or toggle sudo status.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    sudo_text = "✔️ غیرفعال کردن Sudo" if is_sudo else "❌ فعال کردن Sudo"
    markup.add(
        InlineKeyboardButton("🔑 تغییر پسورد", callback_data=f"admin_change_password_{admin_id}"),
        InlineKeyboardButton(sudo_text, callback_data=f"admin_toggle_sudo_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def inbound_access_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing inbound access for an admin.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to manage inbound access.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✅ فعال کردن دسترسی", callback_data=f"enable_inbound_access_{admin_id}"),
        InlineKeyboardButton("🚫 غیرفعال کردن دسترسی", callback_data=f"disable_inbound_access_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def inbound_settings_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing inbound settings for an admin.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to configure inbound settings.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✏️ ویرایش تنظیمات اینباند", callback_data=f"edit_inbound_settings_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def advanced_restrictions_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard for managing advanced restrictions for an admin.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to configure advanced restrictions.
    """
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔧 تنظیم محدودیت‌های پیشرفته", callback_data=f"set_advanced_restrictions_{admin_id}"),
        InlineKeyboardButton("⬅️ بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}")
    )
    return markup

def back_to_admin_detail_keyboard(admin_id: int) -> InlineKeyboardMarkup:
    """Creates a keyboard to return to the admin detail menu.

    Args:
        admin_id (int): The ID of the admin.

    Returns:
        InlineKeyboardMarkup: A keyboard with a single button to return to admin details.
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ انصراف و بازگشت به جزئیات ادمین", callback_data=f"select_admin_{admin_id}"))
    return markup

def back_to_admin_management_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard to return to the admin management menu.

    Returns:
        InlineKeyboardMarkup: A keyboard with a single button to return to admin management.
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ بازگشت به مدیریت ادمین‌ها", callback_data=CALLBACK_MANAGE_ADMINS))
    return markup

def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard to return to the main menu.

    Returns:
        InlineKeyboardMarkup: A keyboard with a single button to return to the main menu.
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data=CALLBACK_MAIN_MENU))
    return markup

def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard for the settings and backup menu.

    Returns:
        InlineKeyboardMarkup: A keyboard with options for backup, restore, and auto-backup settings.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📦 تهیه بکاپ", callback_data=CALLBACK_CREATE_BACKUP),
        InlineKeyboardButton("🔄 بازیابی از بکاپ", callback_data=CALLBACK_START_RESTORE)
    )
    markup.add(
        InlineKeyboardButton("⚙️ تنظیم بکاپ خودکار", callback_data=CALLBACK_START_AUTO_BACKUP)
    )
    markup.add(
        InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data=CALLBACK_MAIN_MENU)
    )
    return markup

def confirmation_keyboard(username: str) -> InlineKeyboardMarkup:
    """Creates a confirmation keyboard for deleting an admin or user.

    Args:
        username (str): The username to delete.

    Returns:
        InlineKeyboardMarkup: A keyboard with options to confirm or cancel deletion.
    """
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ تأیید حذف", callback_data=f"confirm_delete_{username}"),
        InlineKeyboardButton("❌ لغو", callback_data="cancel_delete")
    )
    return markup