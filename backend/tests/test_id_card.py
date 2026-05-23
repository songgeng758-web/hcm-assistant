"""
身份证工具单元测试
"""
from datetime import date

from app.utils import id_card


def _make_valid_id(birth_str: str = "19900307", seq: str = "881") -> str:
    """工具：根据出生日期和顺序码，构造一个校验位正确的身份证号"""
    prefix = "110101" + birth_str + seq
    return prefix + id_card.calc_check_code(prefix)


def test_parse_valid_male():
    valid = _make_valid_id("19900307", "881")
    info = id_card.parse(valid, today=date(2025, 1, 1))
    assert info.is_valid
    assert info.birth_date == date(1990, 3, 7)
    assert info.gender == "男"
    assert info.age == 34


def test_parse_valid_female():
    valid = _make_valid_id("19900307", "882")
    info = id_card.parse(valid, today=date(2025, 1, 1))
    assert info.is_valid
    assert info.gender == "女"


def test_age_before_birthday():
    valid = _make_valid_id("19900307", "881")
    info = id_card.parse(valid, today=date(2025, 3, 6))
    assert info.age == 34
    info = id_card.parse(valid, today=date(2025, 3, 7))
    assert info.age == 35


def test_invalid_length():
    info = id_card.parse("123")
    assert not info.is_valid
    assert "长度" in info.error


def test_invalid_check_code():
    valid = _make_valid_id("19900307", "881")
    bad = valid[:-1] + ("0" if valid[-1] != "0" else "1")
    info = id_card.parse(bad)
    assert not info.is_valid
    assert "校验码" in info.error


def test_invalid_birth():
    info = id_card.parse("110101199013078812")
    assert not info.is_valid


def test_empty():
    info = id_card.parse("")
    assert not info.is_valid
    info = id_card.parse(None)
    assert not info.is_valid


def test_normalize_lowercase_x():
    valid = _make_valid_id("19900307", "881")
    if valid.endswith("X"):
        info = id_card.parse(valid.lower())
        assert info.is_valid