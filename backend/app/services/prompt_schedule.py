"""
@file prompt_schedule.py
@brief Pure schedule matching for tradition prompts.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from dateutil.rrule import rrulestr

from app.models.prompt import Prompt


def should_fire(prompt: Prompt, today: date) -> bool:
    """
    @brief Decide whether a prompt should fire on ``today``.

    @param prompt The prompt to evaluate.
    @param today The date to evaluate against (UTC).
    @return True if the prompt's schedule matches today.
    """
    if not prompt.is_enabled:
        return False

    ftype = prompt.frequency_type
    if ftype == "daily":
        return True
    if ftype == "annual_date":
        return prompt.trigger_month == today.month and prompt.trigger_day == today.day
    if ftype == "weekly":
        if prompt.trigger_weekday is None:
            return False
        return today.weekday() == prompt.trigger_weekday
    if ftype == "monthly":
        return prompt.trigger_month_day == today.day
    if ftype == "one_time":
        return prompt.trigger_one_time_date == today
    if ftype == "custom":
        if not prompt.trigger_custom_rule:
            return False
        try:
            dtstart = datetime.combine(today, datetime.min.time())
            rule = rrulestr(prompt.trigger_custom_rule, dtstart=dtstart)
        except Exception:  # noqa: BLE001
            return False
        next_run = rule.after(
            datetime.combine(today - timedelta(days=1), datetime.max.time()),
            inc=True,
        )
        if next_run is None:
            return False
        return next_run.date() == today
    return False
