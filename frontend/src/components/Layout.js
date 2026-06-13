import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, GitBranch, Droplets, SlidersHorizontal,
  Database, ShieldCheck, Activity, Bug, X, ChevronDown, RotateCcw,
} from "lucide-react";
import { useFilters } from "../context/FilterContext";
import { resetSession, SESSION_ID } from "../lib/api";

const NAV = [
  { to: "/cockpit", label: "Cockpit", icon: LayoutDashboard, testid: "nav-cockpit" },
  { to: "/journeys", label: "Journeys", icon: GitBranch, testid: "nav-journeys" },
  { to: "/leakages", label: "Leakages", icon: Droplets, testid: "nav-leakages" },
  { to: "/simulation", label: "Simulation", icon: SlidersHorizontal, testid: "nav-simulation" },
  { to: "/data-quality", label: "Data Quality", icon: Database, testid: "nav-data-quality" },
  { to: "/evaluation", label: "Agent Reliability", icon: ShieldCheck, testid: "nav-evaluation" },
];

const DebugDrawer = ({ open, onClose }) => {
  const { meta } = useFilters();
  const [resetting, setResetting] = useState(false);
  const [done, setDone] = useState(false);
  if (!open) return null;
  const doReset = async () => {
    setResetting(true);
    try { await resetSession(); setDone(true); setTimeout(() => window.location.reload(), 600); }
    finally { setResetting(false); }
  };
  return (
    <div className="fixed inset-0 z-50" data-testid="debug-drawer">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-[300px] bg-surface shadow-drawer slide-in p-4 overflow-y-auto scroll-area">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[13px] font-semibold">Developer Drawer</h3>
          <button onClick={onClose} data-testid="debug-close"><X size={16} /></button>
        </div>
        <dl className="text-[12px] space-y-2">
          {[
            ["Data version", meta?.data_version],
            ["Rule version", meta?.rule_version],
            ["Prompt version", meta?.prompt_version],
            ["Period", meta?.period],
            ["Reference date", meta?.reference_date],
            ["Date range", meta?.date_range?.label],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-line pb-1.5">
              <dt className="text-muted">{k}</dt>
              <dd className="font-mono text-ink">{v || "—"}</dd>
            </div>
          ))}
          <div className="pt-1 text-[11px] text-muted">
            Model: <span className="text-ink font-medium">Claude Sonnet 4.6</span>, deterministic default + validated fallback.
          </div>
          <div className="pt-1 text-[10px] text-muted break-all">
            Demo session: <span className="font-mono text-ink">{SESSION_ID}</span>
          </div>
        </dl>
        <div className="mt-4 pt-3 border-t border-line">
          <p className="text-[11px] text-muted mb-2">Your changes are isolated to your browser session.</p>
          <button onClick={doReset} disabled={resetting} data-testid="reset-demo-btn"
            className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold bg-surface text-breach border border-breach/30 hover:bg-breach/5 disabled:opacity-50">
            <RotateCcw size={13} /> {done ? "Reset! reloading…" : resetting ? "Resetting…" : "Reset my demo"}
          </button>
        </div>
      </div>
    </div>
  );
};

const RegionSelect = () => {
  const { meta, region, setRegion } = useFilters();
  return (
    <div className="relative">
      <select
        data-testid="region-selector"
        value={region}
        onChange={(e) => setRegion(e.target.value)}
        className="appearance-none bg-surface border border-line rounded-md pl-3 pr-8 py-1.5 text-[12px] font-semibold text-ink cursor-pointer hover:border-accent"
      >
        {(meta?.regions || []).map((r) => (
          <option key={r.region_id} value={r.region_id}>{r.name} Region</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
    </div>
  );
};

export default function Layout({ children }) {
  const [debug, setDebug] = useState(false);
  const loc = useLocation();
  return (
    <div className="min-h-screen flex flex-col bg-canvas">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-surface border-b border-line">
        <div className="flex items-center gap-3 px-4 h-14">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-7 h-7 rounded-md bg-accent text-white">
              <Activity size={16} strokeWidth={2.5} />
            </span>
            <div className="leading-tight">
              <div className="text-[14px] font-bold tracking-tight">Pulse AI</div>
              <div className="text-[10px] text-muted -mt-0.5 hidden sm:block">Revenue Operations Intelligence</div>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <span
              data-testid="synthetic-badge"
              className="hidden sm:inline-flex items-center gap-1.5 px-2 py-1 rounded bg-watch/10 text-watch text-[11px] font-semibold border border-watch/20"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-watch" /> Synthetic Demo Data
            </span>
            <span className="hidden md:inline text-[11px] text-muted">Last 30 days</span>
            <RegionSelect />
            <button
              onClick={() => setDebug(true)}
              data-testid="debug-open"
              className="p-1.5 rounded-md border border-line hover:bg-canvas text-muted hover:text-ink"
              title="Developer drawer"
            >
              <Bug size={15} />
            </button>
          </div>
        </div>
        {/* mobile synthetic badge row */}
        <div className="sm:hidden px-4 pb-2">
          <span data-testid="synthetic-badge-mobile" className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-watch/10 text-watch text-[10px] font-semibold border border-watch/20">
            <span className="w-1.5 h-1.5 rounded-full bg-watch" /> Synthetic Demo Data
          </span>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Desktop sidebar */}
        <nav className="hidden lg:flex flex-col w-52 shrink-0 border-r border-line bg-surface py-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={n.testid}
              className={({ isActive }) =>
                `flex items-center gap-2.5 mx-2 px-3 py-2 rounded-md text-[13px] font-medium transition-colors ${
                  isActive ? "bg-ink text-white" : "text-ink/80 hover:bg-canvas"
                }`
              }
            >
              <n.icon size={16} /> {n.label}
            </NavLink>
          ))}
          <div className="mt-auto px-4 pt-4 text-[10px] text-muted leading-relaxed">
            Track 1 · AI Optimization<br />Lead → Attended Appointment
          </div>
        </nav>

        {/* Mobile horizontal nav */}
        <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-line flex overflow-x-auto scroll-area">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-0.5 min-w-[72px] flex-1 py-2 text-[10px] font-medium ${
                  isActive ? "text-accent" : "text-muted"
                }`
              }
            >
              <n.icon size={18} /> {n.label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 min-w-0 overflow-x-hidden pb-20 lg:pb-6">
          <div key={loc.pathname} className="fade-up max-w-[1280px] mx-auto px-4 py-4">
            {children}
          </div>
        </main>
      </div>

      <DebugDrawer open={debug} onClose={() => setDebug(false)} />
    </div>
  );
}
