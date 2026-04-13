"""Database module — async SQLite via aiosqlite.

Single-user personal database: finance (settings, categories, transactions,
savings goals) + fitness (weight, workout, meal, water logs).
"""
import json
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date, datetime, timedelta

from src.config import DB_PATH
from src.utils.constants import DEFAULT_CATEGORIES

_db_path = DB_PATH


@asynccontextmanager
async def get_db():
    """Async context manager for database connections."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


# ═══════════════════════════════════════════════════════════════════════
# Initialization
# ═══════════════════════════════════════════════════════════════════════

async def init_db():
    """Create tables and seed default categories."""
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                telegram_id INTEGER,
                username TEXT,
                full_name TEXT,
                monthly_income REAL DEFAULT 0,
                currency TEXT DEFAULT 'VND',
                timezone TEXT DEFAULT 'Asia/Ho_Chi_Minh',
                budget_needs_pct REAL DEFAULT 50,
                budget_wants_pct REAL DEFAULT 30,
                budget_savings_pct REAL DEFAULT 20,
                payday INTEGER DEFAULT 1,
                reminder_time TEXT DEFAULT '21:00',
                reminder_enabled INTEGER DEFAULT 1,
                onboarding_complete INTEGER DEFAULT 0,

                -- Fitness fields
                age INTEGER,
                weight REAL,
                height REAL,
                goal TEXT DEFAULT 'bulk',
                activity_level TEXT DEFAULT 'moderate',
                target_weight REAL,
                monthly_food_budget REAL DEFAULT 0,
                food_budget_tier TEXT DEFAULT 'standard',
                tdee REAL,
                daily_calories REAL,
                daily_protein REAL,
                daily_carbs REAL,
                daily_fat REAL,
                current_program TEXT DEFAULT 'ppl',
                workout_day_index INTEGER DEFAULT 0,
                fitness_reminders_enabled INTEGER DEFAULT 1,
                fitness_onboarding_complete INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL DEFAULT '📦',
                type TEXT NOT NULL CHECK(type IN ('need', 'want', 'saving', 'income')),
                keywords TEXT DEFAULT '[]',
                budget_limit REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER REFERENCES categories(id),
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL,
                description TEXT,
                payment_method TEXT DEFAULT 'cash',
                transaction_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '🎯',
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline DATE,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Fitness tables
            CREATE TABLE IF NOT EXISTS weight_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weight REAL NOT NULL,
                note TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workout_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_type TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                sets INTEGER,
                reps TEXT,
                weight_kg REAL,
                note TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS meal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_type TEXT NOT NULL,
                description TEXT,
                calories REAL,
                protein REAL,
                carbs REAL,
                fat REAL,
                cost_vnd REAL DEFAULT 0,
                completed INTEGER DEFAULT 0,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS water_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_ml INTEGER NOT NULL,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);
            CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type);
            CREATE INDEX IF NOT EXISTS idx_weight_date ON weight_logs(logged_at);
            CREATE INDEX IF NOT EXISTS idx_workout_date ON workout_logs(logged_at);
            CREATE INDEX IF NOT EXISTS idx_meal_date ON meal_logs(logged_at);
        """)

        cursor = await db.execute("SELECT COUNT(*) FROM settings")
        count = (await cursor.fetchone())[0]
        if count == 0:
            await db.execute("INSERT INTO settings (id) VALUES (1)")

        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for i, cat in enumerate(DEFAULT_CATEGORIES):
                await db.execute(
                    "INSERT INTO categories (name, emoji, type, keywords, sort_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (cat["name"], cat["emoji"], cat["type"],
                     json.dumps(cat["keywords"], ensure_ascii=False), i)
                )

        await db.commit()

    await _migrate_settings_columns()


