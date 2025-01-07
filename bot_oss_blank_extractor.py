#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os
import requests
from PyPDF2 import PdfReader, PdfWriter
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

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
    os.makedirs("temp", exist_ok=True)
    for name, local_path in LOCAL_FILES.items():
        if not os.path.exists(local_path):
            print(f"Скачивание файла для {name}...")
            response = requests.get(REMOTE_FILES[name])
            with open(local_path, "wb") as f:
                f.write(response.content)


def search_and_extract(file_path, search_term, corpus, match_count):
    reader = PdfReader(file_path)
    for page_number, page in enumerate(reader.pages):
        if search_term in page.extract_text():
            # Нахождение текста, извлечение страниц
            start_page = page_number
            end_page = min(start_page + 4, len(reader.pages))

            writer = PdfWriter()
            for i in range(start_page, end_page):
                writer.add_page(reader.pages[i])

            # Сохранение в новый файл
            sanitized_term = search_term.replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_file = f"temp/extracted_{corpus}_{sanitized_term}_{match_count}.pdf"
            with open(output_file, "wb") as output:
                writer.write(output)
            return output_file
    return None

# Команды Telegram-бота
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Это бот для выгрузки в pdf отдельных именных бланков на ОСС по инициативе собственников ЖК Рихард (25.12.24 - 25.02.25)"
    )
    update.message.reply_text("Введите /начать для работы с ботом.")
    ensure_files_downloaded()

def begin(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Напишите ФИО собственника помещения/наименование юридического лица")

def handle_message(update: Update, context: CallbackContext) -> None:
    search_term = update.message.text.strip()
    if not search_term:
        update.message.reply_text("Введите корректное ФИО или название юридического лица.")
        return

    # Выполняем поиск
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
                update.message.reply_document(f, filename=os.path.basename(result_file))
    else:
        update.message.reply_text(f"Текст '{search_term}' не найден.")

# Настройка и запуск бота
def main():
    TOKEN = "6577404484:AAEjBbfIypMUgoW7nX28ScClQOdk-ebnInU"
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("начать", begin))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

