"""The sign-up form (frontend/src/passwordRules.js) and the backend check the
same password rules. This test reads the frontend file and fails if the two
copies drift apart, e.g. a common password added on one side only.
"""

import re
from pathlib import Path

from app.services import auth_service

FRONTEND_RULES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "passwordRules.js"


def js_constant(name: str) -> str:
    match = re.search(rf"export const {name} = (\d+)", FRONTEND_RULES.read_text(encoding="utf-8"))
    assert match, f"{name} not found in {FRONTEND_RULES}"
    return match[1]


def test_the_common_password_lists_are_identical():
    source = FRONTEND_RULES.read_text(encoding="utf-8")
    block = source[source.index("const COMMON = new Set(["):source.index("])", source.index("const COMMON"))]
    frontend = set(re.findall(r"'([^']*)'", block))

    assert frontend == set(auth_service.COMMON_PASSWORDS)


def test_the_length_limits_are_identical():
    assert int(js_constant("MIN_PASSWORD")) == auth_service.MIN_PASSWORD_LENGTH
    assert int(js_constant("MAX_PASSWORD")) == auth_service.MAX_PASSWORD_LENGTH
