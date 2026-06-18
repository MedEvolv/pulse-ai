"""3-adapter query dispatch (deepening #5; ADR-0003/0004).

The operator query runs through three adapters, in order:

  1. Qdrant retrieval   -> top-k ClosureEvents from the append-only spine (#2)
  2. Engine computation -> typed LtvCac / BindingConstraint / CriticalFew (#4)
  3. AINarrative wrap   -> #3 narrative whose provenance cites the REAL refs

Every answer is grounded in real OpportunityGroup (#1) + ClosureEvent (#2) ids,
across the three knowledge layers (sector / company / customer). Q3: the company
layer compounds as operators engage and closure events accrue in the spine.
"""
from __future__ import annotations

from engine import ai_evidence, cycle_compute
from engine.operator_query import OperatorQuery
from engine.provenance_lineage import KnowledgeLayerRef


class QdrantClosureRetriever:
    """Adapter 1 — Qdrant-shaped retrieval over the closure event spine.

    Functional bounded stand-in (v1.0): returns the top-k ClosureEvents most
    relevant to the query's opportunity group, capped at 5. Real embedding-based
    retrieval (Qdrant + cross-encoder rerank) is the v1.1 wiring; the interface
    (retrieve -> ranked top-k) is the same.
    """

    MAX_RESULTS = 5

    def __init__(self, spine):
        self.spine = spine

    def retrieve(self, opportunity_group_ref, sector, k: int = MAX_RESULTS) -> list:
        k = min(k, self.MAX_RESULTS)
        events = self.spine.all()
        # rank: events citing this opportunity group first, then the rest (stable)
        ranked = sorted(events, key=lambda e: 0 if e.opportunity_group_ref == opportunity_group_ref else 1)
        return ranked[:k]


def dispatch(query: OperatorQuery, region: str, spine, now_iso: str) -> dict:
    """Run the 3-adapter pipeline and return a typed, provenance-bearing answer."""
    sector = query.sector

    # 2. Engine computation (typed #4) — the grounded numbers + refs.
    ltv = cycle_compute.regional_ltv_cac(region, sector)
    bc = cycle_compute.regional_binding_constraint(region, sector)
    cf = cycle_compute.regional_critical_few(region, sector)
    opp_ref = cf.items[0]["opportunity_group_ref"] if cf.items else None

    # 1. Qdrant retrieval (top-k ClosureEvents from the spine, <= 5).
    retriever = QdrantClosureRetriever(spine)
    closure_events = retriever.retrieve(opp_ref, sector)

    # 3. AINarrative wrap (#3) — provenance cites real OpportunityGroup + ClosureEvent ids.
    narrative = ai_evidence.build_narrative(region, sector, query.query_text, "operator", spine, now_iso)

    if query.answer_type == "ltv_cac":
        answer = ltv.model_dump()
    elif query.answer_type == "binding_constraint":
        answer = bc.model_dump() if bc else None
    elif query.answer_type == "critical_few":
        answer = cf.model_dump()
    elif query.answer_type == "closure_history":
        answer = {"closure_events": [e.model_dump() for e in closure_events],
                  "count": len(closure_events)}
    else:  # narrative
        answer = {"headline": narrative.headline, "summary": narrative.summary}

    # 3 knowledge layers (reuse #3's KnowledgeLayerRef).
    knowledge_layers = [
        KnowledgeLayerRef(layer="sector", source_id=f"sector:{sector}", last_reviewed=now_iso),
        KnowledgeLayerRef(layer="company", source_id=f"company:{region}", last_reviewed=now_iso),
        KnowledgeLayerRef(layer="customer", source_id=f"customer:anon:{region}", last_reviewed=now_iso),
    ]

    return {
        "query": query.model_dump(),
        "answer_type": query.answer_type,
        "answer": answer,
        "narrative": narrative.model_dump(),
        "provenance": narrative.provenance_lineage.model_dump(),
        "knowledge_layers": [k.model_dump() for k in knowledge_layers],
        "retrieved_closure_event_ids": [e.closure_id for e in closure_events],
        "opportunity_group_ref": narrative.provenance_lineage.engine_computation.opportunity_group_ref,
        "adapters": ["qdrant_closure_retriever", "engine_computation", "ai_narrative"],
    }
