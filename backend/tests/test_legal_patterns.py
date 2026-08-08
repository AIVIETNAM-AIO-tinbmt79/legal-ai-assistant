from chunking.legal_patterns import (
    match_article,
    match_clause,
    match_point,
    match_named_clause,
    match_named_point,
)


def test_article():
    match = match_article("Điều 8: Phạt vi phạm")

    assert match is not None
    assert match.group(1) == "8"


def test_clause():
    match = match_clause("1. Bên A có trách nhiệm")

    assert match is not None
    assert match.group(1) == "1"


def test_point():
    match = match_point("a) Thanh toán đúng hạn")

    assert match is not None
    assert match.group(1) == "a"


def test_named_clause():
    match = match_named_clause("Khoản 2: Nghĩa vụ của bên B")

    assert match is not None
    assert match.group(1) == "2"


def test_named_point():
    match = match_named_point("Điểm b: Bồi thường thiệt hại")

    assert match is not None
    assert match.group(1) == "b"