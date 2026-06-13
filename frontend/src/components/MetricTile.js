import React from "react";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { fmtValue, fmtDelta } from "../lib/format";
import { StateDot, InfoDot } from "./ui";

// metrics where a negative delta is good (lower is better)
const INVERSE = new Set(["cost_per_attended_inr", "median_first_contact_delay_min"]);

export default function MetricTile({ tile }) {
  const { key, label, format, value, delta, state, formula } = tile;
  const inverse = INVERSE.has(key);
  let trend = "flat";
  if (delta !== null && delta !== undefined && delta !== 0) {
    const positive = inverse ? delta < 0 : delta > 0;
    trend = positive ? "up" : "down";
  }
  const trendColor = trend === "up" ? "text-healthy" : trend === "down" ? "text-breach" : "text-muted";
  const TrendIcon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : Minus;

  return (
    <div
      data-testid={`metric-${key}`}
      className="bg-surface border border-line rounded-card shadow-tile p-3 flex flex-col gap-1.5"
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted font-medium flex items-center gap-1">
          <StateDot state={state} /> {label}
        </span>
        {formula && <InfoDot text={`Formula: ${formula}`} />}
      </div>
      <div className="text-[22px] font-bold tracking-tight tabular leading-none" data-testid={`metric-${key}-value`}>
        {fmtValue(format, value)}
      </div>
      <div className="flex items-center gap-1 text-[11px]">
        {delta !== null && delta !== undefined ? (
          <>
            <span className={`inline-flex items-center ${trendColor} font-semibold`}>
              <TrendIcon size={12} /> {fmtDelta(format, delta)}
            </span>
            <span className="text-muted">vs prior</span>
          </>
        ) : (
          <span className="text-muted">No prior comparison</span>
        )}
      </div>
    </div>
  );
}
