"""
身份证工具
-----------
中国大陆 18 位居民身份证号码的解析与校验
身份证规则参考：GB 11643-1999
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


ID_CARD_PATTERN = re.compile(r"^\d{17}[\dXx]$")
WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
CHECK_CODES = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]


@dataclass
class IdCardInfo:
    raw: str
    is_valid: bool
    error: Optional[str] = None
    birth_date: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    region_code: Optional[str] = None


def normalize(id_card: str) -> str:
    if id_card is None:
        return ""
    return str(id_card).strip().upper()


def calc_check_code(id_17: str) -> str:
    total = sum(int(ch) * w for ch, w in zip(id_17, WEIGHTS))
    return CHECK_CODES[total % 11]


def parse(id_card: str, today: Optional[date] = None) -> IdCardInfo:
    raw = normalize(id_card)

    if not raw:
        return IdCardInfo(raw=raw, is_valid=False, error="身份证号为空")
    if len(raw) != 18:
        return IdCardInfo(raw=raw, is_valid=False, error=f"长度错误（应为18位，实际{len(raw)}位）")
    if not ID_CARD_PATTERN.match(raw):
        return IdCardInfo(raw=raw, is_valid=False, error="格式错误（应为17位数字+1位数字或X）")

    try:
        birth = datetime.strptime(raw[6:14], "%Y%m%d").date()
    except ValueError:
        return IdCardInfo(raw=raw, is_valid=False, error="出生日期不合法")

    today = today or date.today()
    if birth > today:
        return IdCardInfo(raw=raw, is_valid=False, error="出生日期晚于今天")
    if birth.year < 1900:
        return IdCardInfo(raw=raw, is_valid=False, error="出生年份早于1900年")

    expected = calc_check_code(raw[:17])
    if raw[17] != expected:
        return IdCardInfo(
            raw=raw,
            is_valid=False,
            error=f"校验码错误（应为{expected}，实际{raw[17]}）",
        )

    gender = "男" if int(raw[16]) % 2 == 1 else "女"
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    return IdCardInfo(
        raw=raw,
        is_valid=True,
        birth_date=birth,
        age=age,
        gender=gender,
        region_code=raw[:6],
    )


def is_valid(id_card: str) -> bool:
    return parse(id_card).is_valid