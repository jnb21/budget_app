"""Spending vs. budget for one month.

The math lives in build_dashboard(), a plain function with no database, so it
can be tested with hand-made numbers. All amounts are integer cents.
"""

from datetime import date

from app.months import month_bounds
from app.repositories.budget_repository import BudgetRepository
from app.repositories.transaction_repository import TransactionRepository

NEAR_LIMIT_PERCENT = 80  # at or above this share of the budget, warn


def build_dashboard(net_by_category: list[dict], budgets: list[dict]) -> dict:
    """
    net_by_category: [{category_id, category_name, net_cents}] (spending is negative)
    budgets:         [{category_id, category_name, limit_cents}]

    A category's "spent" is its net outflow, so a $20 refund lowers it by $20.
    Categories where more came in than went out (like Income) count as income.
    """
    income = sum(row["net_cents"] for row in net_by_category if row["net_cents"] > 0)
    spent_by_id = {row["category_id"]: -row["net_cents"] for row in net_by_category if row["net_cents"] < 0}
    names = {row["category_id"]: row["category_name"] for row in [*net_by_category, *budgets]}
    limits = {b["category_id"]: b["limit_cents"] for b in budgets}

    rows = []
    for category_id in spent_by_id.keys() | limits.keys():
        spent = spent_by_id.get(category_id, 0)
        limit = limits.get(category_id)
        if limit is None:
            percent, status, remaining = None, "no_budget", None
        else:
            percent = spent * 100 // limit           # whole percent, rounded down
            remaining = limit - spent
            status = "over" if spent > limit else "near" if percent >= NEAR_LIMIT_PERCENT else "ok"
        rows.append({
            "category_id": category_id,
            "category_name": names.get(category_id) or "Uncategorized",
            "spent_cents": spent,
            "limit_cents": limit,
            "remaining_cents": remaining,
            "percent_used": percent,
            "status": status,
        })

    rows.sort(key=lambda r: (-r["spent_cents"], r["category_name"].lower()))  # biggest spending first
    total_spent = sum(spent_by_id.values())
    return {
        "income_cents": income,
        "spent_cents": total_spent,
        "net_cents": income - total_spent,
        "budgeted_cents": sum(limits.values()),
        "categories": rows,
    }


class DashboardService:
    def __init__(self, transactions: TransactionRepository, budgets: BudgetRepository):
        self._transactions = transactions
        self._budgets = budgets

    def summary(self, user_id: int, month: date) -> dict:
        net = self._transactions.net_by_category(user_id, *month_bounds(month))
        budgets = self._budgets.list_for_month(user_id, month)
        return {"month": month.strftime("%Y-%m"), **build_dashboard(net, budgets)}
