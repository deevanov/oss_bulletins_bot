#!/usr/bin/env python
# coding: utf-8

import os
import requests
import csv
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

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/17c7PMdqBagYhzKfpN500X2bXMb8DVvcwG2HTLuZfs9M/export?format=csv"
LOCAL_CSV_PATH = "temp/sheet_data.csv"


def ensure_files_downloaded():
    """Проверяет и скачивает отсутствующие файлы."""
    os.makedirs("temp", exist_ok=True)

    # Проверяем наличие локальных PDF-файлов
    for name, local_path in LOCAL_FILES.items():
        if not os.path.exists(local_path):
            print(f"Скачивание файла для {name}...")
            response = requests.get(REMOTE_FILES[name])
            with open(local_path, "wb") as f:
                f.write(response.content)

    # Проверяем наличие таблицы
    if not os.path.exists(LOCAL_CSV_PATH):
        print("Скачивание таблицы с Google Sheets...")
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        with open(LOCAL_CSV_PATH, "wb") as f:
            f.write(response.content)


def search_in_csv(search_term):
    """Ищет введённый текст как часть строки в таблице."""
    if not os.path.exists(LOCAL_CSV_PATH):
        print("Файл таблицы отсутствует.")
        return False

    with open(LOCAL_CSV_PATH, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if len(row) > 0 and search_term.strip() in row[0].strip():
                return True
    return False


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
    ensure_files_downloaded()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения."""
    search_term = update.message.text.strip()

    # Проверка количества слов
    word_count = len(search_term.split())
    if word_count != 3 and word_count <= 5:
        await update.message.reply_text(
            "Поиск не дал результата. Проверьте правильность и полноту написания ФИО собственника помещения/наименование юридического лица."
        )
        return

    # Поиск в таблице
    if not search_in_csv(search_term):
        await update.message.reply_text(
            "Поиск не дал результата. Проверьте правильность и полноту написания ФИО собственника помещения/наименование юридического лица."
        )
        return

    # Если найдено в таблице, ищем в PDF
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
        await update.message.reply_text(f"Текст '{search_term}' найден в таблице, но не найден в PDF-файлах.")


# Настройка и запуск бота
def main():
    """Основная функция запуска бота."""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не найден. Убедитесь, что он указан в .env.")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
