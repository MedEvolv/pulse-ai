import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useFilters } from "../context/FilterContext";
import { getCockpit } from "../lib/api";
import { inr, pct, num, titleCase } from "../lib/format";
import MetricTile from "../components/MetricTile";
import Funnel from "../components/Funnel";
import BriefPanel from "../components/BriefPanel";
import { Card, CardHeader, SeverityChip, StatusChip, Avatar, Spinner, ErrorState } from "../components/ui";

const REL_BADGE = {
  shared: { t: "shared pool", cls: "bg-info/10 text-info" },
  allocation: { t: "allocation", cls: "bg-accent/10 text-accent" },
  diagnostic: { t: "diagnostic", cls: "bg-muted/15 text-muted" },
};

const TopLeakageCard = ({ l, owners, onClick }) => {
  const owner = owners.find((o) => o.owner_id === l.owner_id);
  const rel = REL_BADGE[l.opportunity_relationship] || REL_BADGE.diagnostic;
  return (
    <button
      onClick={onClick}
      data-testid={`top-leakage-${l.leakage_id}`}
      className="w-full text-left border border-line rounded-card p-3 hover:border-accent transition-colors bg-surface"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[12.5px] font-semibold text-ink">{titleCase(l.type)}</p>
          <p className="text-[11px] text-muted">{l.region}{l.clinic_code ? ` · ${l.clinic_code}` : ""} · {l.stage_label || l.stage}</p>
        </div>
        <SeverityChip level={l.severity} score={l.severity_score} />
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2.5 text-[11px]">
        <div><span className="text-muted block">Affected</span><span className="font-semibold tabular">{num(l.affected_record_count ?? l.affected_records?.length ?? 0)}</span></div>
        <div><span className="text-muted block">Recoverable</span><span className="font-semibold tabular">{num(l.recoverable_appointments)} appts</span></div>
        <div><span className="text-muted block">Est. value</span><span className="font-semibold tabular">{inr(l.recoverable_value_inr)}</span></div>
      </div>
      <div className="flex items-center gap-1.5 mt-2">
        <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${rel.cls}`} data-testid={`rel-${l.leakage_id}`}>{rel.t}</span>
        <span className="text-[9px] text-muted">not additive across alerts</span>
      </div>
      <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-line">
        <div className="flex items-center gap-1.5">
          {owner ? <><Avatar name={owner.name} size={20} /><span className="text-[11px] text-ink">{owner.name}</span></> : <span className="text-[11px] text-muted">Unassigned</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted">{l.evidence_count} evidence</span>
          <StatusChip status={l.status} />
        </div>
      </div>
    </button>
  );
};

export default function Cockpit() {
  const { region, meta } = useFilters();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setErr(null);
    getCockpit(region)
      .then(setData)
      .catch(() => setErr("Could not load cockpit data."))
      .finally(() => setLoading(false));
  }, [region]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner label="Loading cockpit" />;
  if (err) return <ErrorState message={err} onRetry={load} />;
  if (!data) return null;

  const owners = meta?.owners || [];

  return (
    <div className="space-y-4" data-testid="cockpit-page">
      <div className="flex items-end justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight">{data.region_name} Region · Revenue Cockpit</h1>
          <p className="text-[12px] text-muted">
            Last refreshed {new Date(data.last_refreshed).toLocaleString("en-IN")} · First-touch attribution
          </p>
        </div>
        {data.comparison.find((c) => c.region_id === region)?.at_risk && (
          <span className="risk-pulse inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-breach/10 text-breach text-[12px] font-bold border border-breach/30" data-testid="region-risk-badge">
            ⚠ Region at risk
          </span>
        )}
      </div>

      {/* Health strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5" data-testid="health-strip">
        {data.health_strip.map((t) => <MetricTile key={t.key} tile={t} />)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader title="Revenue Journey Funnel" subtitle="Lead capture → attended · click a stage to inspect the dropped cohort" testid="funnel-header" />
          <Funnel funnel={data.funnel} region={region} />
          {data.funnel_context && (
            <div className="px-4 pb-3 -mt-1" data-testid="funnel-context">
              <div className="text-[10.5px] text-muted bg-canvas border border-line rounded p-2">
                {data.funnel_context.label}: Treatment accepted {num(data.funnel_context.treatment_accepted)} · Revenue {inr(data.funnel_context.revenue_realized_inr)}
              </div>
            </div>
          )}
        </Card>
        <BriefPanel region={region} questions={meta?.supported_questions || []} regionName={data.region_name} />
      </div>

      {/* Opportunity waterfall (CP-01 economic truth) */}
      {data.opportunity_summary && (
        <Card>
          <CardHeader
            title="Recovery Opportunity (non-overlapping)"
            subtitle={`${data.opportunity_summary.unique_opportunity_pools} unique stage pools · ${data.opportunity_summary.related_alerts} related alerts · only unique pools are additive`}
            testid="opportunity-header"
          />
          <div className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5" data-testid="opportunity-summary">
              {data.opportunity_summary.opportunity_groups.map((g) => (
                <div key={g.opportunity_group_id} className="border border-line rounded-card p-3" data-testid={`opp-${g.stage}`}>
                  <span className="text-[11px] text-muted block capitalize">{g.stage} stage</span>
                  <span className="text-[18px] font-bold tabular">{num(g.display_additional_attended)} <span className="text-[11px] font-normal text-muted">appts</span></span>
                  <span className="text-[11px] text-healthy block tabular">{inr(g.value_inr)}</span>
                  <span className="text-[9px] text-muted block mt-1 tabular">{pct(g.current_rate)} → {pct(g.benchmark_rate)} benchmark</span>
                </div>
              ))}
              <div className="border-2 border-accent/40 rounded-card p-3 bg-accent/5" data-testid="opp-total">
                <span className="text-[11px] text-muted block">Total unique opportunity</span>
                <span className="text-[18px] font-bold tabular text-ink">{num(data.opportunity_summary.estimated_attendance_opportunity)} <span className="text-[11px] font-normal text-muted">appts</span></span>
                <span className="text-[12px] text-healthy font-semibold block tabular">{inr(data.opportunity_summary.scenario_value_inr)}</span>
              </div>
            </div>
            <p className="text-[10.5px] text-muted italic mt-2">{data.opportunity_summary.note}</p>
          </div>
        </Card>
      )}

      {/* Top leakage */}
      <Card>
        <CardHeader
          title="Top Leakage"
          subtitle="Ranked by deterministic severity score"
          testid="top-leakage-header"
          right={<button onClick={() => navigate("/leakages")} className="text-[11px] text-info font-semibold">View all →</button>}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2.5 p-4">
          {data.top_leakages.length === 0 && <p className="text-[12px] text-muted">No leakage detected for this region.</p>}
          {data.top_leakages.map((l) => (
            <TopLeakageCard key={l.leakage_id} l={l} owners={owners} onClick={() => navigate(`/leakages/${l.leakage_id}`)} />
          ))}
        </div>
      </Card>

      {/* Regional comparison */}
      <Card>
        <CardHeader title="Regional Comparison" subtitle="North vs West vs South" testid="comparison-header" />
        <div className="overflow-x-auto scroll-area">
          <table className="w-full text-[12px] min-w-[640px]" data-testid="comparison-table">
            <thead>
              <tr className="text-muted text-[11px] border-b border-line">
                {["Region", "Spend", "Leads", "Contact", "Booking", "Show", "Cost/Attended", "High Leaks"].map((h) => (
                  <th key={h} className="text-left font-medium px-4 py-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.comparison.map((c) => (
                <tr key={c.region_id} className={`border-b border-line tabular ${c.region_id === region ? "bg-canvas" : ""}`} data-testid={`comparison-row-${c.region_id}`}>
                  <td className="px-4 py-2 font-semibold flex items-center gap-1.5">
                    {c.region}
                    {c.at_risk && <span className="text-[9px] text-breach font-bold bg-breach/10 px-1 rounded">RISK</span>}
                  </td>
                  <td className="px-4 py-2">{inr(c.spend_inr)}</td>
                  <td className="px-4 py-2">{num(c.leads)}</td>
                  <td className={`px-4 py-2 ${c.contact_rate < 0.65 ? "text-breach font-semibold" : ""}`}>{pct(c.contact_rate)}</td>
                  <td className={`px-4 py-2 ${c.booking_rate < 0.5 ? "text-watch font-semibold" : ""}`}>{pct(c.booking_rate)}</td>
                  <td className={`px-4 py-2 ${c.show_rate < 0.65 ? "text-breach font-semibold" : ""}`}>{pct(c.show_rate)}</td>
                  <td className="px-4 py-2">{inr(c.cost_per_attended_inr)}</td>
                  <td className="px-4 py-2">{c.high_severity_leakages}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
