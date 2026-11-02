from datetime import date, datetime, time, timedelta, timezone

# Costa Rica no usa horario de verano: UTC-6 todo el año.
COSTA_RICA_TZ = timezone(timedelta(hours=-6))


def costa_rica_today() -> date:
    return datetime.now(COSTA_RICA_TZ).date()


def local_date(moment: datetime) -> date:
    """Fecha en Costa Rica de un instante guardado en UTC."""
    return moment.astimezone(COSTA_RICA_TZ).date()


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=COSTA_RICA_TZ)


def day_end(day: date) -> datetime:
    return datetime.combine(day, time.max, tzinfo=COSTA_RICA_TZ)
