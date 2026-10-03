from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def local_midnight(day: date, tz: str) -> datetime:
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(tz)).astimezone(UTC)


def local_range_to_utc(
    date_from: date | None, date_to: date | None, tz: str
) -> tuple[datetime | None, datetime | None]:
    start = local_midnight(date_from, tz) if date_from else None
    end = local_midnight(date_to + timedelta(days=1), tz) if date_to else None
    return start, end


def local_today(tz: str, now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(tz)).date()
