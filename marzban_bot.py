#!/usr/bin/env python3
# =================================================================
# Marzban Professional Control Bot - Final Complete Version
# Creator: @HEXMOSTAFA
# Optimized and Refactored by xAI
# Version: 7.4
# Last Updated: August 17, 2025
# =================================================================

import os
import subprocess
import logging
import sys
import tempfile
import bcrypt
from telebot import TeleBot, util
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta
import json

# --- Local Modules ---
import keyboards
import database_manager as db
from config_manager import get_config_value, save_config, load_config
from marzban_api_wrapper import MarzbanAPI

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PANEL_SCRIPT = os.path.join(SCRIPT_DIR, "marzban_panel.py")
LOG_FILE = os.path.join(SCRIPT_DIR, "marzban_bot.log")

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Initialize Bot and API ---
try:
    BOT_TOKEN = get_config_value('telegram.bot_token')
    ADMIN_CHAT_ID = int(get_config_value('telegram.admin_chat_id'))
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        raise ValueError("Telegram Bot Token or Admin Chat ID is not configured.")
    
    bot = TeleBot(BOT_TOKEN)
    marzban_api = MarzbanAPI()
except (ValueError, TypeError) as e:
    logger.critical(f"FATAL: Could not initialize bot. Check your config.json. Error: {e}")
    sys.exit(1)
except Exception as e:
    logger.critical(f"An unexpected error occurred during initialization: {e}")
    sys.exit(1)

# A simple in-memory dictionary to track user states
user_states = {}

# --- Decorators and Helpers ---
def admin_only(func):
    """Decorator to restrict access to the configured admin."""
    def wrapper(message_or_call):
        chat_id = message_or_call.chat.id if hasattr(message_or_call, 'chat') else message_or_call.message.chat.id
        if chat_id != ADMIN_CHAT_ID:
            bot.send_message(chat_id, "⛔️ شما اجازه دسترسی به این ربات را ندارید.")
            return
        return func(message_or_call)
    return wrapper

def run_panel_script(args):
    """Executes the main panel script with sudo and returns its output."""
    command = ['sudo', 'python3', MAIN_PANEL_SCRIPT] + args
    logger.info(f"Executing panel script: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        output = result.stdout + "\n" + result.stderr
        return output.strip() or "✅ عملیات با موفقیت انجام شد."
    except Exception as e:
        logger.error(f"Error executing panel script: {e}", exc_info=True)
        return f"❌ خطای اجرایی اسکریپت: {e}"

def set_user_state(chat_id, state, **kwargs):
    """Sets the state for a user."""
    user_states[chat_id] = {'state': state, **kwargs}

def clear_user_state(chat_id):
    """Clears the state for a user."""
    user_states.pop(chat_id, None)

# --- Start and Main Menu Handlers ---
@bot.message_handler(commands=['start'])
@admin_only
def send_welcome(message):
    """Handles the /start command."""
    text = "🤖 *ربات مدیریت حرفه‌ای مرزبان*\n\nبه منوی اصلی خوش آمدید."
    bot.send_message(message.chat.id, text, reply_markup=keyboards.main_menu_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
@admin_only
def handle_main_menu_callback(call):
    """Handles returning to the main menu."""
    text = "🤖 *ربات مدیریت حرفه‌ای مرزبان*\n\nبه منوی اصلی خوش آمدید:"
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboards.main_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- Centralized Admin Details Display Function ---
def refresh_admin_details(chat_id, message_id, admin_id):
    """Fetches admin info and edits the message to show updated details."""
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"🔄 در حال رفرش کردن اطلاعات ادمین...")
    
    admin_info = db.get_admin_info(admin_id)
    if not admin_info:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ اطلاعات ادمین یافت نشد.",
            reply_markup=keyboards.back_to_main_menu_keyboard()
        )
        return

    status_emoji = "✅" if admin_info.get('status', 'active') == 'active' else "⭕️"
    
    text = (
        f"👤 نام کاربری: `{admin_info['username']}`\n"
        f"▫️ آیدی ادمین: `{admin_info['id']}`\n"
        f"{status_emoji} وضعیت: `{'فعال' if admin_info.get('status') == 'active' else 'غیرفعال'}`\n"
        f"📥 حجم مصرفی: `{admin_info['used_traffic_gb']}` گیگابایت\n"
        f"🧮 حجم کل: `{admin_info['total_traffic_gb']}`\n"
        f"📃 حجم باقی‌مانده: `{admin_info['remaining_traffic_gb']}`\n"
        f"👥 تعداد مجاز به ساخت کاربر: `{admin_info['user_limit']}`\n"
        f"⏳ زمان باقی‌مانده: `{admin_info['days_left']}`\n\n"
        f"📊 *آمار کاربران:*\n"
        f"  - کل کاربران: `{admin_info.get('total_users', 0)}`\n"
        f"  - 🟢 فعال: `{admin_info.get('active_users', 0)}`\n"
        f"  - 🔴 غیرفعال: `{admin_info.get('inactive_users', 0)}`\n"
        f"  - 🔵 آنلاین: `{admin_info.get('online_users', 0)}`"
    )
            
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=keyboards.admin_detail_keyboard(admin_id, admin_info.get('status')),
        parse_mode="Markdown"
    )

