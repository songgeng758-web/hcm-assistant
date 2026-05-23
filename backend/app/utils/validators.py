"""
通用字段校验器
"""
import re

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def is_valid_phone(value: str) -> bool:
    if not value:
        return False
    return bool(PHONE_PATTERN.match(str(value).strip()))


def is_valid_email(value: str) -> bool:
    if not value:
        return False
    return bool(EMAIL_PATTERN.match(str(value).strip()))


def is_blank(value) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return True
    return False


def clean_header(value: str) -> str:
    """
    清洗 Excel 表头：去除首尾空格、不间断空格、换行符、零宽字符等
    实施顾问常见痛点：客户系统导出的 Excel 表头带各种"看不见的"垃圾字符
    """
    if value is None:
        return ""
    s = str(value)
    # 去除常见不可见字符
    invisible_chars = ["\u00a0", "\u200b", "\u200c", "\u200d", "\ufeff", "\t", "\n", "\r"]
    for ch in invisible_chars:
        s = s.replace(ch, "")
    return s.strip()


# 居民身份证的证件类型常见写法
ID_CARD_TYPES = {
    "居民身份证", "身份证", "中华人民共和国居民身份证",
    "二代身份证", "公民身份证", "id_card",
}


def is_id_card_type(value: str) -> bool:
    """判断证件类型是否为身份证"""
    if not value:
        return False
    return str(value).strip() in ID_CARD_TYPES