async def _migrate_settings_columns():
    """Add fitness columns to existing settings table if missing."""
    new_cols = {
        "age": "INTEGER",
        "weight": "REAL",
        "height": "REAL",
        "goal": "TEXT DEFAULT 'bulk'",
        "activity_level": "TEXT DEFAULT 'moderate'",
        "target_weight": "REAL",
        "monthly_food_budget": "REAL DEFAULT 0",
        "food_budget_tier": "TEXT DEFAULT 'standard'",
        "tdee": "REAL",
        "daily_calories": "REAL",
        "daily_protein": "REAL",
        "daily_carbs": "REAL",
        "daily_fat": "REAL",
        "current_program": "TEXT DEFAULT 'ppl'",
        "workout_day_index": "INTEGER DEFAULT 0",
        "fitness_reminders_enabled": "INTEGER DEFAULT 1",
        "fitness_onboarding_complete": "INTEGER DEFAULT 0",
    }
    async with get_db() as db:
        cursor = await db.execute("PRAGMA table_info(settings)")
        existing = {row[1] for row in await cursor.fetchall()}
        for col, col_type in new_cols.items():
            if col not in existing:
                await db.execute(f"ALTER TABLE settings ADD COLUMN {col} {col_type}")
        await db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════════

async def get_settings() -> dict:
    """Get user settings (single row)."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def update_settings(**kwargs) -> None:
    """Update settings fields."""
    async with get_db() as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values())
        vals.append(datetime.now().isoformat())
        await db.execute(
            f"UPDATE settings SET {sets}, updated_at = ? WHERE id = 1", vals
        )
        await db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════════════════════════════

async def get_categories(cat_type: str | None = None,
                         active_only: bool = True) -> list[dict]:
    """Get categories, optionally filtered by type."""
    async with get_db() as db:
        query = "SELECT * FROM categories WHERE 1=1"
        params = []
        if cat_type:
            query += " AND type = ?"
            params.append(cat_type)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY sort_order"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["keywords"] = json.loads(d.get("keywords", "[]"))
            result.append(d)
        return result


async def get_category(cat_id: int) -> dict | None:
    """Get a single category by ID."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (cat_id,))
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            d["keywords"] = json.loads(d.get("keywords", "[]"))
            return d
        return None


async def find_category_by_keywords(text: str) -> tuple[dict | None, float]:
    """Find best matching category by keyword matching."""
    text_lower = text.lower()
    categories = await get_categories()
    best_match = None
    best_score = 0.0

    for cat in categories:
        for keyword in cat["keywords"]:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                score = len(keyword_lower) / max(len(text_lower), 1)
                if f" {keyword_lower} " in f" {text_lower} ":
                    score += 0.3
                score = min(score + 0.4, 1.0)

                if score > best_score:
                    best_score = score
                    best_match = cat

    return best_match, best_score


async def find_category_by_name(name: str) -> dict | None:
    """Find category by exact name match."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM categories WHERE name = ? AND is_active = 1", (name,)
        )
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            d["keywords"] = json.loads(d.get("keywords", "[]"))
            return d
        return None


# ═══════════════════════════════════════════════════════════════════════
# Transactions
# ═══════════════════════════════════════════════════════════════════════

async def add_transaction(category_id: int, tx_type: str, amount: float,
                          description: str, payment_method: str = "cash",
                          transaction_date: date | None = None) -> int:
    """Add a new transaction. Returns the new transaction ID."""
    async with get_db() as db:
        tx_date = transaction_date or date.today()
        cursor = await db.execute(
            "INSERT INTO transactions "
            "(category_id, type, amount, description, payment_method, transaction_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (category_id, tx_type, amount, description, payment_method,
             tx_date.isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_transactions(start_date: date | None = None,
                           end_date: date | None = None,
                           category_id: int | None = None,
                           tx_type: str | None = None,
                           search: str | None = None,
                           limit: int = 50, offset: int = 0) -> list[dict]:
    """Get transactions with optional filters."""
    async with get_db() as db:
        query = """
            SELECT t.*, c.name as category_name, c.emoji as category_emoji,
                   c.type as category_type
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date.isoformat())
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)
        if tx_type:
            query += " AND t.type = ?"
            params.append(tx_type)
        if search:
            query += " AND (t.description LIKE ? OR c.name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY t.transaction_date DESC, t.created_at DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_transactions_for_export(start_date: date | None = None,
                                           end_date: date | None = None) -> list[dict]:
    """Get all transactions for CSV export (no limit)."""
    async with get_db() as db:
        query = """
            SELECT t.transaction_date, t.type, t.amount, t.description,
                   t.payment_method, c.name as category_name,
                   c.type as category_type, c.emoji as category_emoji
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(end_date.isoformat())
        query += " ORDER BY t.transaction_date ASC, t.created_at ASC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_last_transaction() -> dict | None:
    """Get the most recently created transaction."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT t.*, c.name as category_name, c.emoji as category_emoji "
            "FROM transactions t "
            "LEFT JOIN categories c ON t.category_id = c.id "
            "ORDER BY t.created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_transaction(tx_id: int) -> bool:
    """Delete a transaction by ID. Returns True if deleted."""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM transactions WHERE id = ?", (tx_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_transaction(tx_id: int, **kwargs) -> bool:
    """Update transaction fields. Returns True if updated."""
    async with get_db() as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [tx_id]
        cursor = await db.execute(
            f"UPDATE transactions SET {sets} WHERE id = ?", vals
        )
        await db.commit()
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════
# Summaries & Analytics
# ═══════════════════════════════════════════════════════════════════════