# --- Admin Management Handlers ---
@bot.callback_query_handler(func=lambda call: call.data == "manage_admins")
@admin_only
def show_admin_management_menu(call):
    """Displays the admin management menu with glass button headers and admin details below."""
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🔍 در حال دریافت لیست ادمین‌ها...")
    all_admins = db.get_all_admins()
    if not all_admins:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="هیچ ادمینی یافت نشد.",
            reply_markup=keyboards.back_to_admin_management_keyboard()
        )
        return

    # دریافت اطلاعات کامل ادمین‌ها
    admin_details = {}
    for admin in all_admins:
        details = db.get_admin_info(admin['id'])
        if details:
            admin_details[admin['id']] = details

    # ساخت کیبورد با دکمه‌های سرستون (بدون عملکرد)
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("👤 یوزرنیم", callback_data="noop"),
        InlineKeyboardButton("📊 حجم باقی‌مانده", callback_data="noop"),
        InlineKeyboardButton("⏳ زمان باقی‌مانده", callback_data="noop")
    )

    # افزودن اطلاعات ادمین‌ها با دکمه‌های سه‌ستونه
    for admin_id, details in admin_details.items():
        remaining_traffic = f"{details['remaining_traffic_gb']} GB" if details['remaining_traffic_gb'] != "نامحدود" else "♾️"
        days_left = f"{details['days_left']} روز" if details['days_left'] != "نامحدود" else "♾️"
        markup.add(
            InlineKeyboardButton(f"👤 {details['username']}", callback_data=f"select_admin_{admin_id}"),
            InlineKeyboardButton(f"📊 {remaining_traffic}", callback_data=f"select_admin_{admin_id}"),
            InlineKeyboardButton(f"⏳ {days_left}", callback_data=f"select_admin_{admin_id}")
        )

    # افزودن دکمه‌های حذف و ساخت ادمین
    markup.add(
        InlineKeyboardButton("🗑️ حذف ادمین", callback_data="delete_admin"),
        InlineKeyboardButton("➕ ساخت ادمین", callback_data="add_new_admin")
    )
    markup.add(InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data="main_menu"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🛡️ *مدیریت ادمین‌ها*",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "add_new_admin")
@admin_only
def start_add_new_admin(call):
    """Starts the process of adding a new admin with a unique step-by-step method."""
    set_user_state(call.message.chat.id, 'awaiting_admin_username', menu_message_id=call.message.message_id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="➕ *ساخت ادمین جدید - مرحله 1*\n\nلطفاً نام کاربری ادمین جدید (حداقل 3 کاراکتر) را وارد کنید:",
        reply_markup=keyboards.back_to_admin_management_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "delete_admin")
@admin_only
def show_admin_list_for_delete(call):
    """Displays the list of admins for deletion."""
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🔍 در حال دریافت لیست ادمین‌ها برای حذف...")
    all_admins = db.get_all_admins()
    if not all_admins:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="هیچ ادمینی یافت نشد.",
            reply_markup=keyboards.back_to_admin_management_keyboard()
        )
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for admin in all_admins:
        markup.add(InlineKeyboardButton(f"🗑️ حذف {admin['username']}", callback_data=f"prepare_delete_admin_{admin['id']}"))
    markup.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="manage_admins"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👇 ادمین مورد نظر برای حذف را انتخاب کنید:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("prepare_delete_admin_"))
