import React, { useEffect, useState, useCallback } from "react";
import { getEvaluation } from "../lib/api";
import { titleCase } from "../lib/format";
import { Card, CardHeader, Button, Spinner, ErrorState } from "../components/ui";
import { CheckCircle2, XCircle, RefreshCw, ShieldCheck } from "lucide-react";

const Ring = ({ score }) => {
  const ok = score >= 85;
  return (
    <div className="relative w-28 h-28">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#D8DEE8" strokeWidth="9" />
        <circle cx="50" cy="50" r="42" fill="none" stroke={ok ? "#17845B" : "#C47A00"} strokeWidth="9"
          strokeDasharray={`${(score / 100) * 264} 264`} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[26px] font-bold tabular">{score}</span>
        <span className="text-[10px] text-muted">overall</span>
      </div>
    </div>
  );
};

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true); setErr(null);
    getEvaluation().then(setData).catch(() => setErr("Could not run evaluation.")).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner label="Running benchmark fixtures" />;
  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!data) return null;

  return (
    <div className="space-y-4" data-testid="evaluation-page">
      <div className="flex items-end justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight flex items-center gap-2"><ShieldCheck size={18} className="text-accent" /> Agent Reliability</h1>
          <p className="text-[12px] text-muted">Deterministic benchmark · rule {data.rule_version} · prompt {data.prompt_version}</p>
        </div>
        <Button variant="ghost" onClick={load} data-testid="rerun-btn"><RefreshCw size={13} /> Re-run</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader title="Overall Score" subtitle={`${data.passed}/${data.scenario_count} fixtures passed`} />
          <div className="p-4 flex flex-col items-center gap-3">
            <Ring score={data.overall_score} />
            <div className="flex gap-3 text-[12px]">
              <span className="text-healthy font-semibold">{data.passed} passed</span>
              <span className="text-breach font-semibold">{data.failed} failed</span>
            </div>
            <p className="text-[10.5px] text-muted text-center">Min thresholds: overall ≥{data.thresholds.overall}%, citation ={data.thresholds.citation_validity}%, privacy ={data.thresholds.privacy}%, numeric ≥{data.thresholds.numeric_fidelity}%</p>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Dimensions" subtitle="Weighted evaluation criteria" />
          <div className="p-4 space-y-2.5" data-testid="dimensions">
            {Object.entries(data.dimensions).map(([k, v]) => (
              <div key={k}>
                <div className="flex justify-between text-[12px] mb-0.5">
                  <span className="text-ink font-medium">{titleCase(k)} <span className="text-[10px] text-muted">·{data.weights[k]}%</span></span>
                  <span className="tabular font-semibold">{v}%</span>
                </div>
                <div className="h-1.5 bg-canvas rounded overflow-hidden border border-line">
                  <div className={`h-full ${v >= 95 ? "bg-healthy" : v >= 85 ? "bg-accent" : "bg-watch"}`} style={{ width: `${v}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Benchmark Fixtures" subtitle="Expected vs actual · 10 deterministic scenarios" />
        <div className="overflow-x-auto scroll-area">
          <table className="w-full text-[12px] min-w-[760px]" data-testid="fixtures-table">
            <thead>
              <tr className="text-muted text-[11px] border-b border-line">
                {["", "Fixture", "Expected", "Cite", "Numeric", "Abstain", "Privacy", "Action", "Overall"].map((h, i) =>
                  <th key={i} className="text-left font-medium px-3 py-2 whitespace-nowrap">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr key={r.fixture} className="border-b border-line tabular" data-testid={`fixture-${r.fixture}`}>
                  <td className="px-3 py-2">{r.passed ? <CheckCircle2 size={15} className="text-healthy" /> : <XCircle size={15} className="text-breach" />}</td>
                  <td className="px-3 py-2 font-semibold whitespace-nowrap">{titleCase(r.fixture)}</td>
                  <td className="px-3 py-2 text-muted text-[11px] max-w-[220px]">{r.expected}</td>
                  <td className="px-3 py-2">{r.scores.citation_validity}</td>
                  <td className="px-3 py-2">{r.scores.numeric_fidelity}</td>
                  <td className="px-3 py-2">{r.scores.abstention}</td>
                  <td className="px-3 py-2">{r.scores.privacy}</td>
                  <td className="px-3 py-2">{r.scores.actionability}</td>
                  <td className="px-3 py-2 font-bold">{r.overall}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
