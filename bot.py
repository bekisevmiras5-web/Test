#!/usr/bin/env python3
"""
Telegram Bot для передачи данных между устройствами
Размещен на Railway.app + GitHub
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import os
import sqlite3
from datetime import datetime
import sys

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DATA_FILE = "/data/device_data.json"  # Railway предоставляет папку /data
DB_FILE = "/data/devices.db"

# Создаем папку /data если её нет
os.makedirs("/data", exist_ok=True)

# Инициализация БД
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  registered TEXT)''')
    conn.commit()
    conn.close()
    logger.info(f"База данных инициализирована: {DB_FILE}")

def save_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO devices 
                 (user_id, username, first_name, last_name, registered)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, first_name, last_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM devices")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

async def send_hello_to_all(context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    if not users:
        return 0
    
    count = 0
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="hello",
                parse_mode=None
            )
            count += 1
            logger.info(f"Отправлено 'hello' пользователю {user_id}")
        except Exception as e:
            logger.error(f"Не удалось отправить hello пользователю {user_id}: {e}")
    
    return count

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"last_input": None, "started": datetime.now().isoformat()}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Бот размещен на облачном сервере (GitHub + Railway)\n"
        "✅ Работает 24/7 без перерывов\n\n"
        "📋 Команды:\n"
        "• /input 10 20 30 - сохранить числа\n"
        "• /output - получить последние числа\n"
        "• /clear - очистить данные\n"
        "• /users - сколько устройств подключено\n"
        "• /status - статус бота\n\n"
        "⚡ При вводе чисел всем устройствам придет 'hello'"
    )

async def input_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    
    if not context.args:
        await update.message.reply_text("Напиши числа через пробел: /input 10 20 30")
        return
    
    numbers = []
    for arg in context.args:
        try:
            num = int(arg)
            numbers.append(str(num))
        except ValueError:
            try:
                num = float(arg)
                numbers.append(str(num))
            except ValueError:
                await update.message.reply_text(f"❌ '{arg}' не число")
                return
    
    data = load_data()
    data["last_input"] = " ".join(numbers)
    data["last_update"] = datetime.now().isoformat()
    save_data(data)
    
    # Отправляем hello всем
    count = await send_hello_to_all(context)
    
    await update.message.reply_text(
        f"✅ Сохранено: {' '.join(numbers)}\n"
        f"📢 Отправлено 'hello' {count} устройствам"
    )
    logger.info(f"Пользователь {user.id} сохранил: {' '.join(numbers)}")

async def output_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    
    data = load_data()
    
    if not data.get("last_input"):
        await update.message.reply_text("📭 Нет сохраненных данных")
        return
    
    numbers = data["last_input"]
    await update.message.reply_text(f"📊 Данные: {numbers}")

async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["last_input"] = None
    data["cleared_at"] = datetime.now().isoformat()
    save_data(data)
    
    await update.message.reply_text("🗑️ Данные очищены")
    logger.info(f"Пользователь {update.effective_user.id} очистил данные")

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    count = len(users)
    
    if count == 0:
        await update.message.reply_text("📱 Нет подключенных устройств")
        return
    
    await update.message.reply_text(
        f"📱 Подключено устройств: {count}\n"
        f"🔢 ID первых 10: {', '.join(map(str, users[:10]))}"
        + (f"\n...и ещё {count-10}" if count > 10 else "")
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_count = len(get_all_users())
    data = load_data()
    
    status_text = (
        f"🤖 БОТ СТАТУС\n"
        f"━━━━━━━━━━━━\n"
        f"• Сервер: Railway.app 🚄\n"
        f"• Устройств: {users_count} 📱\n"
        f"• Данные: {'✅ Есть' if data.get('last_input') else '❌ Нет'}\n"
        f"• Запущен: {data.get('started', 'неизвестно')}\n"
        f"• Время: {datetime.now().strftime('%H:%M:%S')} ⏰"
    )
    
    await update.message.reply_text(status_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

def main():
    # Твой токен бота
    TOKEN = "8433217743:AAHd8WqL2qjJh2l2AhYPysdrh7jE0dncy8c"
    
    # Инициализация
    init_db()
    logger.info("Инициализация базы данных завершена")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("input", input_data))
    app.add_handler(CommandHandler("output", output_data))
    app.add_handler(CommandHandler("clear", clear_data))
    app.add_handler(CommandHandler("users", show_users))
    app.add_handler(CommandHandler("status", status))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("🚀 Бот запускается на Railway...")
    logger.info(f"Токен: {TOKEN[:10]}...")
    
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