@admin_only
def prepare_delete_admin(call):
    """Prepares for admin deletion by asking for confirmation."""
    admin_id = int(call.data.split('_')[-1])
    admin_info = db.get_admin_info(admin_id)
    if not admin_info:
        bot.answer_callback_query(call.id, "❌ ادمین یافت نشد.", show_alert=True)
        return

    text = f"آیا مطمئن هستید که می‌خواهید ادمین {admin_info['username']} را حذف کنید؟"
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboards.confirmation_keyboard(admin_info['username'])
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
@admin_only
def confirm_delete_admin(call):
    """Confirms and deletes the admin."""
    username = call.data.split('_')[-1]
    admin_info = next((a for a in db.get_all_admins() if a['username'] == username), None)
    if admin_info and db.delete_admin(admin_info['id']):
        bot.answer_callback_query(call.id, f"✅ ادمین {username} با موفقیت حذف شد.", show_alert=True)
    else:
        bot.answer_callback_query(call.id, f"❌ خطا در حذف ادمین {username}.", show_alert=True)
    show_admin_management_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
@admin_only
def cancel_delete(call):
    """Cancels the deletion."""
    bot.answer_callback_query(call.id, "❌ عملیات حذف لغو شد.", show_alert=True)
    show_admin_management_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "list_admins")
@admin_only
def show_admin_list(call):
    """Displays the list of admins."""
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🔍 در حال دریافت لیست ادمین‌ها...")
    all_admins = db.get_all_admins()
    if not all_admins:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="هیچ ادمینی یافت نشد.",
            reply_markup=keyboards.back_to_admin_management_keyboard()
        )
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for admin in all_admins:
        markup.add(InlineKeyboardButton(f"👤 {admin['username']}", callback_data=f"select_admin_{admin['id']}"))
    markup.add(InlineKeyboardButton("⬅️ بازگشت به مدیریت ادمین‌ها", callback_data="manage_admins"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👇 ادمین مورد نظر را انتخاب کنید:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "edit_admin")
@admin_only
def show_admin_list_for_edit(call):
    """Displays the list of admins for editing."""
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="🔍 در حال دریافت لیست ادمین‌ها برای ویرایش...")
    all_admins = db.get_all_admins()
    if not all_admins:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="هیچ ادمینی یافت نشد.",
            reply_markup=keyboards.back_to_admin_management_keyboard()
        )
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for admin in all_admins:
        markup.add(InlineKeyboardButton(f"✏️ ویرایش {admin['username']}", callback_data=f"select_admin_{admin['id']}"))
    markup.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="manage_admins"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👇 ادمین مورد نظر برای ویرایش را انتخاب کنید:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_admin_"))
