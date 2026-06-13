import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getJourney } from "../lib/api";
import { dt, inrFull, mins, titleCase } from "../lib/format";
import { Card, CardHeader, StatusChip, Spinner, ErrorState } from "../components/ui";
import { ArrowLeft, Phone, CalendarCheck, UserPlus, IndianRupee, Circle } from "lucide-react";

const ICONS = { lead_captured: UserPlus, contact_attempt: Phone, appointment: CalendarCheck, revenue: IndianRupee };

export default function JourneyDetail() {
  const { leadId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    getJourney(leadId).then(setData).catch(() => setErr("Lead not found."));
  }, [leadId]);

  if (err) return <ErrorState message={err} onRetry={() => navigate("/journeys")} />;
  if (!data) return <Spinner label="Loading journey" />;

  const { lead, clinic, campaign, timeline } = data;

  return (
    <div className="space-y-4" data-testid="journey-detail-page">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-[12px] text-info font-semibold" data-testid="journey-back">
        <ArrowLeft size={14} /> Back
      </button>

      <Card>
        <CardHeader title={`Lead ${lead.lead_id}`} subtitle={`${campaign?.campaign_name} · ${titleCase(lead.channel)} · ${clinic?.clinic_code} ${clinic?.name}`} />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 text-[12px]">
          <div><span className="text-muted block text-[11px]">Region</span>{lead.region_id}</div>
          <div><span className="text-muted block text-[11px]">Current stage</span>{titleCase(lead.lead_status)}</div>
          <div><span className="text-muted block text-[11px]">1st contact delay</span><span className={lead.first_contact_delay_min > 120 ? "text-breach font-semibold" : ""}>{mins(lead.first_contact_delay_min)}</span></div>
          <div><span className="text-muted block text-[11px]">Appointment</span>{lead.appointment_status ? titleCase(lead.appointment_status) : "—"}</div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Evidence Timeline" subtitle="Every event cites its source system & record ID" />
        <div className="p-4">
          <ol className="relative border-l-2 border-line ml-2" data-testid="journey-timeline">
            {timeline.map((e, i) => {
              const Icon = ICONS[e.type] || Circle;
              return (
                <li key={i} className="mb-4 ml-5" data-testid={`timeline-event-${i}`}>
                  <span className="absolute -left-[11px] flex items-center justify-center w-5 h-5 rounded-full bg-surface border-2 border-accent">
                    <Icon size={11} className="text-accent" />
                  </span>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[12.5px] font-semibold text-ink">{titleCase(e.type)}</span>
                    <StatusChip status={titleCase(e.status)} />
                    <span className="text-[11px] text-muted">{dt(e.at)}</span>
                  </div>
                  <p className="text-[12px] text-ink mt-0.5">{e.detail}</p>
                  <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-[10px] text-muted">
                    <span>source: <span className="font-mono text-ink">{e.source_system}</span></span>
                    <span>record: <span className="font-mono text-ink">{e.source_record_id}</span></span>
                    {e.actor && <span>actor: <span className="text-ink">{e.actor}</span></span>}
                    {e.evidence_id && <span>evidence: <span className="font-mono text-accent">{e.evidence_id}</span></span>}
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="text-[10.5px] text-muted italic mt-2">No raw patient name, phone, email or clinical details are stored or shown.</p>
        </div>
      </Card>
    </div>
  );
}
