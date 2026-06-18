import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useSector } from "../context/SectorContext";
import { Card, CardHeader, Spinner, ErrorState } from "../components/ui";
import Flywheel from "../components/Flywheel";
import SectorGovernancePanel from "../components/SectorGovernancePanel";

// The sector cockpit: the same flywheel + LTV:CAC + per-cohort/per-location/per-stage
// drill + governance, rendered for whichever sector is selected. Sector-blind shape.
const bandTone = (inBand, isConstraint) =>
  isConstraint ? "text-breach" : inBand ? "text-healthy" : "text-watch";

const DrillTable = ({ title, rows, nameKey, subKey, subLabel }) => (
  <Card>
    <CardHeader title={title} subtitle={`Per-${title.toLowerCase().split(" ")[1] || "row"} LTV:CAC`} />
    <table className="w-full text-[12px]">
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-line last:border-0">
            <td className="px-4 py-2 text-ink/90">{r[nameKey]}</td>
            {subKey && <td className="px-4 py-2 text-muted text-right tabular-nums">{r[subKey]} {subLabel}</td>}
            <td className="px-4 py-2 text-right font-semibold tabular-nums text-ink">{r.ltv_cac.toFixed(1)}:1</td>
          </tr>
        ))}
      </tbody>
    </table>
  </Card>
);

export default function FlywheelView() {
  const { sectorId, data, loading, error } = useSector();
  const [activeStage, setActiveStage] = useState(null);

  if (!sectorId) return <Navigate to="/init" replace />;
  if (loading || !data) return <Spinner label="Coercing sector" />;
  if (error) return <ErrorState message={error} />;

  const { headline, stages, cohorts, locations, labels, display_name, depth, reference } = data;
  const active = stages.find((s) => s.id === activeStage);

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-[18px] font-bold text-ink">{display_name} <span className="text-muted font-normal text-[13px]">· {labels.location}s, {labels.customer}s</span></h2>
          <p className="text-[12px] text-muted">{reference}</p>
        </div>
        <span className="text-[11px] text-muted">
          Binding constraint: <span className="text-breach font-semibold">{headline.binding_constraint_label}</span>
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="flex items-center justify-center py-5">
          <Flywheel headline={headline} stages={stages} onSelectStage={setActiveStage} activeStage={activeStage} />
        </Card>

        <Card>
          <CardHeader title="Cycle stages" subtitle="Per-stage LTV:CAC · click a node to focus" />
          <table className="w-full text-[12px]">
            <tbody>
              {stages.map((s) => (
                <tr key={s.id}
                  className={`border-b border-line last:border-0 cursor-pointer hover:bg-canvas ${activeStage === s.id ? "bg-canvas" : ""}`}
                  onClick={() => setActiveStage(s.id)} data-testid={`stage-row-${s.id}`}>
                  <td className="px-4 py-2 text-ink/90">{s.label}</td>
                  <td className="px-4 py-2 text-right">
                    {s.is_constraint && <span className="text-[10px] text-breach font-semibold mr-2">constraint</span>}
                    <span className={`font-semibold tabular-nums ${bandTone(s.in_band, s.is_constraint)}`}>{s.ltv_cac.toFixed(1)}:1</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {active && (
            <div className="px-4 py-2.5 border-t border-line bg-canvas text-[12px]" data-testid="stage-detail">
              <span className="font-semibold text-ink">{active.label}</span>{" "}
              <span className={bandTone(active.in_band, active.is_constraint)}>{active.ltv_cac.toFixed(1)}:1</span>{" "}
              <span className="text-muted">
                — {active.is_constraint
                  ? "this is the binding constraint: the single stage that, improved, moves the headline most."
                  : active.in_band ? "in band, healthy." : "below band, watch."}
              </span>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DrillTable title={`${labels.cohort || "Cohort"}s`} rows={cohorts} nameKey="name" subKey="customers" subLabel={labels.customer?.toLowerCase() + "s"} />
        <DrillTable title={`${labels.location || "Location"}s`} rows={locations} nameKey="name" />
      </div>

      <SectorGovernancePanel governance={data.governance} depth={depth} />
    </div>
  );
}