@admin_only
def show_admin_details(call):
    """Handles the callback for selecting an admin and displays all management options."""
    admin_id = int(call.data.split('_')[-1])
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"🔄 در حال رفرش کردن اطلاعات ادمین...")
    
    admin_info = db.get_admin_info(admin_id)
    if not admin_info:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ اطلاعات ادمین یافت نشد.",
            reply_markup=keyboards.back_to_main_menu_keyboard()
        )
        return

    status_emoji = "✅" if admin_info.get('status', 'active') == 'active' else "⭕️"
    remaining_traffic = f"{admin_info['remaining_traffic_gb']} GB" if admin_info['remaining_traffic_gb'] != "نامحدود" else "♾️"
    days_left = f"{admin_info['days_left']} روز" if admin_info['days_left'] != "نامحدود" else "♾️"

    text = (
        f"👤 نام کاربری: `{admin_info['username']}`\n"
        f"▫️ آیدی ادمین: `{admin_info['id']}`\n"
        f"{status_emoji} وضعیت: `{'فعال' if admin_info.get('status') == 'active' else 'غیرفعال'}`\n"
        f"📥 حجم مصرفی: `{admin_info['used_traffic_gb']}` گیگابایت\n"
        f"🧮 حجم کل: `{admin_info['total_traffic_gb']}`\n"
        f"📃 حجم باقی‌مانده: `{remaining_traffic}`\n"
        f"👥 تعداد مجاز به ساخت کاربر: `{admin_info['user_limit']}`\n"
        f"⏳ زمان باقی‌مانده: `{days_left}`\n\n"
        f"📊 *آمار کاربران:*\n"
        f"  - کل کاربران: `{admin_info.get('total_users', 0)}`\n"
        f"  - 🟢 فعال: `{admin_info.get('active_users', 0)}`\n"
        f"  - 🔴 غیرفعال: `{admin_info.get('inactive_users', 0)}`\n"
        f"  - 🔵 آنلاین: `{admin_info.get('online_users', 0)}`"
    )
            
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        reply_markup=keyboards.admin_detail_keyboard(admin_id, admin_info.get('status')),
        parse_mode="Markdown"
    )

# --- Sub-Menu Handlers ---
@bot.callback_query_handler(func=lambda call: call.data.endswith(("_menu", "_menu_")) or "_menu_" in call.data)
@admin_only
def handle_sub_menus(call):
    """Handles all sub-menu callbacks in the admin detail view."""
    parts = call.data.split('_menu_')
    if len(parts) != 2:
        bot.answer_callback_query(call.id, "❌ خطای ناشناخته در منو.", show_alert=True)
        return

    menu_type, admin_id_str = parts
    admin_id = int(admin_id_str)
    
    admin_info = db.get_admin_info(admin_id)
    if not admin_info:
        bot.answer_callback_query(call.id, "❌ ادمین یافت نشد.", show_alert=True)
        return
        
    menu_map = {
        "traffic": ("♾️ گزینه‌های مدیریت حجم ادمین:", keyboards.traffic_menu_keyboard(admin_id)),
        "expiry": ("⏳ گزینه‌های مدیریت انقضای ادمین:", keyboards.expiry_menu_keyboard(admin_id)),
        "user_limit": ("🧸 گزینه‌های محدودیت ساخت کاربر:", keyboards.user_limit_menu_keyboard(admin_id)),
        "security": ("🔒 گزینه‌های امنیتی:", keyboards.security_menu_keyboard(admin_id, admin_info.get('is_sudo'))),
        "calc_method": ("📊 نحوه محاسبه حجم مصرفی ادمین:", keyboards.calculation_method_menu_keyboard(admin_id, admin_info.get('calculate_volume')))
    }
    
    if menu_type in menu_map:
        text, keyboard = menu_map[menu_type]
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=keyboard)
    else:
        bot.answer_callback_query(call.id, "❌ منوی انتخاب‌شده نامعتبر است.", show_alert=True)
        refresh_admin_details(call.message.chat.id, call.message.message_id, admin_id)

# --- Backup & Restore Handlers ---
@bot.callback_query_handler(func=lambda call: call.data == "settings")
@admin_only
def show_settings_menu(call):
    """Displays the backup and restore settings menu."""
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⚙️ *تنظیمات و پشتیبان‌گیری*\n\nلطفاً عملیات مورد نظر خود را انتخاب کنید.",
        reply_markup=keyboards.settings_menu_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_backup")
