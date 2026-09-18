"""現在時刻（UTC）を返すだけの依存（設計仕様書 9 章 Clock）。

取引日（JST）は PricingService がこの時刻を BUSINESS_TIMEZONE に変換して作る。
date.today() や SQL の CURDATE() は使わない（6.1, DB-4）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Protocol
from zoneinfo import ZoneInfo

from .config import LIMITS


class Clock(Protocol):
    def now_utc(self) -> datetime: ...


class SystemClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """テスト用。固定した UTC 時刻を返す。"""

    def __init__(self, fixed: datetime):
        if fixed.tzinfo is None:
            raise ValueError("FixedClock には tz 付きの datetime を渡してください")
        self._fixed = fixed.astimezone(timezone.utc)

    def now_utc(self) -> datetime:
        return self._fixed


def business_date_of(now_utc: datetime, tz_name: str | None = None) -> date:
    """UTC 時刻 → 業務タイムゾーン（既定 Asia/Tokyo）の日付。"""
    if now_utc.tzinfo is None:
        raise ValueError("now_utc は tz 付きである必要があります")
    return now_utc.astimezone(ZoneInfo(tz_name or LIMITS.BUSINESS_TIMEZONE)).date()


def get_clock() -> Clock:
    return SystemClock()
