from datetime import datetime


def local_now() -> datetime:
    """Naive local wall-clock now.

    Slot times are generated as naive local clinic hours (9am-5pm — see seed.py) and the
    frontend parses the naive ISO strings we send it as local time too (`new Date(...)`
    with no "Z"/offset suffix is browser-local). This used to return `datetime.now(UTC)`
    instead, which on any machine not in UTC (e.g. IST, UTC+5:30) silently desynced from
    every slot timestamp by the UTC offset — corrupting "is this slot in the past",
    "next available slot", and the cancellation-window check. This app runs for a single
    physical clinic in one timezone, so naive local time consistently everywhere is the
    correct choice, not a shortcut — there's no multi-timezone requirement to hedge for.
    """
    return datetime.now()