@admin_only
def create_backup_handler(call):
    bot.answer_callback_query(call.id, "درخواست بکاپ ارسال شد...", show_alert=False)
    bot.send_message(call.message.chat.id, "⏳ در حال شروع فرآیند کامل پشتیبان‌گیری... این عملیات ممکن است چند دقیقه طول بکشد.")
    result = run_panel_script(['run-backup'])
    bot.send_message(call.message.chat.id, f"*گزارش پشتیبان‌گیری:*\n\n`{result}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "start_restore")
@admin_only
def start_restore_handler(call):
    set_user_state(call.message.chat.id, 'awaiting_restore_file')
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔄 *شروع فرآیند بازیابی*\n\nلطفاً فایل بکاپ (`.tar.gz`) خود را ارسال کنید.",
        reply_markup=keyboards.back_to_main_menu_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "start_auto_backup")
@admin_only
def start_auto_backup_handler(call):
    """Handles the prompt for setting up automatic backups."""
    set_user_state(call.message.chat.id, 'awaiting_backup_interval', menu_message_id=call.message.message_id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="⚙️ *تنظیم بکاپ خودکار*\n\nلطفاً بازه زمانی بکاپ خودکار را به **دقیقه** وارد کنید (مثلاً: 60 برای هر ساعت).",
        reply_markup=keyboards.back_to_main_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- Handlers for Actions without User Text Input ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("set_unlimited_", "admin_toggle_sudo_", "set_calc_method_")))
@admin_only
def handle_quick_actions(call):
    """Handles actions that do not require further user input."""
    parts = call.data.split('_')
    bot.answer_callback_query(call.id, "⏳ در حال اعمال تغییرات...")
    
    if call.data.startswith("set_calc_method_"):
        admin_id = int(parts[3])
        new_method = parts[4]
        db.set_admin_traffic_calculation(admin_id, new_method)
    else:
        admin_id = int(parts[-1])
        if call.data.startswith("set_unlimited_"):
            setting_type = parts[2]
            if setting_type == "traffic": db.set_admin_traffic_unlimited(admin_id)
            elif setting_type == "expiry": db.set_admin_expiry_unlimited(admin_id)
            elif setting_type == "user_limit": db.set_admin_user_limit(admin_id, None)
        elif call.data.startswith("admin_toggle_sudo_"):
            admin_info = db.get_admin_info(admin_id)
            db.update_admin_sudo(admin_id, not admin_info.get('is_sudo'))

    refresh_admin_details(call.message.chat.id, call.message.message_id, admin_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("deactivate_users_", "activate_users_")))
@admin_only
def handle_toggle_users_status(call):
    """Handles activating or deactivating all users of an admin via API."""
    action, admin_id_str = call.data.rsplit('_', 1)
    admin_id = int(admin_id_str)
    new_status = 'disabled' if action == 'deactivate_users' else 'active'
    
    bot.answer_callback_query(call.id, "⏳ در حال ارسال دستور به پنل مرزبان...")
    
    try:
        admin_info = db.get_admin_info(admin_id)
        if new_status == 'disabled':
            response = marzban_api.disable_all_active_users(admin_info['username'])
        else:
            response = marzban_api.activate_all_disabled_users(admin_info['username'])
        
        if "detail" in response and "successful" in response['detail'].lower():
            db.set_admin_users_status(admin_id, new_status)
            bot.answer_callback_query(call.id, "✅ عملیات با موفقیت انجام شد.")
        else:
            logger.error(f"API call to toggle user status failed: {response.get('detail')}")
            bot.answer_callback_query(call.id, f"❌ عملیات API ناموفق بود.", show_alert=True)
            return
    except Exception as e:
        logger.error(f"API call to toggle user status failed: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در ارتباط با API مرزبان.", show_alert=True)
        return
        
    refresh_admin_details(call.message.chat.id, call.message.message_id, admin_id)

