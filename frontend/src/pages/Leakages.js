import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useFilters } from "../context/FilterContext";
import { getLeakages } from "../lib/api";
import { inr, num, titleCase } from "../lib/format";
import { Card, CardHeader, SeverityChip, StatusChip, Avatar, Spinner, EmptyState, ErrorState } from "../components/ui";

export default function Leakages() {
  const { region, meta } = useFilters();
  const navigate = useNavigate();
  const [allRegions, setAllRegions] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setLoading(true); setErr(null);
    getLeakages(allRegions ? undefined : region)
      .then((d) => setData(d.leakages))
      .catch(() => setErr("Could not load leakages."))
      .finally(() => setLoading(false));
  }, [region, allRegions]);

  useEffect(() => { load(); }, [load]);

  const owners = meta?.owners || [];

  return (
    <div className="space-y-4" data-testid="leakages-page">
      <div className="flex items-end justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight">Leakage & Intervention Queue</h1>
          <p className="text-[12px] text-muted">Ranked by severity · all actions are demo-local · <span className="text-breach font-medium">No external system writeback</span></p>
        </div>
        <label className="flex items-center gap-1.5 text-[12px] text-ink cursor-pointer" data-testid="all-regions-toggle">
          <input type="checkbox" checked={allRegions} onChange={(e) => setAllRegions(e.target.checked)} />
          All regions
        </label>
      </div>

      <Card>
        <CardHeader title={allRegions ? "All Regions" : `${meta?.regions?.find((r) => r.region_id === region)?.name} Region`} subtitle="Click a row for evidence, formula & actions" />
        {loading ? <Spinner label="Loading leakages" /> : err ? <ErrorState message={err} onRetry={load} /> :
          data.length === 0 ? <EmptyState title="No leakage detected" hint="This region is performing within thresholds." /> : (
            <div className="overflow-x-auto scroll-area">
              <table className="w-full text-[12px] min-w-[920px]" data-testid="leakages-table">
                <thead>
                  <tr className="text-muted text-[11px] border-b border-line">
                    {["Leakage", "Severity", "Region", "Clinic/Scope", "Stage", "Affected", "Recoverable", "Est. Value", "Owner", "Status", "Evidence"].map((h) =>
                      <th key={h} className="text-left font-medium px-3 py-2 whitespace-nowrap">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {data.map((l) => {
                    const owner = owners.find((o) => o.owner_id === l.owner_id);
                    return (
                      <tr key={l.leakage_id} onClick={() => navigate(`/leakages/${l.leakage_id}`)}
                        className="border-b border-line hover:bg-canvas cursor-pointer tabular" data-testid={`leakage-row-${l.leakage_id}`}>
                        <td className="px-3 py-2 font-semibold text-ink whitespace-nowrap">{titleCase(l.type)}</td>
                        <td className="px-3 py-2"><SeverityChip level={l.severity} score={l.severity_score} /></td>
                        <td className="px-3 py-2">{l.region}</td>
                        <td className="px-3 py-2 font-mono text-[11px]">{l.clinic_code || "Region-wide"}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{l.stage}</td>
                        <td className="px-3 py-2">{num(l.affected_record_count ?? l.affected_records?.length ?? 0)}</td>
                        <td className="px-3 py-2">{num(l.recoverable_appointments)} appts</td>
                        <td className="px-3 py-2 font-semibold">{inr(l.recoverable_value_inr)}</td>
                        <td className="px-3 py-2">
                          {owner ? <span className="inline-flex items-center gap-1.5"><Avatar name={owner.name} size={18} /><span className="text-[11px]">{owner.name.split(" ")[0]}</span></span> : <span className="text-muted text-[11px]">—</span>}
                        </td>
                        <td className="px-3 py-2"><StatusChip status={l.status} /></td>
                        <td className="px-3 py-2 text-muted">{l.evidence_count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
      </Card>
    </div>
  );
}
