# config.py
# Конфигурация и переменные окружения

import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
GSHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MANAGERS = [123456789]  # Укажи ID админов
