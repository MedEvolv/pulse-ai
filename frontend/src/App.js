import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { FilterProvider } from "./context/FilterContext";
import { SectorProvider } from "./context/SectorContext";
import Layout from "./components/Layout";
import Init from "./pages/Init";
import FlywheelView from "./pages/FlywheelView";
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
    <SectorProvider>
      <FilterProvider>
        <Routes>
          {/* Init page is the entry point — full screen, no app chrome. */}
          <Route path="/" element={<Navigate to="/init" replace />} />
          <Route path="/init" element={<Init />} />

          {/* Everything else runs inside the app shell. */}
          <Route path="/flywheel" element={<Layout><FlywheelView /></Layout>} />
          <Route path="/cockpit" element={<Layout><Cockpit /></Layout>} />
          <Route path="/journeys" element={<Layout><Journeys /></Layout>} />
          <Route path="/journeys/:leadId" element={<Layout><JourneyDetail /></Layout>} />
          <Route path="/leakages" element={<Layout><Leakages /></Layout>} />
          <Route path="/leakages/:leakageId" element={<Layout><LeakageDetail /></Layout>} />
          <Route path="/simulation" element={<Layout><Simulation /></Layout>} />
          <Route path="/data-quality" element={<Layout><DataQuality /></Layout>} />
          <Route path="/evaluation" element={<Layout><Evaluation /></Layout>} />
          <Route path="*" element={<Navigate to="/init" replace />} />
        </Routes>
      </FilterProvider>
    </SectorProvider>
  );
}