# --- Handlers that Require User Text Input ---
@bot.callback_query_handler(func=lambda call: call.data.startswith(("add_", "subtract_", "admin_")))
@admin_only
def handle_input_prompts(call):
    """Sets user state and prompts for text input for various actions."""
    state_key = call.data.rsplit('_', 1)[0]
    admin_id = int(call.data.split('_')[-1])
    
    prompts = {
        "add_traffic_to_users": "➕ لطفاً مقدار حجم (GB) برای *افزودن* به *تمام کاربران* این ادمین را وارد کنید:",
        "subtract_traffic_from_users": "➖ لطفاً مقدار حجم (GB) برای *کسر* از *تمام کاربران* این ادمین را وارد کنید:",
        "add_time_to_users": "➕ لطفاً تعداد روز برای *افزودن* به انقضای *تمام کاربران* این ادمین را وارد کنید:",
        "subtract_time_from_users": "➖ لطفاً تعداد روز برای *کسر* از انقضای *تمام کاربران* این ادمین را وارد کنید:",
        "admin_add_traffic": "➕ لطفاً مقدار حجم (GB) برای *افزودن* به خود ادمین را وارد کنید:",
        "admin_subtract_traffic": "➖ لطفاً مقدار حجم (GB) برای *کسر* از خود ادمین را وارد کنید:",
        "admin_add_expiry": "➕ لطفاً تعداد روز برای *افزودن* به انقضای خود ادمین را وارد کنید:",
        "admin_subtract_expiry": "➖ لطفاً تعداد روز برای *کسر* از انقضای خود ادمین را وارد کنید:",
        "admin_set_user_limit": "🧸 لطفاً تعداد مجاز ساخت کاربر برای این ادمین را وارد کنید:",
        "admin_change_password": "🔑 لطفاً پسورد جدید برای این ادمین را وارد کنید:",
    }
    
    if state_key in prompts:
        set_user_state(call.message.chat.id, state=state_key, admin_id=admin_id, menu_message_id=call.message.message_id)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=prompts[state_key], reply_markup=keyboards.back_to_admin_detail_keyboard(admin_id), parse_mode="Markdown")

# --- Message Handler & Input Processors ---
@bot.message_handler(content_types=['text', 'document'], func=lambda message: message.chat.id in user_states)
@admin_only
def handle_stateful_messages(message):
    """Main router for messages when a user is in a specific state."""
    chat_id = message.chat.id
    state_info = user_states.get(chat_id)
    if not state_info: return

    state = state_info['state']
    
    if state == 'awaiting_restore_file':
        process_restore_file(message)
        return
    elif state == 'awaiting_admin_username':
        process_admin_username(message)
        return
    elif state == 'awaiting_admin_password':
        process_admin_password(message)
        return
        
    if message.content_type == 'text':
        value = message.text
        admin_id = state_info.get('admin_id')
        menu_message_id = state_info.get('menu_message_id')
        
        try: bot.delete_message(chat_id, message.message_id)
        except Exception: pass
        
        clear_user_state(chat_id)
        
        handler_map = {
            "add_traffic_to_users": process_users_traffic_update,
            "subtract_traffic_from_users": process_users_traffic_update,
            "add_time_to_users": process_users_expiry_update,
            "subtract_time_from_users": process_users_expiry_update,
            "admin_add_traffic": process_admin_traffic_update,
            "admin_subtract_traffic": process_admin_traffic_update,
            "admin_add_expiry": process_admin_expiry_update,
            "admin_subtract_expiry": process_admin_expiry_update,
            "admin_set_user_limit": process_admin_user_limit_update,
            "admin_change_password": process_admin_password_update,
            "awaiting_backup_interval": process_backup_interval,
        }

        if state in handler_map:
            if state == "awaiting_backup_interval":
                handler_map[state](chat_id, menu_message_id, value)
            else:
                handler_map[state](chat_id, menu_message_id, state, value, admin_id)

