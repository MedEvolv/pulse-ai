import React from "react";
import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight } from "lucide-react";
import { useSector } from "../context/SectorContext";
import { Spinner } from "../components/ui";

// The demo init page: one screen, one selector. The industry-agnostic claim in
// product form — pick a sector, the same engine renders the same flywheel.
const BAND_STYLES = {
  "below baseline": "text-breach",
  baseline: "text-watch",
  target: "text-healthy",
  stretch: "text-accent",
};

export default function Init() {
  const { sectors, selectSector } = useSector();
  const navigate = useNavigate();

  if (!sectors) return <Spinner label="Loading sectors" />;

  const enter = (id) => { selectSector(id); navigate("/flywheel"); };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-canvas px-4 py-10">
      <div className="flex items-center gap-2 mb-1">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-md bg-accent text-white">
          <Activity size={18} strokeWidth={2.5} />
        </span>
        <h1 className="text-[22px] font-bold tracking-tight text-ink">Pulse AI</h1>
      </div>
      <p className="text-[13px] text-muted mb-1">Revenue Operations OS — RevOpsOS</p>
      <p className="text-[12px] text-muted mb-8">Friday mentor pitch · synthetic demo</p>

      <p className="text-[13px] font-semibold text-ink mb-3">Pick a sector</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full max-w-[820px]">
        {sectors.sectors.map((s) => (
          <button
            key={s.sector}
            data-testid={`sector-${s.sector}`}
            onClick={() => enter(s.sector)}
            className="group text-left bg-surface border border-line rounded-card shadow-tile px-4 py-3 hover:border-accent transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-[14px] font-semibold text-ink">{s.display_name}</span>
              {s.is_default && (
                <span className="text-[9px] font-semibold uppercase tracking-wide text-accent bg-accent/10 px-1.5 py-0.5 rounded">Default</span>
              )}
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className={`text-[20px] font-bold tabular-nums ${BAND_STYLES[s.band_label] || "text-ink"}`}>{s.ltv_cac.toFixed(1)}:1</span>
              <span className="text-[10px] text-muted">LTV:CAC · {s.band_label}</span>
            </div>
            <div className="mt-1 flex items-center justify-between">
              <span className="text-[10px] text-muted capitalize">
                {s.depth === "full" ? "Full sector" : "Stub sector"}
              </span>
              <ArrowRight size={14} className="text-muted group-hover:text-accent" />
            </div>
          </button>
        ))}
      </div>

      <p className="text-[12px] text-muted mt-8">Same engine. Same flywheel. Same headline number.</p>
      <p className="text-[11px] text-muted mt-6">{sectors.attribution} · {sectors.hosting}</p>
    </div>
  );
}