async def get_spending_summary(start_date: date, end_date: date) -> dict:
    """Get total income/expense/net for a date range."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions "
            "WHERE type = 'income' AND transaction_date BETWEEN ? AND ?",
            (start_date.isoformat(), end_date.isoformat())
        )
        total_income = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions "
            "WHERE type = 'expense' AND transaction_date BETWEEN ? AND ?",
            (start_date.isoformat(), end_date.isoformat())
        )
        total_expense = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM transactions "
            "WHERE transaction_date BETWEEN ? AND ?",
            (start_date.isoformat(), end_date.isoformat())
        )
        tx_count = (await cursor.fetchone())[0]

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net": total_income - total_expense,
            "tx_count": tx_count,
            "start_date": start_date,
            "end_date": end_date,
        }


async def get_category_spending(start_date: date, end_date: date) -> list[dict]:
    """Get expense breakdown by category for a date range."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.id, c.name, c.emoji, c.type, c.budget_limit,
                   COALESCE(SUM(t.amount), 0) as total_spent,
                   COUNT(t.id) as tx_count
            FROM categories c
            LEFT JOIN transactions t ON c.id = t.category_id
                AND t.type = 'expense'
                AND t.transaction_date BETWEEN ? AND ?
            WHERE c.is_active = 1 AND c.type != 'income'
            GROUP BY c.id
            HAVING total_spent > 0
            ORDER BY total_spent DESC
            """,
            (start_date.isoformat(), end_date.isoformat())
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_type_spending(start_date: date, end_date: date) -> dict:
    """Get expense totals by type (need/want/saving)."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT c.type, COALESCE(SUM(t.amount), 0) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'expense'
              AND t.transaction_date BETWEEN ? AND ?
            GROUP BY c.type
            """,
            (start_date.isoformat(), end_date.isoformat())
        )
        rows = await cursor.fetchall()
        result = {"need": 0, "want": 0, "saving": 0}
        for row in rows:
            if row["type"] in result:
                result[row["type"]] = row["total"]
        return result


async def get_daily_spending(start_date: date, end_date: date) -> list[dict]:
    """Get daily expense totals for a date range."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT transaction_date, COALESCE(SUM(amount), 0) as total,
                   COUNT(*) as tx_count
            FROM transactions
            WHERE type = 'expense'
              AND transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date
            """,
            (start_date.isoformat(), end_date.isoformat())
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════════════
# Savings Goals
# ═══════════════════════════════════════════════════════════════════════

async def add_goal(name: str, target_amount: float,
                   deadline: date | None = None, emoji: str = "🎯") -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO savings_goals (name, target_amount, deadline, emoji) "
            "VALUES (?, ?, ?, ?)",
            (name, target_amount,
             deadline.isoformat() if deadline else None, emoji)
        )
        await db.commit()
        return cursor.lastrowid


async def get_goals(active_only: bool = True) -> list[dict]:
    async with get_db() as db:
        query = "SELECT * FROM savings_goals"
        if active_only:
            query += " WHERE is_completed = 0"
        query += " ORDER BY created_at DESC"
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_goal(goal_id: int, **kwargs) -> bool:
    async with get_db() as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [goal_id]
        cursor = await db.execute(
            f"UPDATE savings_goals SET {sets} WHERE id = ?", vals
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_goal(goal_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM savings_goals WHERE id = ?", (goal_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════
# Fitness — Weight Logs
# ═══════════════════════════════════════════════════════════════════════

async def log_weight(weight: float, note: str = "") -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO weight_logs (weight, note) VALUES (?, ?)",
            (weight, note)
        )
        await db.commit()
        return cursor.lastrowid


async def get_weight_history(days: int = 30) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM weight_logs WHERE logged_at >= ? ORDER BY logged_at",
            (since,)
        )
        return [dict(r) for r in await cursor.fetchall()]


# ═══════════════════════════════════════════════════════════════════════
# Fitness — Workout Logs
# ═══════════════════════════════════════════════════════════════════════

async def log_workout(day_type: str, exercise_name: str,
                      sets: int, reps: str, weight_kg: float,
                      note: str = "") -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO workout_logs "
            "(day_type, exercise_name, sets, reps, weight_kg, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (day_type, exercise_name, sets, reps, weight_kg, note)
        )
        await db.commit()
        return cursor.lastrowid


async def get_exercise_pr(exercise_name: str) -> float | None:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT MAX(weight_kg) FROM workout_logs WHERE exercise_name = ?",
            (exercise_name,)
        )
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None


async def did_workout_today() -> bool:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM workout_logs WHERE logged_at >= ?",
            (today_start.isoformat(),)
        )
        return ((await cursor.fetchone())[0] or 0) > 0


async def get_workout_history(days: int = 7) -> list[dict]:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM workout_logs WHERE logged_at >= ? ORDER BY logged_at DESC",
            (since,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def advance_workout_day() -> int:
    """Advance workout day index and return new index."""
    settings = await get_settings()
    idx = (settings.get("workout_day_index", 0) or 0) + 1
    schedule_len = 7
    new_idx = idx % schedule_len
    await update_settings(workout_day_index=new_idx)
    return new_idx


# ═══════════════════════════════════════════════════════════════════════
# Fitness — Meal Logs
# ═══════════════════════════════════════════════════════════════════════

async def log_meal_entry(meal_type: str, description: str = "",
                         calories: float = 0, protein: float = 0,
                         carbs: float = 0, fat: float = 0,
                         cost_vnd: float = 0, completed: bool = True) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO meal_logs "
            "(meal_type, description, calories, protein, carbs, fat, cost_vnd, completed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (meal_type, description, calories, protein, carbs, fat,
             cost_vnd, 1 if completed else 0)
        )
        await db.commit()
        return cursor.lastrowid


async def get_today_meals() -> list[dict]:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM meal_logs WHERE logged_at >= ? ORDER BY logged_at",
            (today_start.isoformat(),)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_today_nutrition() -> dict:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0), "
            "COALESCE(SUM(carbs),0), COALESCE(SUM(fat),0), COUNT(*) "
            "FROM meal_logs WHERE logged_at >= ? AND completed = 1",
            (today_start.isoformat(),)
        )
        row = await cursor.fetchone()
        return {
            "calories": row[0], "protein": row[1],
            "carbs": row[2], "fat": row[3], "meals_done": row[4],
        }


# ═══════════════════════════════════════════════════════════════════════
# Fitness — Water Logs
# ═══════════════════════════════════════════════════════════════════════

async def log_water(amount_ml: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO water_logs (amount_ml) VALUES (?)", (amount_ml,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_today_water() -> int:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_ml), 0) FROM water_logs WHERE logged_at >= ?",
            (today_start.isoformat(),)
        )
        return (await cursor.fetchone())[0] or 0


# ═══════════════════════════════════════════════════════════════════════
# Fitness — Weekly Report
# ═══════════════════════════════════════════════════════════════════════

async def get_fitness_weekly_report() -> dict:
    week_start = (datetime.utcnow() - timedelta(days=7)).isoformat()
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT DATE(logged_at)) FROM workout_logs WHERE logged_at >= ?",
            (week_start,)
        )
        workout_days = (await cursor.fetchone())[0] or 0

        cursor = await db.execute(
            "SELECT COUNT(*) FROM meal_logs WHERE logged_at >= ? AND completed = 1",
            (week_start,)
        )
        meals_logged = (await cursor.fetchone())[0] or 0

        weights = await get_weight_history(days=7)
        weight_change = 0.0
        latest_weight = None
        if len(weights) >= 2:
            weight_change = round(weights[-1]["weight"] - weights[0]["weight"], 1)
        if weights:
            latest_weight = weights[-1]["weight"]

        return {
            "workout_days": workout_days,
            "meals_logged": meals_logged,
            "weight_change": weight_change,
            "latest_weight": latest_weight,
        }
