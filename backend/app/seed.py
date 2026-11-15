"""Fill the demo user's account with fake transactions and budgets.

Run it with:  python -m app.seed

It REPLACES the demo user's transactions and budgets each time (and touches
no other user), so running it twice gives the same result. The numbers come
from a fixed random seed: the same "today" always produces the same data.
"""

import random
import sys
from datetime import date

from app import db
from app.config import get_settings
from app.dependencies import DEMO_USER_EMAIL
from app.months import month_bounds

# category -> (transactions per month, smallest $, largest $, example descriptions)
SPENDING = {
    "Groceries":     (6, 35, 160, ["Metro", "IGA", "Maxi", "Costco"]),
    "Dining out":    (5, 14, 70, ["Tim Hortons", "Pizza place", "Sushi bar", "Café"]),
    "Transport":     (3, 25, 90, ["STM monthly pass top-up", "Gas station", "Taxi"]),
    "Entertainment": (2, 15, 60, ["Cinema", "Streaming subscription", "Concert"]),
    "Shopping":      (2, 30, 140, ["Clothing store", "Hardware store", "Bookstore"]),
    "Health":        (1, 20, 80, ["Pharmacy"]),
}
FIXED = [  # (day of month, category, cents, description)
    (1, "Rent", -1_650_00, "Rent"),
    (5, "Utilities", -142_37, "Hydro and internet"),
    (15, "Income", 2_800_00, "Salary"),
    (28, "Income", 2_800_00, "Salary"),
]
BUDGETS = {  # category -> monthly limit in cents
    "Rent": 1_650_00, "Groceries": 550_00, "Dining out": 150_00, "Transport": 150_00,
    "Utilities": 160_00, "Entertainment": 80_00, "Shopping": 200_00,
}
MONTHS = 3  # the current month and the two before it


def _months_back(today: date, count: int) -> list[date]:
    """First days of this month and the count-1 months before it, oldest first."""
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append(date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return sorted(months)


def fake_transactions(today: date) -> list[tuple[date, str, int, str]]:
    """(date, category name, cents, description), never after today."""
    rng = random.Random(42)
    rows = []
    for month in _months_back(today, MONTHS):
        days_in_month = (month_bounds(month)[1] - month).days
        for day, category, cents, description in FIXED:
            rows.append((month.replace(day=min(day, days_in_month)), category, cents, description))
        for category, (count, low, high, descriptions) in SPENDING.items():
            for _ in range(count):
                day = rng.randint(1, days_in_month)
                cents = -rng.randint(low * 100, high * 100)
                rows.append((month.replace(day=day), category, cents, rng.choice(descriptions)))
        rows.append((month.replace(day=20), "Shopping", 25_00, "Refund: clothing store"))  # a refund
    return [row for row in rows if row[0] <= today]


def seed_demo_data(today: date) -> dict:
    """Replace the demo user's data. Returns how many rows were written."""
    transactions = fake_transactions(today)
    with db.get_connection() as conn:  # one transaction: all of it or none of it
        conn.execute("INSERT INTO users (email) VALUES (%s) ON CONFLICT (lower(email)) DO NOTHING",
                     (DEMO_USER_EMAIL,))
        user_id = conn.execute("SELECT id FROM users WHERE lower(email) = lower(%s)",
                               (DEMO_USER_EMAIL,)).fetchone()["id"]
        category_ids = {r["name"]: r["id"] for r in
                        conn.execute("SELECT id, name FROM categories WHERE user_id IS NULL")}

        conn.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
        conn.execute("DELETE FROM budgets WHERE user_id = %s", (user_id,))

        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO transactions
                   (user_id, posted_date, amount_cents, description, category_id, category_source)
                   VALUES (%s, %s, %s, %s, %s, 'user')""",
                [(user_id, day, cents, text, category_ids[cat]) for day, cat, cents, text in transactions],
            )
            cur.executemany(
                "INSERT INTO budgets (user_id, category_id, month, limit_cents) VALUES (%s, %s, %s, %s)",
                [(user_id, category_ids[cat], month, limit)
                 for month in _months_back(today, MONTHS) for cat, limit in BUDGETS.items()],
            )
    return {"transactions": len(transactions), "budgets": MONTHS * len(BUDGETS)}


def main() -> int:
    db.open_pool(get_settings())
    try:
        counts = seed_demo_data(date.today())
    finally:
        db.close_pool()
    print(f"demo user {DEMO_USER_EMAIL}: {counts['transactions']} transactions, {counts['budgets']} budgets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