def process_users_traffic_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        amount_gb = float(value)
        if "subtract" in state: amount_gb = -amount_gb
        db.update_users_of_admin_traffic(admin_id, amount_gb)
        bot.send_message(chat_id, f"✅ حجم کاربران با موفقیت به‌روزرسانی شد.", delete_in=5)
    except ValueError: 
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً یک عدد معتبر وارد کنید.", delete_in=5)
    finally: 
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_users_expiry_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        days = int(value)
        if "subtract" in state: days = -days
        db.update_users_of_admin_expiry(admin_id, days)
        bot.send_message(chat_id, f"✅ انقضای کاربران با موفقیت به‌روزرسانی شد.", delete_in=5)
    except ValueError: 
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.", delete_in=5)
    finally: 
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_admin_traffic_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        amount_gb = float(value)
        if "subtract" in state: amount_gb = -amount_gb
        db.update_admin_traffic(admin_id, amount_gb)
        bot.send_message(chat_id, f"✅ حجم ادمین با موفقیت به‌روزرسانی شد.", delete_in=5)
    except ValueError: 
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً یک عدد معتبر وارد کنید.", delete_in=5)
    finally: 
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_admin_expiry_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        days = int(value)
        if "subtract" in state: days = -days
        db.update_admin_expiry(admin_id, days)
        bot.send_message(chat_id, f"✅ انقضای ادمین با موفقیت به‌روزرسانی شد.", delete_in=5)
    except ValueError: 
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.", delete_in=5)
    finally: 
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_admin_user_limit_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        limit = int(value)
        if limit < 0: raise ValueError
        db.set_admin_user_limit(admin_id, limit)
        blocked_admin_ids = db.get_blocked_admin_ids()
        if not db.update_user_creation_trigger(blocked_admin_ids):
            raise Exception("Failed to update user creation trigger.")
        bot.send_message(chat_id, f"✅ محدودیت تعداد کاربر به {limit} تنظیم شد.", delete_in=5)
    except ValueError: 
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً یک عدد صحیح و مثبت وارد کنید.", delete_in=5)
    except Exception as e:
        logger.error(f"Failed to update user limit for admin {admin_id}: {e}")
        bot.send_message(chat_id, f"❌ خطا در تنظیم محدودیت: {e}", delete_in=5)
    finally: 
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_admin_password_update(chat_id, menu_message_id, state, value, admin_id):
    try:
        password = value.encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt(rounds=10)).decode('utf-8')
        if db.update_admin_password(admin_id, hashed_password):
            bot.send_message(chat_id, "✅ پسورد با موفقیت تغییر کرد.", delete_in=5)
        else:
            raise Exception("DB update failed")
    except Exception as e:
        logger.error(f"Password update failed: {e}")
        bot.send_message(chat_id, "❌ خطا در تغییر پسورد.", delete_in=5)
    finally:
        refresh_admin_details(chat_id, menu_message_id, admin_id)

def process_backup_interval(chat_id, menu_message_id, value):
    try:
        interval = int(value)
        if interval <= 0: raise ValueError
        
        config = load_config() or {}
        config.setdefault('telegram', {})['backup_interval'] = str(interval)
        save_config(config)

        bot.edit_message_text(chat_id=chat_id, message_id=menu_message_id, text=f"✅ بازه زمانی به {interval} دقیقه تنظیم شد. در حال تنظیم Cronjob...")
        
        result_message = run_panel_script(['do-auto-backup-setup'])
        bot.send_message(chat_id, f"✨ *گزارش راه‌اندازی بکاپ خودکار:*\n\n`{result_message}`", parse_mode="Markdown")
    except ValueError:
        bot.send_message(chat_id, "❌ ورودی نامعتبر است. لطفاً فقط عدد صحیح و مثبت وارد کنید.", delete_in=5)
    finally:
        class DummyCall:
            def __init__(self, chat_id, msg_id):
                self.message = type("Message", (), {"chat": type("Chat", (), {"id": chat_id})(), "message_id": msg_id})()
                self.data = 'main_menu'
        handle_main_menu_callback(DummyCall(chat_id, menu_message_id))

