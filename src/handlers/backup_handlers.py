from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from backup_manager import BackupManager
import config

backup_router = Router()
backup_manager = BackupManager()

@backup_router.callback_query(F.data == "backup_create")
async def create_backup(callback: CallbackQuery):
    if callback.from_user.id not in config.SUDO_ADMINS:
        await callback.answer("ØºÛŒØ±Ù…Ø¬Ø§Ø²", show_alert=True)
        return
    success, message = backup_manager.create_backup()
    await callback.message.edit_text(
        config.MESSAGES["backup_success"].format(filename=message) if success else config.MESSAGES["backup_error"].format(error=message),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=config.BUTTONS["back"], callback_data="sudo_menu")]])
    )
    await callback.answer()

@backup_router.callback_query(F.data == "backup_restore")
async def list_backups(callback: CallbackQuery):
    if callback.from_user.id not in config.SUDO_ADMINS:
        await callback.answer("ØºÛŒØ±Ù…Ø¬Ø§Ø²", show_alert=True)
        return
    backups = backup_manager.list_backups()
    if not backups:
        await callback.message.edit_text("Ù‡ÛŒÚ† Ø¨Ú©Ø§Ù¾ÛŒ ÛŒØ§ÙØª Ù†Ø´Ø¯.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=config.BUTTONS["back"], callback_data="sudo_menu")]]))
        return
    buttons = [[InlineKeyboardButton(text=b, callback_data=f"restore_{b}")] for b in backups]
    buttons.append([InlineKeyboardButton(text=config.BUTTONS["back"], callback_data="sudo_menu")])
    await callback.message.edit_text("Ø§Ù†ØªØ®Ø§Ø¨ Ø¨Ú©Ø§Ù¾ Ø¨Ø±Ø§ÛŒ Ø±ÛŒØ³ØªÙˆØ±:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@backup_router.callback_query(F.data.startswith("restore_"))
async def restore_backup(callback: CallbackQuery):
    if callback.from_user.id not in config.SUDO_ADMINS:
        await callback.answer("ØºÛŒØ±Ù…Ø¬Ø§Ø²", show_alert=True)
        return
    backup_filename = callback.data.split("_", 1)[1]
    success, message = backup_manager.restore_backup(backup_filename)
    await callback.message.edit_text(
        config.MESSAGES["restore_success"] if success else config.MESSAGES["restore_error"].format(error=message),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=config.BUTTONS["back"], callback_data="sudo_menu")]])
    )
    await callback.answer()
