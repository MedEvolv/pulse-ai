import React, { useEffect, useState, useCallback } from "react";
import { useFilters } from "../context/FilterContext";
import { getDataQuality } from "../lib/api";
import { num, pct } from "../lib/format";
import { Card, CardHeader, StatusChip, Spinner, ErrorState } from "../components/ui";
import { CheckCircle2, XCircle, Database } from "lucide-react";

export default function DataQuality() {
  const { region } = useFilters();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setErr(null);
    getDataQuality(region).then(setData).catch(() => setErr("Could not load data quality."));
  }, [region]);

  useEffect(() => { load(); }, [load]);

  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!data) return <Spinner label="Loading data quality" />;

  return (
    <div className="space-y-4" data-testid="data-quality-page">
      <div>
        <h1 className="text-[18px] font-bold tracking-tight">Source & Data-Quality Readiness</h1>
        <p className="text-[12px] text-muted">The Regional Leakage Brief runs only if readiness rules are met</p>
      </div>

      <Card className={data.briefing_ready ? "border-healthy/40" : "border-breach/40"}>
        <div className="flex items-center gap-3 p-4" data-testid="readiness-banner">
          {data.briefing_ready ? <CheckCircle2 className="text-healthy" size={22} /> : <XCircle className="text-breach" size={22} />}
          <div>
            <p className="text-[13px] font-semibold">{data.briefing_ready ? "Briefing ready" : "Insufficient evidence — briefing will abstain"}</p>
            <p className="text-[11px] text-muted">Identity match rate: <span className="font-semibold text-ink">{pct(data.identity_match_rate)}</span> · {data.readiness_rule}</p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="source-cards">
        {data.sources.map((s) => (
          <Card key={s.key} data-testid={`source-card-${s.key}`}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-line">
              <span className="text-[13px] font-semibold flex items-center gap-1.5"><Database size={14} className="text-muted" />{s.label}</span>
              <StatusChip status={s.status} />
            </div>
            <div className="p-4 grid grid-cols-2 gap-y-2.5 gap-x-3 text-[12px]">
              <div><span className="text-muted block text-[11px]">Records</span><span className="font-semibold tabular">{num(s.records)}</span></div>
              <div><span className="text-muted block text-[11px]">Coverage</span><span className="font-semibold">{s.date_coverage}</span></div>
              <div><span className="text-muted block text-[11px]">Freshness</span><span className="font-semibold">{s.freshness}</span></div>
              <div><span className="text-muted block text-[11px]">Completeness</span><span className="font-semibold tabular">{pct(s.completeness)}</span></div>
              <div><span className="text-muted block text-[11px]">Duplicate rate</span><span className="font-semibold tabular">{pct(s.duplicate_rate)}</span></div>
              <div><span className="text-muted block text-[11px]">Unmatched ID</span><span className="font-semibold tabular">{pct(s.unmatched_identity_rate)}</span></div>
              {s.blocking?.length > 0 && (
                <div className="col-span-2 text-[10.5px] text-watch bg-watch/10 rounded p-1.5">⚠ {s.blocking.join(" · ")}</div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
