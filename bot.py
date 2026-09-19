import os
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle.tools import Keyboard, Text

import database as db
from current_api import get_current_rate, convert_currency

# Загружаем переменные из .env
load_dotenv()

bot = Bot(token=os.getenv("VK_BOT_TOKEN"))
db.init_db()

# Страна -> код валюты (для автоопределения)
COUNTRY_TO_CURRENCY = {
    "россия": "RUB", "беларусь": "BYN", "казахстан": "KZT", "украина": "UAH",
    "китай": "CNY", "япония": "JPY", "южная корея": "KRW", "таиланд": "THB",
    "вьетнам": "VND", "индия": "INR", "индонезия": "IDR", "турция": "TRY",
    "оаэ": "AED", "египет": "EGP", "израиль": "ILS", "грузия": "GEL",
    "армения": "AMD", "азербайджан": "AZN", "сша": "USD", "канада": "CAD",
    "мексика": "MXN", "бразилия": "BRL", "великобритания": "GBP",
    "швейцария": "CHF", "норвегия": "NOK", "швеция": "SEK", "дания": "DKK",
    "польша": "PLN", "чехия": "CZK", "венгрия": "HUF",
    "италия": "EUR", "германия": "EUR", "франция": "EUR", "испания": "EUR",
    "португалия": "EUR", "греция": "EUR", "нидерланды": "EUR", "бельгия": "EUR",
    "австрия": "EUR", "ирландия": "EUR", "финляндия": "EUR", "эстония": "EUR",
    "латвия": "EUR", "литва": "EUR", "хорватия": "EUR", "словения": "EUR",
    "словакия": "EUR", "кипр": "EUR", "мальта": "EUR",
}

# Состояния диалога для каждого пользователя
user_state = {}

COMMAND_LABELS = (
    "/start", "start", "начать", "help", "/help", "помощь",
    "/newtrip", "🧳 создать новое путешествие",
    "/balance", "💰 баланс",
    "/history", "📜 история расходов",
    "/switch", "📋 мои путешествия",
    "/setrate", "📈 изменить курс",
)

MAIN_KEYBOARD = (
    Keyboard()
    .add(Text("🧳 Создать новое путешествие"))
    .add(Text("📋 Мои путешествия"))
    .row()
    .add(Text("💰 Баланс"))
    .add(Text("📜 История расходов"))
    .row()
    .add(Text("📈 Изменить курс"))
)

CONFIRM_KEYBOARD = (
    Keyboard()
    .add(Text("✅ Да"))
    .add(Text("❌ Нет"))
)


def get_currency(country: str):
    """Код валюты по названию страны или None, если неизвестна"""
    return COUNTRY_TO_CURRENCY.get(country.strip().lower())


def parse_number(text: str):
    """Преобразует строку в число или None, если это не число"""
    try:
        return float(text.replace(",", ".").strip())
    except ValueError:
        return None


def get_rate(from_cur: str, to_cur: str):
    """Курс from_cur -> to_cur через API"""
    data = get_current_rate(default=from_cur, currencies=[to_cur])
    return data.get("quotes", {}).get(f"{from_cur}{to_cur}")


def balance_text(trip: dict) -> str:
    return (f"💰 Остаток: {trip['balance_to']:.2f} {trip['to_currency']} "
            f"= {trip['balance_from']:.2f} {trip['from_currency']}")


def finish_state(user_id: int):
    user_state.pop(user_id, None)


async def ask_rate(message: Message, state: dict):
    """Получить курс через API и спросить подтверждение"""
    try:
        rate = get_rate(state["from_cur"], state["to_cur"])
    except Exception:
        rate = None
    if rate:
        state["rate"] = rate
        state["step"] = "rate_confirm"
        await message.answer(
            f"📈 Текущий курс: 1 {state['from_cur']} = {rate:.6f} {state['to_cur']}.\n"
            f"Подходит такой курс?",
            keyboard=CONFIRM_KEYBOARD)
    else:
        state["step"] = "custom_rate"
        await message.answer(
            f"Не удалось получить курс из API. 😅\n"
            f"Введите курс вручную: сколько {state['to_cur']} за 1 {state['from_cur']}:")


async def show_balance(message: Message, user_id: int):
    trip = db.get_active_trip(user_id)
    if not trip:
        await message.answer("У вас пока нет путешествий. Создайте первое кнопкой «🧳 Создать новое путешествие»!",
                             keyboard=MAIN_KEYBOARD)
    else:
        await message.answer(f"📍 {trip['from_country']} → {trip['to_country']}\n{balance_text(trip)}",
                             keyboard=MAIN_KEYBOARD)


async def show_history(message: Message, user_id: int):
    trip = db.get_active_trip(user_id)
    if not trip:
        await message.answer("У вас пока нет путешествий — и истории тоже. 😊", keyboard=MAIN_KEYBOARD)
        return
    expenses = db.get_expenses(trip["id"])
    if not expenses:
        await message.answer("Расходов пока не записано.", keyboard=MAIN_KEYBOARD)
        return
    lines = [f"📜 Расходы в путешествии {trip['from_country']} → {trip['to_country']}:"]
    for e in expenses:
        lines.append(f"• {e['amount']:.2f} {trip['to_currency']} = "
                     f"{e['amount_converted']:.2f} {trip['from_currency']} — "
                     f"{e['description'] or 'без описания'} ({e['created_at'][:16]})")
    await message.answer("\n".join(lines), keyboard=MAIN_KEYBOARD)


