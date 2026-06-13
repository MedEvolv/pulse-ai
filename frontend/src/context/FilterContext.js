import React, { createContext, useContext, useEffect, useState } from "react";
import { getMeta } from "../lib/api";

const FilterContext = createContext(null);

export const FilterProvider = ({ children }) => {
  const [meta, setMeta] = useState(null);
  const [region, setRegion] = useState("REG-NORTH");
  const [error, setError] = useState(null);

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch(() => setError("Unable to load reference data. Check backend."));
  }, []);

  return (
    <FilterContext.Provider value={{ meta, region, setRegion, error }}>
      {children}
    </FilterContext.Provider>
  );
};

export const useFilters = () => useContext(FilterContext);
