"""Pre-canned operator query library (deepening #5; ADR-0003).

~30 questions per sector (6 per cycle stage across the 5 answer domains) for all
6 sectors. Sector-shaped via the governance stage labels. Deterministic — same
sector profiles in, same library out. No free-text in v1.0.
"""
from __future__ import annotations

from functools import lru_cache

from engine import sector_governance
from engine.operator_query import OperatorQuery

# 6 templates per stage -> ~30 per sector. (label) is the sector-shaped stage name.
_TEMPLATES = [
    ("ltv_cac", "What is the LTV:CAC at the {label} stage?"),
    ("binding_constraint", "Is {label} the binding constraint right now?"),
    ("critical_few", "Which cohorts drive most of the {label} opportunity?"),
    ("closure_history", "What closure proofs back the {label} stage?"),
    ("narrative", "Why did {label} move this period?"),
    ("narrative", "What is the single move on {label}?"),
]


def _build_for_sector(sector_id: str) -> list:
    profile = sector_governance.load_sector(sector_id)
    if not profile:
        return []
    out: list[OperatorQuery] = []
    for stage in sector_governance.CYCLE_STAGES:
        label = profile.stage_label(stage)
        ids_here = []
        for i, (answer_type, template) in enumerate(_TEMPLATES):
            qid = f"OQ-{sector_id}-{stage}-{i+1}"
            ids_here.append(qid)
            out.append(OperatorQuery(
                query_id=qid,
                query_text=template.format(label=label),
                sector=sector_id,
                stage=stage,
                answer_type=answer_type,
            ))
        # link the questions of the same stage as 'related'
        for q in out[-len(_TEMPLATES):]:
            q.related = [x for x in ids_here if x != q.query_id]
    return out


@lru_cache(maxsize=1)
def build_library() -> tuple:
    """The full pre-canned library across all sectors (immutable tuple)."""
    library: list[OperatorQuery] = []
    for sid in sector_governance.list_sectors():
        library.extend(_build_for_sector(sid))
    return tuple(library)