async def show_trips(message: Message, user_id: int):
    trips = db.get_all_trips(user_id)
    if not trips:
        await message.answer("У вас пока нет путешествий. Создайте первое!", keyboard=MAIN_KEYBOARD)
        return
    lines = ["📋 Ваши путешествия (отправьте номер, чтобы переключиться):"]
    for i, t in enumerate(trips, 1):
        mark = "✅" if t["is_active"] else "   "
        lines.append(f"{mark} {i}. {t['from_country']} → {t['to_country']} "
                     f"({t['balance_to']:.2f} {t['to_currency']})")
    user_state[user_id] = {"step": "switch_choice", "trips": [t["id"] for t in trips]}
    await message.answer("\n".join(lines), keyboard=MAIN_KEYBOARD)


@bot.on.message()
async def default_handler(message: Message):
    user_id = message.from_id
    text = (message.text or "").strip()
    low = text.lower()
    state = user_state.get(user_id)

    # Если нажата кнопка меню или команда — сбрасываем диалог и идём в команды
    if state and low in COMMAND_LABELS:
        finish_state(user_id)
        state = None

    # ---------- Шаги диалогов ----------
    if state:
        step = state["step"]

        if step == "from_country":
            cur = get_currency(text)
            if cur:
                state.update(step="to_country", from_country=text, from_cur=cur)
                await message.answer(f"✅ {text} — валюта {cur}.\n\nТеперь введите страну назначения:")
            else:
                state["step"] = "from_cur_code"
                state["from_country"] = text
                await message.answer(f"Не знаю валюту страны «{text}». 😅\nВведите код валюты из 3 букв (например, RUB):")
            return

        if step == "from_cur_code":
            code = text.upper()
            if len(code) == 3 and code.isalpha():
                state.update(step="to_country", from_cur=code)
                await message.answer(f"✅ Валюта принята: {code}.\n\nТеперь введите страну назначения:")
            else:
                await message.answer("Введите ровно 3 буквы, например RUB или USD:")
            return

        if step == "to_country":
            cur = get_currency(text)
            if cur:
                state.update(to_country=text, to_cur=cur)
                await ask_rate(message, state)
            else:
                state["step"] = "to_cur_code"
                state["to_country"] = text
                await message.answer(f"Не знаю валюту страны «{text}». 😅\nВведите код валюты из 3 букв (например, CNY):")
            return

        if step == "to_cur_code":
            code = text.upper()
            if len(code) == 3 and code.isalpha():
                state["to_cur"] = code
                await ask_rate(message, state)
            else:
                await message.answer("Введите ровно 3 буквы, например CNY или EUR:")
            return

        if step == "rate_confirm":
            if low in ("✅ да", "да", "yes"):
                state["step"] = "initial_amount"
                await message.answer(f"Отлично! Введите начальную сумму в домашней валюте ({state['from_cur']}):")
            elif low in ("❌ нет", "no", "нет"):
                state["step"] = "custom_rate"
                await message.answer(f"Введите свой курс: сколько {state['to_cur']} за 1 {state['from_cur']} (например, по местному обменнику):")
            else:
                await message.answer("Нажмите «✅ Да» или «❌ Нет».", keyboard=CONFIRM_KEYBOARD)
            return

        if step == "custom_rate":
            rate = parse_number(text)
            if rate and rate > 0:
                state["rate"] = rate
                state["step"] = "initial_amount"
                await message.answer(f"✅ Курс сохранён: 1 {state['from_cur']} = {rate} {state['to_cur']}.\n\n"
                                     f"Введите начальную сумму в домашней валюте ({state['from_cur']}):")
            else:
                await message.answer("Введите курс числом, например 0.079:")
            return

        if step == "initial_amount":
            amount = parse_number(text)
            if not amount or amount <= 0:
                await message.answer("Введите сумму числом, например 40000:")
                return
            try:
                data = convert_currency(amount, state["from_cur"], state["to_cur"])
                converted = data.get("result")
                if converted is None:
                    converted = amount * state["rate"]
            except Exception:
                converted = amount * state["rate"]
            db.create_trip(
                user_id=user_id,
                from_country=state["from_country"],
                from_currency=state["from_cur"],
                to_country=state["to_country"],
                to_currency=state["to_cur"],
                rate=state["rate"],
                balance_from=amount,
                balance_to=converted,
            )
            finish_state(user_id)
            await message.answer(
                f"🎉 Путешествие создано: {state['from_country']} → {state['to_country']}!\n"
                f"💰 Стартовый баланс: {amount:.2f} {state['from_cur']} = {converted:.2f} {state['to_cur']}\n\n"
                f"Теперь присылайте траты числами в {state['to_cur']} — я буду их учитывать!",
                keyboard=MAIN_KEYBOARD)
            return

        if step == "confirm_expense":
            if low in ("✅ да", "да", "yes"):
                trip = db.get_active_trip(user_id)
                if trip:
                    db.add_expense(trip["id"], state["amount"], state["converted"])
                    db.update_balance(trip["id"],
                                      trip["balance_from"] - state["converted"],
                                      trip["balance_to"] - state["amount"])
                    trip = db.get_active_trip(user_id)
                    finish_state(user_id)
                    await message.answer(f"✅ Расход записан!\n{balance_text(trip)}", keyboard=MAIN_KEYBOARD)
                else:
                    finish_state(user_id)
                    await message.answer("Путешествие не найдено... Создайте новое.", keyboard=MAIN_KEYBOARD)
            elif low in ("❌ нет", "no", "нет"):
                finish_state(user_id)
                await message.answer("Хорошо, не записываю. 🙂", keyboard=MAIN_KEYBOARD)
            else:
                await message.answer("Нажмите «✅ Да» или «❌ Нет».", keyboard=CONFIRM_KEYBOARD)
            return

        if step == "switch_choice":
            num = parse_number(text)
            trips = state.get("trips", [])
            if num and 1 <= int(num) <= len(trips):
                db.switch_trip(user_id, trips[int(num) - 1])
                finish_state(user_id)
                trip = db.get_active_trip(user_id)
                await message.answer(f"✅ Переключились на {trip['from_country']} → {trip['to_country']}.\n"
                                     f"{balance_text(trip)}", keyboard=MAIN_KEYBOARD)
                return
            finish_state(user_id)
            # если ввели не номер — падаем вниз в команды

        if step == "setrate_value":
            rate = parse_number(text)
            trip = db.get_active_trip(user_id)
            if rate and rate > 0 and trip:
                db.set_rate(trip["id"], rate)
                finish_state(user_id)
                await message.answer(f"✅ Новый курс сохранён: 1 {trip['from_currency']} = {rate} {trip['to_currency']}.",
                                     keyboard=MAIN_KEYBOARD)
            else:
                await message.answer("Введите курс числом, например 0.082:")
            return

    # ---------- Команды и кнопки меню ----------
    if low in ("/start", "start", "начать", "help", "/help", "помощь"):
        await message.answer(
            "👋 Привет! Я — финансовый помощник для путешествий.\n\n"
            "Я умею:\n"
            "🧳 создавать кошельки для разных стран\n"
            "💱 конвертировать валюты по актуальному курсу\n"
            "📊 отслеживать расходы и показывать остаток в двух валютах\n\n"
            "Команды: /newtrip /switch /balance /history /setrate\n"
            "Или просто нажимайте кнопки меню!",
            keyboard=MAIN_KEYBOARD)
        return

    if low in ("/newtrip", "🧳 создать новое путешествие"):
        user_state[user_id] = {"step": "from_country"}
        await message.answer("🧳 Создаём новое путешествие!\n\nВведите страну отправления (например, Россия):")
        return

    if low in ("/balance", "💰 баланс"):
        await show_balance(message, user_id)
        return

    if low in ("/history", "📜 история расходов"):
        await show_history(message, user_id)
        return

    if low in ("/switch", "📋 мои путешествия"):
        await show_trips(message, user_id)
        return

    if low in ("/setrate", "📈 изменить курс"):
        trip = db.get_active_trip(user_id)
        if not trip:
            await message.answer("Сначала создайте путешествие — потом будем менять курс. 🙂", keyboard=MAIN_KEYBOARD)
        else:
            user_state[user_id] = {"step": "setrate_value"}
            await message.answer(f"Текущий курс: 1 {trip['from_currency']} = {trip['rate']} {trip['to_currency']}.\n"
                                 f"Введите новый курс:")
        return

    # ---------- Расход: просто число ----------
    amount = parse_number(text)
    if amount is not None and amount > 0:
        trip = db.get_active_trip(user_id)
        if trip and trip["rate"]:
            converted = amount / trip["rate"]
            user_state[user_id] = {"step": "confirm_expense", "amount": amount, "converted": converted}
            await message.answer(
                f"💱 {amount:.2f} {trip['to_currency']} = {converted:.2f} {trip['from_currency']}\n"
                f"Учесть как расход?",
                keyboard=CONFIRM_KEYBOARD)
        else:
            await message.answer("Похоже на число, но у вас нет активного путешествия. "
                                 "Создайте его кнопкой «🧳 Создать новое путешествие».", keyboard=MAIN_KEYBOARD)
        return

    await message.answer(
        "🤔 Не понял. Нажмите кнопку меню или отправьте команду:\n"
        "/newtrip — новое путешествие\n/balance — баланс\n/history — история\n"
        "/switch — мои путешествия\n/setrate — изменить курс",
        keyboard=MAIN_KEYBOARD)


if __name__ == "__main__":
    print("🤖 Финансовый бот для путешествий запущен...")
    bot.run_forever()