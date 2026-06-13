import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { FilterProvider } from "./context/FilterContext";
import Layout from "./components/Layout";
import Cockpit from "./pages/Cockpit";
import Journeys from "./pages/Journeys";
import JourneyDetail from "./pages/JourneyDetail";
import Leakages from "./pages/Leakages";
import LeakageDetail from "./pages/LeakageDetail";
import Simulation from "./pages/Simulation";
import DataQuality from "./pages/DataQuality";
import Evaluation from "./pages/Evaluation";

export default function App() {
  return (
    <FilterProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/cockpit" replace />} />
          <Route path="/cockpit" element={<Cockpit />} />
          <Route path="/journeys" element={<Journeys />} />
          <Route path="/journeys/:leadId" element={<JourneyDetail />} />
          <Route path="/leakages" element={<Leakages />} />
          <Route path="/leakages/:leakageId" element={<LeakageDetail />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="*" element={<Navigate to="/cockpit" replace />} />
        </Routes>
      </Layout>
    </FilterProvider>
  );
}
