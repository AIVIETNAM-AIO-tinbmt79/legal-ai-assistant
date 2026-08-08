import re


# =========================
# Article
# =========================

ARTICLE_PATTERN = re.compile(
    r"^\s*Điều\s+(\d+)"
    r"(?:\s*[\.:]?\s*(.*))?$",
    re.IGNORECASE,
)


# =========================
# Section
# =========================

SECTION_PATTERN = re.compile(
    r"^\s*"
    r"([IVXLCDM]+)"
    r"[\.\)]\s+"
    r"(.+?)"
    r"\s*$",
    re.IGNORECASE,
)


# =========================
# Clause
# =========================

CLAUSE_PATTERN = re.compile(
    r"^\s*(\d+)[\.\)]\s+(.+)$"
)


# =========================
# Point
# =========================

POINT_PATTERN = re.compile(
    r"^\s*([a-zA-Z])[\.\)]\s+(.+)$"
)


def match_article(line: str):
    return ARTICLE_PATTERN.match(line)


def match_section(line: str):
    return SECTION_PATTERN.match(line)


def match_clause(line: str):
    return CLAUSE_PATTERN.match(line)


def match_point(line: str):
    return POINT_PATTERN.match(line)