"""Search query parsing and SQL filter builder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

TOKEN_RE = re.compile(r"(?P<key>\w+):(?P<value>[^\s]+)")
OP_RE = re.compile(r"(?P<key>\w+)(?P<op>>=|<=|>|<)(?P<value>[^\s]+)")

ALLOWED_KEYS = {"label", "model", "user", "date", "conf", "latency"}
NUM_KEYS = {"conf", "latency"}

FIELD_MAP = {
    "label": "p.top1_label",
    "model": "p.model_name",
    "user": "u.username",
    "conf": "p.top1_conf",
    "latency": "p.latency_ms",
}


@dataclass
class ParsedQuery:
    """Represent ParsedQuery."""

    filters: list[tuple[str, str, str]]
    free_text: list[str]


def parse_search_query(q: str) -> ParsedQuery:
    """Execute parse search query."""
    filters: list[tuple[str, str, str]] = []
    free_text: list[str] = []
    if not q:
        return ParsedQuery(filters, free_text)
    for token in q.split():
        op_match = OP_RE.match(token)
        if op_match:
            key = op_match.group("key")
            if key in ALLOWED_KEYS:
                filters.append((key, op_match.group("op"), op_match.group("value")))
                continue
        token_match = TOKEN_RE.match(token)
        if token_match:
            key = token_match.group("key")
            if key in ALLOWED_KEYS:
                filters.append((key, ":", token_match.group("value")))
                continue
        free_text.append(token)
    return ParsedQuery(filters, free_text)


def _parse_date_range(value: str) -> tuple[str, str] | None:
    """Execute parse date range."""
    if ".." in value:
        start_raw, end_raw = value.split("..", 1)
        try:
            start = datetime.strptime(start_raw, "%Y-%m-%d")
            end = datetime.strptime(end_raw, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            return None
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
    try:
        day = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    start = day
    end = day + timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def build_where_clause(search_text: str, filters: dict) -> tuple[str, list]:
    """Execute build where clause."""
    clauses: list[str] = []
    params: list = []
    parsed = parse_search_query(search_text)

    for key, op, value in parsed.filters:
        if key == "date":
            date_range = _parse_date_range(value)
            if not date_range:
                continue
            clauses.append("p.created_at >= ? AND p.created_at < ?")
            params.extend(date_range)
            continue
        field = FIELD_MAP.get(key)
        if not field:
            continue
        if key in NUM_KEYS and op in {">", ">=", "<", "<="}:
            try:
                number = float(value)
            except ValueError:
                continue
            clauses.append(f"{field} {op} ?")
            params.append(number)
        elif op == ":":
            clauses.append(f"{field} = ?")
            params.append(value)

    free_text = " ".join(parsed.free_text).strip()
    if free_text:
        like = f"%{free_text}%"
        clauses.append("(p.top1_label LIKE ? OR p.notes LIKE ? OR p.input_ref LIKE ?)")
        params.extend([like, like, like])

    if filters.get("model"):
        clauses.append("p.model_name = ?")
        params.append(filters["model"])
    if filters.get("label"):
        clauses.append("p.top1_label = ?")
        params.append(filters["label"])
    if filters.get("user"):
        clauses.append("u.username = ?")
        params.append(filters["user"])
    if filters.get("date_from"):
        clauses.append("p.created_at >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("p.created_at < ?")
        params.append(filters["date_to"])
    if filters.get("conf_min") is not None:
        clauses.append("p.top1_conf >= ?")
        params.append(filters["conf_min"])
    if filters.get("conf_max") is not None:
        clauses.append("p.top1_conf <= ?")
        params.append(filters["conf_max"])
    if filters.get("latency_max") is not None:
        clauses.append("p.latency_ms <= ?")
        params.append(filters["latency_max"])

    where_sql = ""
    if clauses:
        where_sql = " WHERE " + " AND ".join(clauses)
    return where_sql, params
