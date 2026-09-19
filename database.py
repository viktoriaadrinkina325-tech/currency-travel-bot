import sqlite3

DB_NAME = "travel_bot.db"


def get_connection():
    """Получить соединение с базой данных"""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Инициализация базы данных — создание таблиц"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица путешествий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_country TEXT NOT NULL,
            from_currency TEXT NOT NULL,
            to_country TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate REAL NOT NULL,
            balance_from REAL NOT NULL,
            balance_to REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица расходов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            amount_converted REAL NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trip_id) REFERENCES trips(id)
        )
    """)

    conn.commit()
    conn.close()


def create_trip(user_id, from_country, from_currency, to_country, to_currency,
                rate, balance_from, balance_to):
    """Создать новое путешествие и сделать его активным"""
    conn = get_connection()
    cursor = conn.cursor()

    # Деактивируем старые путешествия пользователя
    cursor.execute("UPDATE trips SET is_active = 0 WHERE user_id = ?", (user_id,))

    # Создаём новое
    cursor.execute("""
        INSERT INTO trips (user_id, from_country, from_currency, to_country,
                          to_currency, rate, balance_from, balance_to, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (user_id, from_country, from_currency, to_country, to_currency,
          rate, balance_from, balance_to))

    trip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trip_id


def get_active_trip(user_id):
    """Получить активное путешествие пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, from_country, from_currency, to_country, to_currency,
               rate, balance_from, balance_to, is_active, created_at
        FROM trips
        WHERE user_id = ? AND is_active = 1
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "from_country": row[1],
            "from_currency": row[2],
            "to_country": row[3],
            "to_currency": row[4],
            "rate": row[5],
            "balance_from": row[6],
            "balance_to": row[7],
            "is_active": row[8],
            "created_at": row[9]
        }
    return None


def get_all_trips(user_id):
    """Получить все путешествия пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, from_country, to_country, to_currency, balance_from,
               balance_to, is_active, created_at
        FROM trips WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    trips = []
    for row in rows:
        trips.append({
            "id": row[0],
            "from_country": row[1],
            "to_country": row[2],
            "to_currency": row[3],
            "balance_from": row[4],
            "balance_to": row[5],
            "is_active": row[6],
            "created_at": row[7]
        })
    return trips


def switch_trip(user_id, trip_id):
    """Переключиться на другое путешествие"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trips SET is_active = 0 WHERE user_id = ?", (user_id,))
    cursor.execute("""
        UPDATE trips SET is_active = 1
        WHERE id = ? AND user_id = ?
    """, (trip_id, user_id))
    conn.commit()
    conn.close()


def update_balance(trip_id, new_balance_from, new_balance_to):
    """Обновить баланс путешествия"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE trips
        SET balance_from = ?, balance_to = ?
        WHERE id = ?
    """, (new_balance_from, new_balance_to, trip_id))
    conn.commit()
    conn.close()


def set_rate(trip_id, new_rate):
    """Изменить курс обмена"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trips SET rate = ? WHERE id = ?", (new_rate, trip_id))
    conn.commit()
    conn.close()


def add_expense(trip_id, amount, amount_converted, description=""):
    """Добавить расход"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (trip_id, amount, amount_converted, description)
        VALUES (?, ?, ?, ?)
    """, (trip_id, amount, amount_converted, description))
    conn.commit()
    conn.close()


def get_expenses(trip_id):
    """Получить историю расходов"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, amount_converted, description, created_at
        FROM expenses WHERE trip_id = ?
        ORDER BY created_at DESC
    """, (trip_id,))
    rows = cursor.fetchall()
    conn.close()

    expenses = []
    for row in rows:
        expenses.append({
            "amount": row[0],
            "amount_converted": row[1],
            "description": row[2],
            "created_at": row[3]
        })
    return expenses


if __name__ == "__main__":
    print("🗄 Тест базы данных")

    # 1. Инициализируем БД
    init_db()
    print("✅ Таблицы созданы")

    # 2. Создаём путешествие Россия → Китай
    user_id = 12345
    trip_id = create_trip(
        user_id=user_id,
        from_country="Россия",
        from_currency="RUB",
        to_country="Китай",
        to_currency="CNY",
        rate=0.079,
        balance_from=4000,
        balance_to=316
    )
    print(f"✅ Создано путешествие #{trip_id}")

    # 3. Получаем активное путешествие
    active = get_active_trip(user_id)
    print(f"📍 Активное: {active['from_country']} → {active['to_country']}")
    print(f"💰 Баланс: {active['balance_from']} {active['from_currency']} = "
          f"{active['balance_to']} {active['to_currency']}")

    # 4. Добавляем расход: обед 50 юаней
    add_expense(trip_id, amount=50, amount_converted=632.9, description="Обед")
    update_balance(trip_id, 4000 - 632.9, 316 - 50)
    print("✅ Добавлен расход: 50 CNY = 632.9 RUB")

    # 5. Проверяем новый баланс
    active = get_active_trip(user_id)
    print(f"💰 Новый баланс: {active['balance_from']:.2f} RUB = "
          f"{active['balance_to']:.2f} CNY")

    # 6. История расходов
    expenses = get_expenses(trip_id)
    print(f"📜 История ({len(expenses)} записей):")
    for e in expenses:
        print(f"   {e['description']}: {e['amount']} CNY = {e['amount_converted']} RUB")