def process_restore_file(message):
    chat_id = message.chat.id
    clear_user_state(chat_id)
    if message.content_type != 'document' or not message.document.file_name.endswith('.tar.gz'):
        bot.send_message(chat_id, "❌ فایل نامعتبر است. لطفاً یک فایل با فرمت `.tar.gz` ارسال کنید.", reply_markup=keyboards.main_menu_keyboard())
        return
    temp_file_path = None
    try:
        bot.send_message(chat_id, "✅ فایل دریافت شد. در حال دانلود و شروع فرآیند بازیابی...")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as temp_file:
            temp_file.write(downloaded_file)
            temp_file_path = temp_file.name

        bot.send_message(chat_id, "⏳ بازیابی در حال انجام است... این عملیات بسیار حساس است و ممکن است چندین دقیقه طول بکشد.")
        result_message = run_panel_script(['do-restore', temp_file_path])
        bot.send_message(chat_id, f"✨ *گزارش فرآیند بازیابی:*\n\n`{result_message}`", parse_mode="Markdown", reply_markup=keyboards.main_menu_keyboard())
    
    except Exception as e:
        logger.error(f"Restore process failed: {e}", exc_info=True)
        bot.send_message(chat_id, f"❌ خطایی حیاتی در فرآیند بازیابی رخ داد: {e}", reply_markup=keyboards.main_menu_keyboard())
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        clear_user_state(chat_id)

def process_admin_username(message):
    """Processes the username for adding a new admin."""
    username = message.text.strip()
    if not username or len(username) < 3:
        bot.send_message(message.chat.id, "❌ نام کاربری نامعتبر است. حداقل 3 کاراکتر وارد کنید.")
        return
    set_user_state(message.chat.id, 'awaiting_admin_password', username=username, menu_message_id=user_states[message.chat.id]['menu_message_id'])
    bot.delete_message(message.chat.id, message.message_id)
    bot.send_message(message.chat.id, f"نام کاربری: {username}\n\n🔑 لطفاً پسورد ادمین جدید را وارد کنید (حداقل 6 کاراکتر):")

def process_admin_password(message):
    """Processes the password for adding a new admin."""
    chat_id = message.chat.id
    username = user_states[chat_id]['username']
    menu_message_id = user_states[chat_id]['menu_message_id']
    password = message.text.strip()
    if not password or len(password) < 6:
        bot.send_message(chat_id, "❌ پسورد نامعتبر است. حداقل 6 کاراکتر وارد کنید.")
        return
    try:
        if db.add_new_admin(username, password):
            bot.send_message(chat_id, f"✅ ادمین {username} با موفقیت اضافه شد.", delete_in=5)
            # Optionally sync with Marzban API if needed
            try:
                marzban_api.create_admin(username, password)
            except Exception as e:
                logger.error(f"Failed to sync new admin with Marzban API: {e}")
        else:
            bot.send_message(chat_id, f"❌ خطا در افزودن ادمین {username}.", delete_in=5)
    except Exception as e:
        logger.error(f"Failed to add admin {username}: {e}")
        bot.send_message(chat_id, f"❌ خطا در افزودن ادمین {username}: {e}", delete_in=5)
    finally:
        clear_user_state(chat_id)
        bot.delete_message(chat_id, message.message_id)
        class DummyCall:
            def __init__(self, chat_id, msg_id):
                self.message = type("Message", (), {"chat": type("Chat", (), {"id": chat_id})(), "message_id": msg_id})()
                self.data = 'manage_admins'
        show_admin_management_menu(DummyCall(chat_id, menu_message_id))

# --- Fallback and Main Loop ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("noop"))
@admin_only
def handle_noop(call):
    bot.answer_callback_query(call.id, "این دکمه صرفاً نمایشی است.", show_alert=False)

@bot.callback_query_handler(func=lambda call: call.data == "noop_placeholder")
@admin_only
def handle_noop_placeholder(call):
    bot.answer_callback_query(call.id, "این قابلیت هنوز پیاده‌سازی نشده است.", show_alert=True)

if __name__ == '__main__':
    try:
        import bcrypt
    except ImportError:
        logger.critical("Bcrypt library not found. Please run: pip install bcrypt")
        sys.exit(1)
        
    logger.info("Marzban Control Bot (Advanced) is starting...")
    bot.set_my_commands([BotCommand("start", "شروع و نمایش منوی اصلی")])
    util.logger.setLevel(logging.INFO) 
    bot.infinity_polling(timeout=10, long_polling_timeout=5)