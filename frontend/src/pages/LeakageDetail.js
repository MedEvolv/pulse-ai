import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useFilters } from "../context/FilterContext";
import { getLeakage, createIntervention, updateIntervention, claimProof, verifyClosure } from "../lib/api";
import { inr, inrFull, num, titleCase, dt, pct } from "../lib/format";
import { Card, CardHeader, SeverityChip, StatusChip, Avatar, Button, Spinner, ErrorState } from "../components/ui";
import EvidenceDrawer from "../components/EvidenceDrawer";
import { ArrowLeft, FileText, AlertTriangle, Check, ShieldCheck, GitCommitHorizontal } from "lucide-react";

const REL_LABEL = {
  shared: "Shared opportunity pool — not additive across related alerts",
  allocation: "Allocation of the regional pool — non-additive sub-pool",
  diagnostic: "Diagnostic signal — creates no independent recovery pool",
};

const Stat = ({ label, value, accent }) => (
  <div>
    <span className="text-[11px] text-muted block">{label}</span>
    <span className={`text-[13px] font-semibold tabular ${accent || ""}`}>{value}</span>
  </div>
);

export default function LeakageDetail() {
  const { leakageId } = useParams();
  const navigate = useNavigate();
  const { meta } = useFilters();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [drawer, setDrawer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [note, setNote] = useState("");
  const [owner, setOwner] = useState("");
  const [due, setDue] = useState("");
  const [proofForm, setProofForm] = useState({ consecutive_days: 5, note: "" });

  const load = useCallback(() => {
    getLeakage(leakageId).then((d) => {
      setData(d);
      setOwner(d.intervention?.owner_id || "");
      setDue(d.intervention?.due_date || "");
    }).catch(() => setErr("Leakage not found."));
  }, [leakageId]);

  useEffect(() => { load(); }, [load]);

  if (err) return <ErrorState message={err} onRetry={() => navigate("/leakages")} />;
  if (!data) return <Spinner label="Loading leakage" />;

  const { leakage: l, evidence, intervention, proof, metric_evidence: mev } = data;
  const owners = meta?.owners || [];
  const bd = l.severity_breakdown || {};
  const status = intervention?.status || "Detected";
  const allowed = intervention?.allowed_transitions || [];

  const wrap = async (fn, ok) => {
    setBusy(true); setMsg(null);
    try { await fn(); await load(); setMsg({ ok: true, text: ok }); }
    catch (e) { setMsg({ ok: false, text: e?.response?.data?.detail || "Action failed." }); }
    finally { setBusy(false); }
  };

  const ensureIntervention = async () => {
    if (intervention) return intervention.intervention_id;
    const created = await createIntervention({ leakage_id: l.leakage_id, owner_id: owner || null, due_date: due || null });
    return created.intervention_id;
  };

  const assign = () => wrap(async () => {
    const id = await ensureIntervention();
    await updateIntervention(id, { owner_id: owner, due_date: due || null, status: "Assigned", note: "Assigned via cockpit" });
  }, "Intervention assigned.");

  const transition = (to) => wrap(async () => {
    const id = await ensureIntervention();
    await updateIntervention(id, { status: to, note: `Moved to ${to}` });
  }, `Moved to ${to}.`);

  const reject = () => wrap(async () => {
    const id = await ensureIntervention();
    await updateIntervention(id, { status: "Rejected", note: "Recommendation rejected" });
  }, "Recommendation rejected.");

  const addNote = () => wrap(async () => {
    const id = await ensureIntervention();
    await updateIntervention(id, { note });
    setNote("");
  }, "Note added.");

  const submitProof = () => wrap(async () => {
    await claimProof(intervention.intervention_id, {
      metric_id: l.metric_id, metric_evidence_id: l.metric_evidence_id,
      observed_before: l.observed, threshold: l.threshold,
      consecutive_days: Number(proofForm.consecutive_days),
      evidence_ids: (l.evidence_ids || []).slice(0, 3),
      note: proofForm.note || "Recovery proof submitted",
    });
  }, "Closure claimed — awaiting verification.");

  const verify = (decision) => wrap(async () => {
    await verifyClosure(intervention.intervention_id, { decision, verified_by: "OWNER-ANANYA", note: `Verification ${decision}` });
  }, decision === "approved" ? "Verified & closed." : "Sent back (reopened).");

  return (
    <div className="space-y-4" data-testid="leakage-detail-page">
      <button onClick={() => navigate("/leakages")} className="inline-flex items-center gap-1 text-[12px] text-info font-semibold" data-testid="leakage-back">
        <ArrowLeft size={14} /> Back to queue
      </button>

      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight">{titleCase(l.type)}</h1>
          <p className="text-[12px] text-muted">{l.region} · {l.clinic_code || "Region-wide"} · {l.stage_label || l.stage} · {l.leakage_id}</p>
        </div>
        <SeverityChip level={l.severity} score={l.severity_score} testid="detail-severity" />
      </div>

      {/* Relationship banner (CP-01 economic truth) */}
      <div className="text-[11px] bg-canvas border border-line rounded-card px-3 py-2 flex items-center gap-2" data-testid="relationship-banner">
        <GitCommitHorizontal size={14} className="text-accent" />
        <span className="font-semibold text-ink capitalize">{l.opportunity_relationship}</span>
        <span className="text-muted">· {REL_LABEL[l.opportunity_relationship]}</span>
        {l.opportunity_group_id && <span className="ml-auto font-mono text-[10px] text-muted">{l.opportunity_group_id}</span>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader title="Definition & Formula" />
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Stat label="Metric" value={titleCase(l.metric)} />
                <Stat label="Observed" value={l.unit === "rate" ? pct(l.observed) : l.unit === "inr" ? inr(l.observed) : num(l.observed) + (l.unit === "minutes" ? "m" : "")} accent="text-breach" />
                <Stat label="Threshold" value={l.unit === "rate" ? pct(l.threshold) : l.unit === "inr" ? inr(l.threshold) : num(l.threshold) + (l.unit === "minutes" ? "m" : "")} />
                <Stat label="Confidence" value={titleCase(l.confidence)} />
              </div>
              <div className="grid grid-cols-3 gap-3 pt-2 border-t border-line">
                <Stat label="Affected records" value={num(l.affected_record_count ?? l.affected_records?.length ?? 0)} />
                <Stat label="Recoverable appts" value={l.opportunity_relationship === "diagnostic" ? "—" : num(l.recoverable_appointments)} accent="text-healthy" />
                <Stat label="Est. recoverable value" value={l.opportunity_relationship === "diagnostic" ? "Diagnostic (₹0 pool)" : inrFull(l.recoverable_value_inr)} accent="text-healthy" />
              </div>
              <p className="text-[10.5px] text-muted italic">Estimate, not realized revenue. {l.caveats?.join(" · ")}</p>
            </div>
          </Card>

          {mev && (
            <Card>
              <CardHeader title="Aggregate Metric Evidence" subtitle={mev.evidence_id} testid="metric-evidence" />
              <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[12px]">
                <Stat label="Numerator" value={num(mev.numerator)} />
                <Stat label="Denominator" value={num(mev.denominator)} />
                <Stat label="Value" value={mev.value} />
                <Stat label="Affected" value={num(mev.affected_record_count)} />
                <div className="col-span-2 sm:col-span-4">
                  <span className="text-[11px] text-muted block">Cohort hash</span>
                  <span className="font-mono text-[10px] text-ink break-all">{mev.cohort_hash}</span>
                </div>
                <div className="col-span-2 sm:col-span-4 text-[10.5px] text-muted">Limitations: {mev.limitations?.join(" · ")}</div>
              </div>
            </Card>
          )}

          <Card>
            <CardHeader title="Severity Breakdown" subtitle="impact·0.45 + deviation·0.30 + confidence·0.15 + ownership·0.10" />
            <div className="p-4 space-y-2">
              {[["Impact", bd.impact_score, 0.45], ["Deviation", bd.deviation_score, 0.30], ["Confidence", bd.confidence_score, 0.15], ["Ownership urgency", bd.ownership_urgency_score, 0.10]].map(([k, v, w]) => (
                <div key={k}>
                  <div className="flex justify-between text-[11px] mb-0.5"><span className="text-muted">{k} <span className="text-[10px]">×{w}</span></span><span className="tabular font-semibold">{v ?? 0}</span></div>
                  <div className="h-1.5 bg-canvas rounded overflow-hidden border border-line"><div className="h-full bg-accent" style={{ width: `${v || 0}%` }} /></div>
                </div>
              ))}
              <div className="flex justify-between text-[12px] pt-2 border-t border-line"><span className="font-semibold">Severity score</span><span className="tabular font-bold">{l.severity_score}</span></div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Affected Lead IDs" subtitle="Pseudonymous · click a lead to inspect its evidence timeline" />
            <div className="p-4 flex flex-wrap gap-1.5">
              {(l.affected_records || []).slice(0, 40).map((lid) => (
                <button key={lid} onClick={() => navigate(`/journeys/${lid}`)} className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-canvas border border-line hover:border-accent text-ink">{lid}</button>
              ))}
              {(l.affected_records || []).length === 0 && <span className="text-[12px] text-muted">No individual records (contextual/diagnostic signal).</span>}
            </div>
          </Card>
        </div>

        {/* Accountability column (CP-05 proof-based closure) */}
        <div className="space-y-4">
          <Card>
            <CardHeader title="Intervention" right={<Button variant="ghost" onClick={() => setDrawer(true)} data-testid="open-evidence-btn"><FileText size={13} /> Evidence ({evidence.length})</Button>} />
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-muted">Status</span>
                <StatusChip status={status} testid="intervention-status" />
                <span className="ml-auto text-[10px] text-muted">No external writeback</span>
              </div>

              {msg && (
                <div className={`text-[11px] rounded p-2 ${msg.ok ? "bg-healthy/10 text-healthy" : "bg-breach/10 text-breach"}`} data-testid="action-msg">{msg.text}</div>
              )}

              {/* Assignment */}
              <div>
                <label className="text-[11px] text-muted block mb-1">Owner</label>
                <select value={owner} onChange={(e) => setOwner(e.target.value)} data-testid="owner-select"
                  className="w-full bg-surface border border-line rounded-md px-2 py-1.5 text-[12px] hover:border-accent outline-none">
                  <option value="">Unassigned</option>
                  {owners.map((o) => <option key={o.owner_id} value={o.owner_id}>{o.name} · {o.role.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[11px] text-muted block mb-1">Due date</label>
                <input type="date" value={due || ""} onChange={(e) => setDue(e.target.value)} data-testid="due-date-input"
                  className="w-full bg-surface border border-line rounded-md px-2 py-1.5 text-[12px] hover:border-accent outline-none" />
              </div>
              <Button variant="accent" className="w-full" disabled={busy || !owner} onClick={assign} data-testid="assign-intervention-btn">
                {busy ? "Saving…" : "Assign Intervention"}
              </Button>

              {/* State-machine transitions */}
              {allowed.length > 0 && (
                <div className="pt-2 border-t border-line">
                  <p className="text-[11px] text-muted mb-1.5">Move to next stage</p>
                  <div className="grid grid-cols-2 gap-2">
                    {allowed.filter((s) => s !== "Rejected").map((s) => (
                      <Button key={s} variant={s === "Proof Required" ? "info" : "ghost"} disabled={busy}
                        onClick={() => transition(s)} data-testid={`transition-${s.replace(/\s+/g, "-").toLowerCase()}`}>{s}</Button>
                    ))}
                  </div>
                </div>
              )}

              {/* Proof claim (only at Proof Required) */}
              {intervention?.can_claim_proof && (
                <div className="pt-2 border-t border-line space-y-2" data-testid="proof-form">
                  <p className="text-[11px] font-semibold text-ink flex items-center gap-1"><ShieldCheck size={13} className="text-accent" /> Claim closure (structured proof)</p>
                  <div className="flex gap-2 items-center">
                    <label className="text-[11px] text-muted">Consecutive recovery days</label>
                    <input type="number" min="0" value={proofForm.consecutive_days} data-testid="proof-days-input"
                      onChange={(e) => setProofForm({ ...proofForm, consecutive_days: e.target.value })}
                      className="w-16 bg-surface border border-line rounded-md px-2 py-1 text-[12px] tabular outline-none focus:border-accent" />
                  </div>
                  <input value={proofForm.note} onChange={(e) => setProofForm({ ...proofForm, note: e.target.value })}
                    placeholder="Proof note…" data-testid="proof-note-input"
                    className="w-full bg-surface border border-line rounded-md px-2 py-1.5 text-[12px] outline-none focus:border-accent" />
                  <Button variant="accent" className="w-full" disabled={busy} onClick={submitProof} data-testid="claim-closure-btn">Submit proof & claim closure</Button>
                  <p className="text-[10px] text-muted">Requires ≥5 consecutive days. Closure still needs separate verification.</p>
                </div>
              )}

              {/* Verification (only at Closure Claimed) */}
              {intervention?.can_verify && (
                <div className="pt-2 border-t border-line space-y-2" data-testid="verify-block">
                  <p className="text-[11px] font-semibold text-ink">Verify closure claim</p>
                  {proof && (
                    <div className="text-[11px] text-muted bg-canvas rounded p-2 border border-line">
                      Proof {proof.proof_id}: {num(proof.consecutive_days)} days · evidence {proof.evidence_ids?.length || 0} · {proof.note}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <Button variant="accent" disabled={busy} onClick={() => verify("approved")} data-testid="verify-approve-btn"><Check size={13} /> Approve & Close</Button>
                    <Button variant="danger" disabled={busy} onClick={() => verify("rejected")} data-testid="verify-reject-btn">Send back</Button>
                  </div>
                  <p className="text-[10px] text-muted">Separate verification action — the claimer cannot self-close.</p>
                </div>
              )}

              {allowed.includes("Rejected") && (
                <Button variant="danger" className="w-full" disabled={busy} onClick={reject} data-testid="reject-btn">Reject recommendation</Button>
              )}

              <div className="pt-2 border-t border-line">
                <label className="text-[11px] text-muted block mb-1">Add internal note</label>
                <div className="flex gap-2">
                  <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note…" data-testid="note-input"
                    className="flex-1 bg-surface border border-line rounded-md px-2 py-1.5 text-[12px] outline-none focus:border-accent" />
                  <Button variant="ghost" disabled={busy || !note} onClick={addNote} data-testid="add-note-btn">Add</Button>
                </div>
              </div>

              <div className="text-[11px] text-ink bg-canvas rounded p-2 border border-line">
                <span className="font-semibold">Closure criteria:</span> {intervention?.closure_criteria || "Provide proof the metric crossed back over threshold for 5 consecutive days."}
              </div>
            </div>
          </Card>

          {intervention?.history?.length > 0 && (
            <Card>
              <CardHeader title="Status History" />
              <div className="p-4 space-y-2">
                {intervention.history.slice().reverse().map((h, i) => (
                  <div key={i} className="text-[11px] flex items-start gap-2" data-testid={`history-${i}`}>
                    <span className="w-1.5 h-1.5 rounded-full bg-accent mt-1.5 shrink-0" />
                    <div>
                      <span className="font-semibold">{titleCase(h.event)}</span> → <StatusChip status={h.status} />
                      {h.note && <span className="text-muted"> · {h.note}</span>}
                      <span className="text-muted block">{dt(h.at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {l.confidence === "low" && (
            <div className="flex items-start gap-2 text-[11px] text-watch bg-watch/10 border border-watch/20 rounded-card p-3">
              <AlertTriangle size={14} className="mt-0.5" />
              Contextual signal only — not presented as the proven cause of acquisition leakage.
            </div>
          )}
        </div>
      </div>

      <EvidenceDrawer open={drawer} onClose={() => setDrawer(false)} title={titleCase(l.type)} evidence={evidence} />
    </div>
  );
}
