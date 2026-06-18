import React from "react";
import { ShieldCheck, Network, ClipboardCheck, CalendarClock } from "lucide-react";
import { Card, CardHeader } from "./ui";

// The sector governance profile, rendered as the 4 sub-layers. The engine is one;
// this profile is one of six. "To add a 7th sector, write one YAML file."
const Item = ({ children }) => (
  <li className="flex gap-2 text-[12px] text-ink/90 leading-snug">
    <span className="mt-1.5 w-1 h-1 rounded-full bg-accent shrink-0" />
    <span>{children}</span>
  </li>
);

const SubLayer = ({ icon: Icon, title, children }) => (
  <div>
    <div className="flex items-center gap-1.5 mb-1.5">
      <Icon size={14} className="text-accent" />
      <h4 className="text-[12px] font-semibold text-ink">{title}</h4>
    </div>
    <ul className="space-y-1 pl-0.5">{children}</ul>
  </div>
);

export default function SectorGovernancePanel({ governance, depth }) {
  const g = governance || {};
  const protocols = g.protocols?.data_sources || [];
  const policies = g.policies || {};
  const cadences = g.cadences || {};

  return (
    <Card data-testid="governance-panel">
      <CardHeader
        title="Sector Governance Profile"
        subtitle="Rulesets · Protocols · Policies · Cadences — config, not code"
        right={
          <span className="text-[10px] font-semibold uppercase tracking-wide text-muted bg-canvas border border-line px-1.5 py-0.5 rounded">
            {depth === "full" ? "Full depth" : "Stub depth"}
          </span>
        }
      />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 p-4">
        <SubLayer icon={ShieldCheck} title={`Rulesets (${(g.rulesets || []).length})`}>
          {(g.rulesets || []).map((r, i) => <Item key={i}>{r}</Item>)}
        </SubLayer>
        <SubLayer icon={Network} title={`Protocols (${protocols.length} data sources)`}>
          {protocols.map((p, i) => (
            <Item key={i}>{p.name} — {p.cadence} {p.format?.replace("_", " ")}</Item>
          ))}
          {(g.protocols?.forbidden_sources || []).map((f, i) => (
            <Item key={`f${i}`}><span className="text-breach">Forbidden:</span> {f}</Item>
          ))}
        </SubLayer>
        <SubLayer icon={ClipboardCheck} title="Policies">
          {policies.closure_proof && <Item>Closure proof: {policies.closure_proof}</Item>}
          {policies.escalation && <Item>Escalation: {policies.escalation}</Item>}
          {policies.ai_disclosure && <Item>AI disclosure: {policies.ai_disclosure}</Item>}
        </SubLayer>
        <SubLayer icon={CalendarClock} title="Cadences">
          {cadences.recall && <Item>Recall: {cadences.recall}</Item>}
          {cadences.lapse_threshold_days && <Item>Lapse threshold: {cadences.lapse_threshold_days} days</Item>}
          {cadences.reactivation && <Item>Reactivation: {cadences.reactivation}</Item>}
          {cadences.reactivation_owner && <Item>Owner: {cadences.reactivation_owner}</Item>}
        </SubLayer>
      </div>
    </Card>
  );
}
