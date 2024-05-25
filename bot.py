#!/usr/bin/env python
# coding: utf-8

# In[2]:


import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import asyncio

nest_asyncio.apply()

# Токен вашего бота
TOKEN = '' #здесь нужен токен

# Состояния для ConversationHandler
INPUT_ALBUMS = range(1)

# Включение логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создание планировщика
scheduler = AsyncIOScheduler()

# Список для хранения альбомов и их дат
albums_data = {}

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Используйте команду /plan_next_week для планирования.')

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        '/plan_next_week - команда, чтобы заполнить альбомы для следующей недели.\n'
        '/albums - узнать, какие альбомы на этой неделе.'
    )

async def plan_next_week(update: Update, context: CallbackContext) -> int:
    context.user_data['albums'] = []
    await update.message.reply_text('Пожалуйста, напишите 5 альбомов следующей недели (каждый с новой строки).')
    return INPUT_ALBUMS

async def input_albums(update: Update, context: CallbackContext) -> int:
    albums = update.message.text.split('\n')
    if len(albums) != 5:
        await update.message.reply_text('Пожалуйста, введите ровно 5 альбомов.')
        return INPUT_ALBUMS
    
    today = datetime.now()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    dates = [(next_monday + timedelta(days=i)).strftime('%d.%m.%Y') for i in range(5)]
    
    context.user_data['albums'] = albums
    albums_data.clear()  # Очистка старых данных
    albums_data.update({dates[i]: albums[i] for i in range(5)})

    response = f"Вот альбомы с {dates[0]} по {dates[4]}:\n"
    days = ['пн', 'вт', 'ср', 'чт', 'пт']
    for i, album in enumerate(albums):
        response += f"{days[i]} — {dates[i]} — {album}\n"
        release_date = next_monday + timedelta(days=i)
        schedule_reminders(update, context, release_date, album)

    await update.message.reply_text(response)
    return ConversationHandler.END

async def albums_command(update: Update, context: CallbackContext) -> None:
    today = datetime.now().strftime('%d.%m.%Y')
    response = "Альбомы на этой неделе:\n"
    for date, album in albums_data.items():
        checkmark = " ✅" if datetime.strptime(date, '%d.%m.%Y') < datetime.now() else ""
        response += f"{date} — {album}{checkmark}\n"
    await update.message.reply_text(response)

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Планирование отменено.')
    return ConversationHandler.END

def schedule_reminders(update: Update, context: CallbackContext, release_date: datetime, album: str) -> None:
    chat_id = update.message.chat_id

    reminder_3_days = release_date - timedelta(days=3)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=reminder_3_days,
        args=[context, chat_id, f"@kal3vala или @ph_morty не забудь сделать монтаж ролика {album}"]
    )

    reminder_2_days = release_date - timedelta(days=2)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=reminder_2_days,
        args=[context, chat_id, f"@kal3vala или @ph_morty не забудь залить ролик {album}\n@pdmska сделай обложку {album}"]
    )

    reminder_1_day = release_date - timedelta(days=1)
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=reminder_1_day,
        args=[context, chat_id, f"@pdmska если не сделал обложку для {album} то пора\n@Nikolay_Morgunov не забудь написать текст для альбома {album} и поставить отложку"]
    )

    # Планирование напоминания на каждую субботу в 15:00 по московскому времени
    scheduler.add_job(
        weekly_reminder,
        'cron',
        day_of_week='sat',
        hour=15,
        minute=0,
        timezone='Europe/Moscow',
        args=[context, chat_id]
    )

async def send_reminder(context: CallbackContext, chat_id: int, message: str) -> None:
    await context.bot.send_message(chat_id=chat_id, text=message)

async def weekly_reminder(context: CallbackContext, chat_id: int) -> None:
    message = "@ph_morty @kal3vala @grypod @pdmska @Nikolay_Morgunov не забудьте заполнить на следующую неделю"
    await context.bot.send_message(chat_id=chat_id, text=message)

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('plan_next_week', plan_next_week)],
        states={
            INPUT_ALBUMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_albums)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("albums", albums_command))

    scheduler.start()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == '__main__':
    asyncio.run(main())


# In[ ]:




