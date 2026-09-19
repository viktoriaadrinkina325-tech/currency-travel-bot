import os
import requests
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

API_KEY = os.getenv("CURRENCY_API_KEY")
if not API_KEY:
    raise ValueError("Не найден CURRENCY_API_KEY в файле .env")

BASE_URL = "https://api.exchangerate.host"


def get_current_rate(default: str = "USD", currencies: list = ["EUR", "GBP", "JPY"]):
    """Текущие курсы валют относительно базовой валюты"""
    params = {
        "access_key": API_KEY,
        "source": default,
        "currencies": ",".join(currencies),
    }
    response = requests.get(f"{BASE_URL}/live", params=params)
    response.raise_for_status()
    return response.json()


def convert_currency(amount, from_currency, to_currency):
    """Конвертация суммы из одной валюты в другую"""
    params = {
        "access_key": API_KEY,
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
    }
    response = requests.get(f"{BASE_URL}/convert", params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Тест 1: курсы рубля к основным валютам
    data = get_current_rate(default="RUB", currencies=["USD", "EUR", "GBP", "JPY", "CNY"])
    print("📈 Курсы рубля:", data.get("quotes", data))

    # Тест 2: конвертация 100 долларов в евро
    result = convert_currency(100, "USD", "EUR")
    print("💱 100 USD в EUR:", result.get("result", result))