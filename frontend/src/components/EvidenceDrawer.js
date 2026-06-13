import React, { useEffect } from "react";
import { X, FileText } from "lucide-react";

export default function EvidenceDrawer({ open, onClose, title, evidence = [] }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50" data-testid="evidence-drawer">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full sm:w-[420px] bg-surface shadow-drawer slide-in flex flex-col">
        <div className="flex items-center justify-between px-4 h-14 border-b border-line shrink-0">
          <div>
            <h3 className="text-[13px] font-semibold flex items-center gap-1.5">
              <FileText size={15} className="text-accent" /> Evidence
            </h3>
            <p className="text-[11px] text-muted">{title}</p>
          </div>
          <button onClick={onClose} data-testid="evidence-close" className="p-1.5 rounded hover:bg-canvas">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto scroll-area p-3 space-y-2">
          <p className="text-[11px] text-muted px-1">
            Every material claim is bound to these source records. {evidence.length} item(s).
          </p>
          {evidence.length === 0 && (
            <p className="text-[12px] text-muted px-1 py-4">No evidence references attached.</p>
          )}
          {evidence.map((e) => (
            <div key={e.evidence_id} className="border border-line rounded-card p-3" data-testid={`evidence-${e.evidence_id}`}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] font-semibold text-accent">{e.evidence_id}</span>
                <span className="text-[10px] text-muted bg-canvas px-1.5 py-0.5 rounded">{e.source_system}</span>
              </div>
              <p className="text-[12px] text-ink mt-1.5">{e.summary}</p>
              <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-[10px] text-muted">
                <span>src: <span className="font-mono text-ink">{e.source_record_id}</span></span>
                {e.clinic_code && <span>clinic: <span className="font-mono text-ink">{e.clinic_code}</span></span>}
                {e.lead_id && <span>lead: <span className="font-mono text-ink">{e.lead_id}</span></span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
