import React from "react";
import { useNavigate } from "react-router-dom";
import { num, pct } from "../lib/format";

export default function Funnel({ funnel, region }) {
  const navigate = useNavigate();
  const max = Math.max(...funnel.map((s) => s.count), 1);

  return (
    <div className="px-4 py-3 space-y-2" data-testid="funnel">
      {funnel.map((s, i) => {
        const w = Math.max((s.count / max) * 100, 4);
        const barColor = s.leakage ? "bg-breach/80" : i === 0 ? "bg-ink" : "bg-accent/80";
        return (
          <div key={s.stage} className="group">
            <div className="flex items-center justify-between text-[12px] mb-1">
              <span className="font-medium text-ink flex items-center gap-1.5">
                {s.stage}
                {s.leakage && (
                  <span className="text-[10px] text-breach font-semibold bg-breach/10 px-1.5 py-0.5 rounded">leak</span>
                )}
              </span>
              <span className="tabular text-muted">
                <span className="text-ink font-semibold">{num(s.count)}</span>
                {s.conversion_rate !== null && (
                  <span className="ml-2">{pct(s.conversion_rate)} conv</span>
                )}
              </span>
            </div>
            <span className="tip-wrap" style={{ width: "100%" }}>
              <button
                onClick={() => navigate(`/journeys?region=${region}`)}
                data-testid={`funnel-stage-${i}`}
                className="block w-full text-left"
                aria-label={`${s.stage}: ${s.count} records`}
              >
                <div className="h-7 rounded bg-canvas overflow-hidden border border-line relative">
                  <div
                    className={`h-full ${barColor} transition-all duration-500 flex items-center`}
                    style={{ width: `${w}%` }}
                  />
                  {s.drop > 0 && (
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-breach font-semibold">
                      −{num(s.drop)}
                    </span>
                  )}
                </div>
              </button>
              <span className="tip">{s.drop ? `${num(s.drop)} dropped from previous stage. Click to view affected leads.` : "Top of funnel"}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
