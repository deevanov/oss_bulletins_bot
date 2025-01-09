#!/usr/bin/env python
# coding: utf-8

import os
import requests
from PyPDF2 import PdfReader, PdfWriter
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Загрузка токена из файла .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Пути для локального хранения файлов
LOCAL_FILES = {
    "Корпус 1": "temp/Решения_ОС_корпус1.pdf",
    "Корпус 2": "temp/Решения_ОС_корпус2.pdf"
}

REMOTE_FILES = {
    "Корпус 1": "https://drive.google.com/uc?id=1iscPvNlOdSLQH2kFH2mum2x62Vd6uINH",
    "Корпус 2": "https://drive.google.com/uc?id=1gX6U0lljhehiTbfjlGC5ZS-sUphJkGBm"
}

def ensure_files_downloaded():
    """Проверяет и скачивает отсутствующие файлы."""
    os.makedirs("temp", exist_ok=True)
    for name, local_path in LOCAL_FILES.items():
        if not os.path.exists(local_path):
            print(f"Скачивание файла для {name}...")
            response = requests.get(REMOTE_FILES[name])
            with open(local_path, "wb") as f:
                f.write(response.content)

def search_and_extract(file_path, search_term, corpus, match_count):
    """Ищет текст и извлекает страницы из PDF."""
    reader = PdfReader(file_path)
    for page_number, page in enumerate(reader.pages):
        text = page.extract_text()
        if search_term in text:
            start_page = page_number
            end_page = min(start_page + 4, len(reader.pages))

            writer = PdfWriter()
            for i in range(start_page, end_page):
                writer.add_page(reader.pages[i])

            sanitized_term = search_term.replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_file = f"temp/extracted_{corpus}_{sanitized_term}_{match_count}.pdf"
            with open(output_file, "wb") as output:
                writer.write(output)
            return output_file
    return None

# Команды Telegram-бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Это бот для выгрузки в PDF отдельных именных бланков на ОСС по инициативе собственников ЖК Рихард (25.12.24 - 25.02.25)"
    )
    await update.message.reply_text("Введите /начать для работы с ботом.")
    ensure_files_downloaded()

async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /начать."""
    await update.message.reply_text("Напишите ФИО собственника помещения/наименование юридического лица")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения."""
    search_term = update.message.text.strip()
    if not search_term:
        await update.message.reply_text("Введите корректное ФИО или название юридического лица.")
        return

    match_count = 0
    results = []
    for name, local_path in LOCAL_FILES.items():
        match_count += 1
        result = search_and_extract(local_path, search_term, name.replace("Корпус ", "К"), match_count)
        if result:
            results.append(result)

    if results:
        for result_file in results:
            with open(result_file, "rb") as f:
                await update.message.reply_document(f, filename=os.path.basename(result_file))
    else:
        await update.message.reply_text(f"Текст '{search_term}' не найден.")

# Настройка и запуск бота
def main():
    """Основная функция запуска бота."""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не найден. Убедитесь, что он указан в .env.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("начать", begin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
