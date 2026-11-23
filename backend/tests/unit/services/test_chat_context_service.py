"""
@file test_chat_context_service.py
@brief Unit tests for birthday math in the chat context service.
"""

from datetime import date

from app.services.chat_context_service import days_until_birthday


def test_birthday_today_and_wrap() -> None:
    assert days_until_birthday(date(1990, 5, 5), date(2026, 5, 5)) == 0
    assert days_until_birthday(date(1990, 1, 1), date(2026, 12, 31)) == 1


def test_leap_day_in_common_year() -> None:
    assert days_until_birthday(date(2000, 2, 29), date(2027, 2, 27)) == 1
