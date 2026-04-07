import asyncio
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Фикс для Python 3.14
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

TOKEN = "8727038230:AAGeSWwD5Y66ALmz_45K7AckDE7jY8lzOSQ"

# ===== FLASK ДЛЯ RENDER (ЧТОБЫ БОТ НЕ УСЫПАЛ) =====
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "Бот работает!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()
# ===== КОНЕЦ БЛОКА FLASK =====

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, 'schedule_data.json')

def load_schedule():
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_week_parity():
    data = load_schedule()
    start_date_str = data.get("date_start", "2026-02-02")
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    days_passed = (datetime.now().date() - start_date.date()).days
    week_number = (days_passed // 7) + 1
    if week_number <= 0:
        week_number = 1
    return ("even", week_number) if week_number % 2 == 0 else ("odd", week_number)

def get_weekday_name():
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return weekdays[datetime.now().weekday()]

def get_weekday_name_for_date(days_ahead=0):
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    target_date = datetime.now() + timedelta(days=days_ahead)
    return weekdays[target_date.weekday()]

def format_schedule(day_name, schedule_data, parity, week_number):
    day_schedule = schedule_data.get(day_name, {})
    lessons = day_schedule.get(parity, [])
    parity_text = "ЧЁТНАЯ" if parity == "even" else "НЕЧЁТНАЯ"
    
    if not lessons:
        return f"📭 <b>{day_name}</b> ({parity_text} неделя, №{week_number})\n\nПар нет"
    
    result = f"📚 <b>{day_name}</b>\n📌 {parity_text} неделя (№{week_number})\n\n"
    for lesson in lessons:
        result += f"⏰ <b>{lesson['time']}</b>\n"
        result += f"📖 {lesson['subject']}\n"
        if lesson.get('teacher'):
            result += f"👨‍🏫 {lesson['teacher']}\n"
        if lesson.get('room'):
            result += f"🏛 Ауд. {lesson['room']}\n"
        result += "─────────────\n"
    return result

def format_full_week(schedule_data, parity, week_number):
    weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    parity_text = "ЧЁТНАЯ" if parity == "even" else "НЕЧЁТНАЯ"
    result = f"🗓 <b>Расписание на неделю</b>\n📌 {parity_text} неделя (№{week_number})\n\n"
    
    for day in weekdays:
        day_schedule = schedule_data.get(day, {})
        lessons = day_schedule.get(parity, [])
        result += f"<b>{day}</b>\n"
        if lessons:
            for lesson in lessons:
                result += f"  ⏰ {lesson['time']} — {lesson['subject']}"
                if lesson.get('room'):
                    result += f" (ауд.{lesson['room']})"
                result += "\n"
                if lesson.get('teacher'):
                    result += f"     👨‍🏫 {lesson['teacher']}\n"
        else:
            result += "  📭 Нет пар\n"
        result += "\n"
    return result

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Сегодня", callback_data='today')],
        [InlineKeyboardButton("📆 Завтра", callback_data='tomorrow')],
        [InlineKeyboardButton("🗓 Вся неделя", callback_data='week')],
        [InlineKeyboardButton("🔄 Какая неделя?", callback_data='current_week')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parity, week_num = get_week_parity()
    parity_text = "чётная" if parity == "even" else "нечётная"
    await update.message.reply_text(
        f"🎓 <b>Привет!</b>\n\n📌 Сейчас <b>{parity_text}</b> неделя (№{week_num})\n\n👇 Выбери действие:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_schedule()
    parity, week_num = get_week_parity()
    message = format_schedule(get_weekday_name(), data, parity, week_num)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=get_main_keyboard())

async def tomorrow_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_schedule()
    parity, week_num = get_week_parity()
    message = format_schedule(get_weekday_name_for_date(1), data, parity, week_num)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=get_main_keyboard())

async def week_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_schedule()
    parity, week_num = get_week_parity()
    message = format_full_week(data, parity, week_num)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=get_main_keyboard())

async def current_week_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parity, week_num = get_week_parity()
    parity_text = "чётная" if parity == "even" else "нечётная"
    data = load_schedule()
    start_date = data.get("date_start", "2026-02-02")
    await update.message.reply_text(
        f"📅 <b>Текущая неделя</b>\n\n• Тип: <b>{parity_text}</b>\n• Номер: <b>{week_num}</b>\n• Начало семестра: <b>{start_date}</b>",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_schedule()
    parity, week_num = get_week_parity()
    
    if query.data == 'today':
        message = format_schedule(get_weekday_name(), data, parity, week_num)
        await query.edit_message_text(message, parse_mode='HTML')
        await query.message.reply_text("👇 Выбери действие:", reply_markup=get_main_keyboard())
    elif query.data == 'tomorrow':
        message = format_schedule(get_weekday_name_for_date(1), data, parity, week_num)
        await query.edit_message_text(message, parse_mode='HTML')
        await query.message.reply_text("👇 Выбери действие:", reply_markup=get_main_keyboard())
    elif query.data == 'week':
        message = format_full_week(data, parity, week_num)
        await query.edit_message_text(message, parse_mode='HTML')
        await query.message.reply_text("👇 Выбери действие:", reply_markup=get_main_keyboard())
    elif query.data == 'current_week':
        parity_text = "чётная" if parity == "even" else "нечётная"
        start_date = data.get("date_start", "2026-02-02")
        message = f"📅 <b>Текущая неделя</b>\n\n• Тип: <b>{parity_text}</b>\n• Номер: <b>{week_num}</b>\n• Начало семестра: <b>{start_date}</b>"
        await query.edit_message_text(message, parse_mode='HTML')
        await query.message.reply_text("👇 Выбери действие:", reply_markup=get_main_keyboard())
    elif query.data == 'menu':
        parity, week_num = get_week_parity()
        parity_text = "чётная" if parity == "even" else "нечётная"
        await query.edit_message_text(
            f"🎓 <b>Главное меню</b>\n\n📌 Сейчас <b>{parity_text}</b> неделя (№{week_num})\n\n👇 Выбери действие:",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Команды:</b>\n/start — Главное меню\n/today — Сегодня\n/tomorrow — Завтра\n/week — Вся неделя\n/current — Какая неделя\n/help — Эта справка",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_schedule))
    app.add_handler(CommandHandler("tomorrow", tomorrow_schedule))
    app.add_handler(CommandHandler("week", week_schedule))
    app.add_handler(CommandHandler("current", current_week_info))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 БОТ ЗАПУЩЕН!")
    app.run_polling()

if __name__ == '__main__':
    main()
