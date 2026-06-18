import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { getSectors, getSector } from "../lib/api";

// RevOpsOS v1.0 sector layer: one engine, six governance profiles. The selected
// sector is persisted per browser so live sector-switching survives navigation
// (the load-bearing demo moment). See backend/sectors.py + CONTEXT.md glossary.
const SectorContext = createContext(null);
const STORAGE_KEY = "pulse_sector";

export const SectorProvider = ({ children }) => {
  const [sectors, setSectors] = useState(null);
  const [sectorId, setSectorId] = useState(() => localStorage.getItem(STORAGE_KEY) || null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSectors()
      .then((r) => setSectors(r))
      .catch(() => setError("Unable to load sectors. Check backend."));
  }, []);

  const selectSector = useCallback((id) => {
    setSectorId(id);
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  }, []);

  useEffect(() => {
    if (!sectorId) { setData(null); return; }
    let alive = true;
    setLoading(true);
    getSector(sectorId)
      .then((d) => { if (alive) { setData(d); setError(null); } })
      .catch(() => { if (alive) setError("Unable to load sector."); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [sectorId]);

  return (
    <SectorContext.Provider
      value={{ sectors, sectorId, selectSector, data, loading, error,
        attribution: sectors?.attribution || "A product of ArchLife",
        hosting: sectors?.hosting || "pulse-ai.archlife.in" }}
    >
      {children}
    </SectorContext.Provider>
  );
};

export const useSector = () => useContext(SectorContext);
