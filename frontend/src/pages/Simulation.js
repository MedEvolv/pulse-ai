import React, { useEffect, useState, useCallback } from "react";
import { useFilters } from "../context/FilterContext";
import { postSimulation } from "../lib/api";
import { inr, inrFull, num, pct } from "../lib/format";
import { Card, CardHeader, Spinner, Tooltip } from "../components/ui";
import { TrendingUp } from "lucide-react";

const Slider = ({ label, value, onChange, testid }) => (
  <div data-testid={testid}>
    <div className="flex justify-between text-[12px] mb-1">
      <span className="text-ink font-medium">{label}</span>
      <span className="tabular font-semibold text-accent">+{value}pp</span>
    </div>
    <input type="range" min="0" max="15" step="1" value={value} onChange={(e) => onChange(Number(e.target.value))}
      className="w-full accent-[#00A6A6]" />
  </div>
);

const Out = ({ label, value, sub, accent }) => (
  <div className="bg-surface border border-line rounded-card p-3">
    <span className="text-[11px] text-muted block">{label}</span>
    <span className={`text-[20px] font-bold tabular ${accent || "text-ink"}`}>{value}</span>
    {sub && <span className="text-[10px] text-muted block">{sub}</span>}
  </div>
);

export default function Simulation() {
  const { region, meta } = useFilters();
  const [c, setC] = useState(10);
  const [b, setB] = useState(0);
  const [s, setS] = useState(10);
  const [val, setVal] = useState(17500);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(() => {
    setLoading(true);
    postSimulation({ region, contact_improve_pp: c, booking_improve_pp: b, show_improve_pp: s, avg_realized_value: val })
      .then(setRes).finally(() => setLoading(false));
  }, [region, c, b, s, val]);

  useEffect(() => { const t = setTimeout(run, 150); return () => clearTimeout(t); }, [run]);

  const regionName = meta?.regions?.find((r) => r.region_id === region)?.name;

  return (
    <div className="space-y-4" data-testid="simulation-page">
      <div>
        <h1 className="text-[18px] font-bold tracking-tight">Scenario Simulator · {regionName} Region</h1>
        <p className="text-[12px] text-muted">Deterministic cohort arithmetic — <span className="font-medium">not a forecast</span></p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader title="Improvement Levers" subtitle="0–15 percentage points each" />
          <div className="p-4 space-y-4">
            <Slider label="Contact rate improvement" value={c} onChange={setC} testid="slider-contact" />
            <Slider label="Booking rate improvement" value={b} onChange={setB} testid="slider-booking" />
            <Slider label="Show rate improvement" value={s} onChange={setS} testid="slider-show" />
            <div>
              <label className="text-[12px] text-ink font-medium block mb-1">Avg realized value / attended (₹)</label>
              <input type="number" value={val} onChange={(e) => setVal(Number(e.target.value))} data-testid="avg-value-input"
                className="w-full bg-canvas border border-line rounded-md px-2 py-1.5 text-[12px] outline-none focus:border-accent tabular" />
            </div>
            <button onClick={() => { setC(0); setB(0); setS(0); }} data-testid="reset-sim" className="text-[11px] text-info font-semibold">Reset levers</button>
          </div>
        </Card>

        <Card>
          <CardHeader title="Scenario Estimate" subtitle="Based on current cohort and explicit assumptions" right={<TrendingUp size={16} className="text-accent" />} />
          <div className="p-4">
            {loading && !res ? <Spinner label="Computing" /> : res && (
              <div className="space-y-3" data-testid="sim-output">
                <div className="grid grid-cols-2 gap-2.5">
                  <Out label="Additional contacted" value={`+${num(res.simulated.additional_contacted)}`} accent="text-info" />
                  <Out label="Additional booked" value={`+${num(res.simulated.additional_booked)}`} accent="text-info" />
                  <Out label="Additional attended" value={`+${num(res.simulated.additional_attended)}`} accent="text-healthy"
                    sub={`raw ${res.simulated.additional_attended_raw}`} />
                  <Out label="Est. recoverable value" value={inr(res.simulated.estimated_recoverable_value_inr)} accent="text-healthy"
                    sub={inrFull(res.simulated.estimated_recoverable_value_inr)} />
                </div>
                <div className="grid grid-cols-3 gap-2.5 pt-2 border-t border-line text-[12px]">
                  <div><span className="text-muted block text-[11px]">Baseline CPA</span><span className="tabular font-semibold">{inr(res.baseline.cost_per_attended_inr)}</span></div>
                  <div><span className="text-muted block text-[11px]">Scenario CPA</span><span className="tabular font-semibold text-healthy">{inr(res.simulated.cost_per_attended_inr)}</span></div>
                  <div><span className="text-muted block text-[11px]">Show rate</span><span className="tabular font-semibold">{pct(res.baseline.show_rate)} → {pct(res.simulated.show_rate)}</span></div>
                </div>
                <ul className="text-[10.5px] text-muted space-y-0.5 pt-2 border-t border-line">
                  {res.assumptions.map((a, i) => <li key={i}>• {a}</li>)}
                </ul>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
