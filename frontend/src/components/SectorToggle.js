import React from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { useSector } from "../context/SectorContext";

// Header sector switcher — the live sector-switching surface used in the demo.
// Switching re-coerces the engine into the chosen sector without leaving the view.
export default function SectorToggle() {
  const { sectors, sectorId, selectSector } = useSector();
  const navigate = useNavigate();
  if (!sectors) return null;

  return (
    <div className="relative">
      <select
        data-testid="sector-selector"
        value={sectorId || ""}
        onChange={(e) => { selectSector(e.target.value); navigate("/flywheel"); }}
        className="appearance-none bg-surface border border-line rounded-md pl-3 pr-8 py-1.5 text-[12px] font-semibold text-ink cursor-pointer hover:border-accent"
      >
        {sectors.sectors.map((s) => (
          <option key={s.sector} value={s.sector}>{s.display_name}</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
    </div>
  );
}
