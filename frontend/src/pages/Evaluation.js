import React, { useEffect, useState, useCallback } from "react";
import { getEvaluation } from "../lib/api";
import { titleCase } from "../lib/format";
import { Card, CardHeader, Button, Spinner, ErrorState } from "../components/ui";
import { CheckCircle2, XCircle, RefreshCw, ShieldCheck, FlaskConical } from "lucide-react";

const Ring = ({ score, ok }) => (
  <div className="relative w-28 h-28">
    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
      <circle cx="50" cy="50" r="42" fill="none" stroke="#D8DEE8" strokeWidth="9" />
      <circle cx="50" cy="50" r="42" fill="none" stroke={ok ? "#17845B" : "#C47A00"} strokeWidth="9"
        strokeDasharray={`${(score / 100) * 264} 264`} strokeLinecap="round" />
    </svg>
    <div className="absolute inset-0 flex flex-col items-center justify-center">
      <span className="text-[24px] font-bold tabular">{score}</span>
      <span className="text-[9px] text-muted">offline</span>
    </div>
  </div>
);

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true); setErr(null);
    getEvaluation().then(setData).catch(() => setErr("Could not run evaluation.")).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner label="Running offline fixtures" />;
  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!data) return null;

  return (
    <div className="space-y-4" data-testid="evaluation-page">
      <div className="flex items-end justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight flex items-center gap-2"><ShieldCheck size={18} className="text-accent" /> {data.name}</h1>
          <p className="text-[12px] text-muted">{data.eval_version} · rule {data.rule_version} · prompt {data.prompt_version}</p>
        </div>
        <Button variant="ghost" onClick={load} data-testid="rerun-btn"><RefreshCw size={13} /> Re-run</Button>
      </div>

      <div className="flex items-start gap-2 text-[11px] text-info bg-info/5 border border-info/20 rounded-card p-3" data-testid="eval-disclaimer">
        <FlaskConical size={14} className="mt-0.5 shrink-0" />
        <span>{data.disclaimer} Deterministic contract tests executed: {data.modes?.deterministic_contract_tests?.case_count}. Optional model contract tests: not executed (consume budget).</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader title="Overall Score" subtitle={`${data.passed}/${data.scenario_count} fixtures passed`} />
          <div className="p-4 flex flex-col items-center gap-3">
            <Ring score={data.overall_score} ok={data.overall_score >= data.release_thresholds.overall} />
            <div className="flex gap-3 text-[12px]">
              <span className="text-healthy font-semibold">{data.passed} passed</span>
              <span className="text-breach font-semibold">{data.failed} failed</span>
            </div>
            <span className={`text-[11px] font-semibold px-2 py-1 rounded ${data.release_ready ? "bg-healthy/10 text-healthy" : "bg-watch/10 text-watch"}`} data-testid="release-ready">
              {data.release_ready ? "Release gates met" : "Release gates not met"}
            </span>
            <p className="text-[10px] text-muted text-center">Gates: privacy {data.release_thresholds.privacy_safety}, provenance {data.release_thresholds.provenance_validity}, action {data.release_thresholds.action_boundary_compliance}, overall ≥{data.release_thresholds.overall}</p>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Dimensions" subtitle="Scores computed from executed assertions only — no hardcoded values" />
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-x-5 gap-y-2.5" data-testid="dimensions">
            {Object.entries(data.dimensions).map(([k, v]) => (
              <div key={k}>
                <div className="flex justify-between text-[12px] mb-0.5">
                  <span className="text-ink font-medium">{titleCase(k)} <span className="text-[10px] text-muted">·{data.weights[k]}%</span></span>
                  <span className="tabular font-semibold">{v}%</span>
                </div>
                <div className="h-1.5 bg-canvas rounded overflow-hidden border border-line">
                  <div className={`h-full ${v >= 100 ? "bg-healthy" : v >= 90 ? "bg-accent" : "bg-watch"}`} style={{ width: `${v}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Adversarial Fixtures" subtitle="Each injects its named fault and runs through production validation logic" />
        <div className="overflow-x-auto scroll-area">
          <table className="w-full text-[12px] min-w-[820px]" data-testid="fixtures-table">
            <thead>
              <tr className="text-muted text-[11px] border-b border-line">
                {["", "Case", "Description", "Dimension", "Expected", "Actual reason", "Assertions"].map((h, i) =>
                  <th key={i} className="text-left font-medium px-3 py-2 whitespace-nowrap">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr key={r.case_id} className="border-b border-line tabular align-top" data-testid={`fixture-${r.case_id}`}>
                  <td className="px-3 py-2">{r.passed ? <CheckCircle2 size={15} className="text-healthy" /> : <XCircle size={15} className="text-breach" />}</td>
                  <td className="px-3 py-2 font-mono text-[10px] whitespace-nowrap">{r.case_id}</td>
                  <td className="px-3 py-2 text-muted max-w-[240px]">{r.description}</td>
                  <td className="px-3 py-2 text-[10px]">{titleCase(r.dimension)}</td>
                  <td className="px-3 py-2 text-[10px]">{r.expected.accepted ? "accept" : "reject"}{r.expected.reason_code ? ` · ${r.expected.reason_code}` : ""}</td>
                  <td className="px-3 py-2 font-mono text-[10px]">{r.actual.reason_code || (r.actual.accepted ? "accepted" : "—")}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {r.assertions.map((a, i) => (
                        <span key={i} className={`text-[9px] px-1 py-0.5 rounded ${a.passed ? "bg-healthy/10 text-healthy" : "bg-breach/10 text-breach"}`}>{a.name}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
