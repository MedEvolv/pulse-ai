import React, { useState } from "react";
import { Search, Sparkles, ShieldCheck, AlertTriangle, ChevronRight, Cpu, FileCheck } from "lucide-react";
import { postBrief } from "../lib/api";
import { Button, Spinner } from "./ui";
import EvidenceDrawer from "./EvidenceDrawer";

const CONF_COLOR = { high: "text-healthy", medium: "text-watch", low: "text-breach" };

export default function BriefPanel({ region, questions = [], regionName }) {
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState(null);
  const [query, setQuery] = useState("");
  const [drawer, setDrawer] = useState({ open: false, ids: [] });

  const run = async (question) => {
    setLoading(true);
    setBrief(null);
    try {
      const data = await postBrief({ region, question: question || query, use_model: true });
      setBrief(data);
    } catch (e) {
      setBrief({ error: "Brief generation failed. Try again." });
    } finally {
      setLoading(false);
    }
  };

  const pool = brief?.evidence_pool || [];
  const openEvidence = (ids) =>
    setDrawer({ open: true, ids: pool.filter((e) => ids.includes(e.evidence_id)) });

  return (
    <div className="bg-surface border border-line rounded-card shadow-tile" data-testid="brief-panel">
      <div className="px-4 py-3 border-b border-line flex items-center justify-between">
        <div>
          <h3 className="text-[13px] font-semibold flex items-center gap-1.5">
            <Sparkles size={15} className="text-accent" /> What changed and why it matters
          </h3>
          <p className="text-[11px] text-muted mt-0.5">Evidence-bound regional briefing</p>
        </div>
        {brief && !brief.error && (
          <span
            data-testid="brief-mode"
            className={`text-[10px] font-semibold px-2 py-1 rounded inline-flex items-center gap-1 ${
              brief.fallback_active ? "bg-info/10 text-info" : "bg-accent/10 text-accent"
            }`}
          >
            {brief.fallback_active ? <FileCheck size={11} /> : <Cpu size={11} />}
            {brief.mode === "model" ? "AI brief · Claude" : brief.mode === "bounded" ? "Bounded" : "Deterministic briefing"}
          </span>
        )}
      </div>

      <div className="p-4">
        {/* Search-first */}
        <div className="flex gap-2 mb-2">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input
              data-testid="brief-search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="Ask a question about this region…"
              className="w-full pl-8 pr-3 py-2 text-[12px] bg-canvas border border-line rounded-md focus:border-accent outline-none"
            />
          </div>
          <Button variant="accent" onClick={() => run()} data-testid="brief-ask-btn" disabled={loading}>
            Ask
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5 mb-3">
          {questions.map((q) => (
            <button
              key={q}
              data-testid="suggested-question"
              onClick={() => run(q)}
              className="text-[11px] px-2 py-1 rounded-full border border-line text-ink/80 hover:border-accent hover:text-accent transition-colors"
            >
              {q}
            </button>
          ))}
        </div>

        {loading && <Spinner label="Briefing agent thinking" />}

        {!loading && !brief && (
          <div className="text-center py-6 text-[12px] text-muted" data-testid="brief-empty">
            Select a question to generate an evidence-bound brief for {regionName} Region.
          </div>
        )}

        {brief?.error && <div className="text-[12px] text-breach py-4">{brief.error}</div>}

        {brief && !brief.error && (
          <div className="space-y-3 fade-up" data-testid="brief-content">
            {brief.insufficient_evidence ? (
              <div className="flex items-start gap-2 p-3 rounded-card bg-watch/10 border border-watch/20">
                <AlertTriangle size={16} className="text-watch mt-0.5" />
                <div>
                  <p className="text-[13px] font-semibold text-ink">{brief.headline}</p>
                  <p className="text-[12px] text-muted mt-0.5">{brief.summary}</p>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <p className="text-[14px] font-bold text-ink leading-snug" data-testid="brief-headline">
                    {brief.headline}
                  </p>
                  <p className="text-[12px] text-muted mt-1">{brief.summary}</p>
                </div>

                <div className="space-y-2">
                  {(brief.top_findings || []).map((f, i) => (
                    <div key={i} className="border border-line rounded-card p-3" data-testid={`brief-finding-${i}`}>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-[12.5px] font-semibold text-ink">{f.finding}</p>
                        <span className={`text-[10px] font-semibold uppercase shrink-0 ${CONF_COLOR[f.confidence] || "text-muted"}`}>
                          {f.confidence}
                        </span>
                      </div>
                      <p className="text-[11.5px] text-muted mt-1">{f.why_it_matters}</p>
                      {f.evidence_ids?.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 mt-2">
                          {f.evidence_ids.map((eid) => (
                            <button
                              key={eid}
                              onClick={() => openEvidence([eid])}
                              data-testid={`evidence-chip-${eid}`}
                              className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent hover:bg-accent/20"
                            >
                              {eid}
                            </button>
                          ))}
                          <button
                            onClick={() => openEvidence(f.evidence_ids)}
                            className="text-[10px] text-info font-semibold inline-flex items-center"
                          >
                            view evidence <ChevronRight size={11} />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {brief.recommended_interventions?.length > 0 && (
                  <div className="rounded-card bg-canvas border border-line p-3">
                    <p className="text-[11px] font-semibold text-muted uppercase tracking-wide mb-2">Recommended interventions</p>
                    <ul className="space-y-1.5">
                      {brief.recommended_interventions.map((iv, i) => (
                        <li key={i} className="flex items-center gap-2 text-[12px]" data-testid={`brief-intervention-${i}`}>
                          <ShieldCheck size={13} className="text-accent shrink-0" />
                          <span className="text-ink">{iv.title}</span>
                          <span className="ml-auto text-[10px] text-muted bg-surface border border-line px-1.5 py-0.5 rounded">
                            {iv.owner_role?.replace(/_/g, " ")}
                          </span>
                          <span className="text-[10px] text-info">human-approved</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {brief.caveats?.length > 0 && (
                  <p className="text-[10.5px] text-muted italic">
                    Caveats: {brief.caveats.join(" · ")}
                  </p>
                )}
                {brief.generated_at && (
                  <p className="text-[10px] text-muted">Generated {new Date(brief.generated_at).toLocaleString("en-IN")}</p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <EvidenceDrawer
        open={drawer.open}
        onClose={() => setDrawer({ open: false, ids: [] })}
        title="Brief finding evidence"
        evidence={drawer.ids}
      />
    </div>
  );
}
