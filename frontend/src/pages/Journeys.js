import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useFilters } from "../context/FilterContext";
import { getJourneys } from "../lib/api";
import { dt, mins, titleCase } from "../lib/format";
import { Card, CardHeader, StatusChip, Spinner, EmptyState, ErrorState } from "../components/ui";

const STAGES = ["captured", "contacted", "appointment_booked", "attended", "treatment_accepted"];
const APPT = ["attended", "no_show", "cancelled"];
const FLAGS = ["uncontacted_24h", "slow_first_contact", "contact_to_booking_drop", "high_no_show_rate"];

const Select = ({ value, onChange, options, label, testid }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
    className="bg-surface border border-line rounded-md px-2 py-1.5 text-[11px] text-ink hover:border-accent outline-none">
    <option value="">{label}</option>
    {options.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
  </select>
);

export default function Journeys() {
  const { region, meta } = useFilters();
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const initF = {
    clinic: sp.get("clinic") || "", channel: sp.get("channel") || "",
    campaign: sp.get("campaign") || "", stage: sp.get("stage") || "",
    appointment_status: sp.get("appointment_status") || "",
    leakage_flag: sp.get("leakage_flag") || "", funnel_stage: sp.get("funnel_stage") || "",
  };
  const [f, setF] = useState(initF);

  // hydrate when URL changes (e.g. arriving from a funnel/leakage drilldown)
  useEffect(() => {
    setF({
      clinic: sp.get("clinic") || "", channel: sp.get("channel") || "",
      campaign: sp.get("campaign") || "", stage: sp.get("stage") || "",
      appointment_status: sp.get("appointment_status") || "",
      leakage_flag: sp.get("leakage_flag") || "", funnel_stage: sp.get("funnel_stage") || "",
    });
  }, [sp.toString()]);

  const setFilter = (patch) => {
    const next = { ...f, ...patch };
    setF(next);
    const params = {};
    if (region) params.region = region;
    Object.entries(next).forEach(([k, v]) => { if (v) params[k] = v; });
    setSp(params, { replace: true });
  };

  const load = useCallback(() => {
    setLoading(true); setErr(null);
    getJourneys({ region, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) })
      .then((d) => setRows(d.journeys))
      .catch(() => setErr("Could not load journeys."))
      .finally(() => setLoading(false));
  }, [region, f]);

  useEffect(() => { load(); }, [load]);

  const clinics = (meta?.clinics || []).filter((c) => c.region_id === region);
  const clearAll = () => { setF({ clinic: "", channel: "", campaign: "", stage: "", appointment_status: "", leakage_flag: "", funnel_stage: "" }); setSp(region ? { region } : {}, { replace: true }); };

  return (
    <div className="space-y-4" data-testid="journeys-page">
      <div>
        <h1 className="text-[18px] font-bold tracking-tight">Lead Journey Explorer</h1>
        <p className="text-[12px] text-muted">Pseudonymous leads · no patient name, phone, email or clinical data</p>
      </div>

      <Card>
        <div className="flex flex-wrap gap-2 p-3 border-b border-line" data-testid="journey-filters">
          <Select value={f.clinic} onChange={(v) => setFilter({ clinic: v })} label="All clinics" testid="filter-clinic"
            options={clinics.map((c) => ({ v: c.clinic_code, t: `${c.clinic_code} ${c.name}` }))} />
          <Select value={f.channel} onChange={(v) => setFilter({ channel: v })} label="All channels" testid="filter-channel"
            options={[{ v: "google", t: "Google" }, { v: "meta", t: "Meta" }]} />
          <Select value={f.stage} onChange={(v) => setFilter({ stage: v })} label="All stages" testid="filter-stage"
            options={STAGES.map((s) => ({ v: s, t: titleCase(s) }))} />
          <Select value={f.appointment_status} onChange={(v) => setFilter({ appointment_status: v })} label="Any appt status" testid="filter-appt"
            options={APPT.map((s) => ({ v: s, t: titleCase(s) }))} />
          <Select value={f.leakage_flag} onChange={(v) => setFilter({ leakage_flag: v })} label="Any leakage flag" testid="filter-flag"
            options={FLAGS.map((s) => ({ v: s, t: titleCase(s) }))} />
          {f.funnel_stage && (
            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-accent/10 text-accent" data-testid="funnel-stage-chip">
              Funnel drop: {titleCase(f.funnel_stage)}
              <button onClick={() => setFilter({ funnel_stage: "" })} className="font-bold">×</button>
            </span>
          )}
          {Object.values(f).some(Boolean) && (
            <button onClick={clearAll} className="text-[11px] text-info font-semibold px-2" data-testid="clear-filters">Clear</button>
          )}
          <span className="ml-auto text-[11px] text-muted self-center">{rows?.length ?? 0} leads</span>
        </div>

        {loading ? <Spinner label="Loading journeys" /> : err ? <ErrorState message={err} onRetry={load} /> :
          rows.length === 0 ? <EmptyState title="No leads match these filters" hint="Adjust or clear the filters above." /> : (
            <div className="overflow-x-auto scroll-area max-h-[60vh]">
              <table className="w-full text-[12px] min-w-[860px]" data-testid="journeys-table">
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-muted text-[11px] border-b border-line">
                    {["Lead", "Campaign", "Channel", "Clinic", "Created", "1st Contact", "Connected", "Appt Status", "Stage", "Leakage Flags"].map((h) =>
                      <th key={h} className="text-left font-medium px-3 py-2 whitespace-nowrap">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.lead_id} onClick={() => navigate(`/journeys/${r.lead_id}`)}
                      className="border-b border-line hover:bg-canvas cursor-pointer tabular" data-testid={`journey-row-${r.lead_id}`}>
                      <td className="px-3 py-2 font-mono text-accent font-semibold">{r.lead_id}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{r.campaign_id}</td>
                      <td className="px-3 py-2">{titleCase(r.channel)}</td>
                      <td className="px-3 py-2 font-mono">{r.clinic_code}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{dt(r.created_at)}</td>
                      <td className={`px-3 py-2 ${r.first_contact_delay_min > 120 ? "text-breach font-semibold" : ""}`}>{mins(r.first_contact_delay_min)}</td>
                      <td className="px-3 py-2">{r.connected ? "Yes" : <span className="text-breach">No</span>}</td>
                      <td className="px-3 py-2">{r.appointment_status ? <StatusChip status={titleCase(r.appointment_status)} /> : <span className="text-muted">—</span>}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{titleCase(r.lead_status)}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {r.leakage_flags.length ? r.leakage_flags.map((fl) =>
                            <span key={fl} className="text-[9px] bg-breach/10 text-breach px-1 py-0.5 rounded">{titleCase(fl)}</span>)
                            : <span className="text-muted text-[10px]">—</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>
    </div>
  );
}
