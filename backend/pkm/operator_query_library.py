"""Operator query library access (deepening #5; ADR-0003).

The "Ask [Company]:" lookup surface over the pre-canned library. Lives in the PKM
layer because the library is the operator's entry into the company knowledge.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from engine.operator_query import OperatorQuery
from engine.pre_canned_library import build_library


@lru_cache(maxsize=1)
def _by_id() -> dict:
    return {q.query_id: q for q in build_library()}


def get_question(query_id: str) -> Optional[OperatorQuery]:
    return _by_id().get(query_id)


def questions_for_sector(sector: str) -> list:
    return [q for q in build_library() if q.sector == sector]


def questions_for_stage(sector: str, stage: str) -> list:
    return [q for q in build_library() if q.sector == sector and q.stage == stage]


def count_for_sector(sector: str) -> int:
    return len(questions_for_sector(sector))
