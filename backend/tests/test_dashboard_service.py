"""Unit tests for the dashboard math: hand-made numbers, totals checked by hand.

build_dashboard() is a plain function, so no fakes are even needed: we pass
in rows shaped like the repository's results and check what comes out.
"""

from app.services.dashboard_service import build_dashboard


def net(category_id, name, cents):
    return {"category_id": category_id, "category_name": name, "net_cents": cents}


def budget(category_id, name, cents):
    return {"category_id": category_id, "category_name": name, "limit_cents": cents}


def line(result, name):
    return next(row for row in result["categories"] if row["category_name"] == name)


def test_totals_add_up():
    # Arrange: $5,600 income, $1,650 rent, $412.50 groceries.
    result = build_dashboard(
        [net(10, "Income", 560_000), net(2, "Rent", -165_000), net(1, "Groceries", -41_250)],
        [budget(1, "Groceries", 50_000)],
    )

    assert result["income_cents"] == 560_000
    assert result["spent_cents"] == 165_000 + 41_250    # 206,250 = $2,062.50
    assert result["net_cents"] == 560_000 - 206_250     # 353,750 = $3,537.50
    assert result["budgeted_cents"] == 50_000


def test_under_budget_is_ok_with_the_remaining_amount():
    result = build_dashboard([net(1, "Groceries", -41_250)], [budget(1, "Groceries", 60_000)])

    groceries = line(result, "Groceries")
    assert groceries["remaining_cents"] == 18_750   # $600 - $412.50 = $187.50
    assert groceries["percent_used"] == 68          # 68.75% rounded DOWN
    assert groceries["status"] == "ok"


def test_80_percent_or_more_is_near_the_limit():
    result = build_dashboard([net(1, "Dining out", -16_000)], [budget(1, "Dining out", 20_000)])

    assert line(result, "Dining out")["percent_used"] == 80
    assert line(result, "Dining out")["status"] == "near"


def test_exactly_at_the_limit_is_near_not_over():
    result = build_dashboard([net(1, "Dining out", -20_000)], [budget(1, "Dining out", 20_000)])

    assert line(result, "Dining out")["status"] == "near"
    assert line(result, "Dining out")["remaining_cents"] == 0


def test_one_cent_over_is_over_with_a_negative_remainder():
    result = build_dashboard([net(1, "Dining out", -20_001)], [budget(1, "Dining out", 20_000)])

    assert line(result, "Dining out")["status"] == "over"
    assert line(result, "Dining out")["remaining_cents"] == -1


def test_a_refund_lowers_spending():
    # $140 spent and a $25 refund in the same category: the repository sums them to -$115.
    result = build_dashboard([net(3, "Shopping", -14_000 + 2_500)], [])

    assert line(result, "Shopping")["spent_cents"] == 11_500


def test_a_budget_with_no_spending_still_shows_up():
    result = build_dashboard([], [budget(4, "Transport", 15_000)])

    transport = line(result, "Transport")
    assert (transport["spent_cents"], transport["remaining_cents"], transport["status"]) == (0, 15_000, "ok")


def test_spending_with_no_budget_is_marked_no_budget():
    result = build_dashboard([net(5, "Health", -3_000)], [])

    health = line(result, "Health")
    assert (health["status"], health["limit_cents"], health["percent_used"]) == ("no_budget", None, None)


def test_uncategorized_spending_gets_a_name():
    result = build_dashboard([net(None, None, -999)], [])

    assert line(result, "Uncategorized")["spent_cents"] == 999


def test_income_is_not_listed_as_spending():
    result = build_dashboard([net(10, "Income", 280_000)], [])

    assert result["categories"] == []


def test_biggest_spending_comes_first():
    result = build_dashboard([net(1, "Small", -100), net(2, "Big", -900), net(3, "Middle", -500)], [])

    assert [row["category_name"] for row in result["categories"]] == ["Big", "Middle", "Small"]
