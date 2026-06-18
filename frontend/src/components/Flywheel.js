import React from "react";

// The flywheel: 5 universal cycle stages around a ring, LTV:CAC band in the
// center. The binding-constraint stage is rendered as the visible drag.
// Sector-blind shape; stage labels + numbers come from the coerced sector data.
const BAND_COLOR = {
  "below baseline": "#C83B3B", // breach
  baseline: "#C47A00",         // watch
  target: "#17845B",           // healthy
  stretch: "#00A6A6",          // accent
};

export default function Flywheel({ headline, stages, onSelectStage, activeStage }) {
  const size = 320;
  const cx = size / 2;
  const cy = size / 2;
  const r = 118;
  const centerColor = BAND_COLOR[headline.band_label] || "#17212B";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label="Flywheel">
        {/* ring */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#D8DEE8" strokeWidth="2" strokeDasharray="4 4" />

        {/* center: headline LTV:CAC + band */}
        <circle cx={cx} cy={cy} r={64} fill="#FFFFFF" stroke={centerColor} strokeWidth="3" />
        <text x={cx} y={cy - 12} textAnchor="middle" fontSize="11" fill="#667085">LTV:CAC</text>
        <text x={cx} y={cy + 12} textAnchor="middle" fontSize="28" fontWeight="700" fill={centerColor}>
          {headline.ltv_cac.toFixed(1)}:1
        </text>
        <text x={cx} y={cy + 30} textAnchor="middle" fontSize="10" fill="#667085">
          {headline.band_label} · band {headline.band[0]}–{headline.band[1]}
        </text>

        {/* 5 stage nodes around the ring */}
        {stages.map((s, i) => {
          const angle = (-90 + (360 / stages.length) * i) * (Math.PI / 180);
          const x = cx + r * Math.cos(angle);
          const y = cy + r * Math.sin(angle);
          const isConstraint = s.is_constraint;
          const fill = isConstraint ? "#C83B3B" : s.in_band ? "#17845B" : "#C47A00";
          const isActive = activeStage === s.id;
          return (
            <g key={s.id} style={{ cursor: onSelectStage ? "pointer" : "default" }}
               onClick={() => onSelectStage && onSelectStage(s.id)}
               data-testid={`flywheel-stage-${s.id}`}>
              <circle cx={x} cy={y} r={isActive ? 30 : 26} fill="#FFFFFF" stroke={fill}
                strokeWidth={isActive ? 4 : 3} />
              <text x={x} y={y - 2} textAnchor="middle" fontSize="13" fontWeight="700" fill={fill}>
                {s.ltv_cac.toFixed(1)}
              </text>
              <text x={x} y={y + 11} textAnchor="middle" fontSize="8" fill="#667085">
                {isConstraint ? "constraint" : ""}
              </text>
              <text x={x} y={y + (y < cy ? -34 : 42)} textAnchor="middle" fontSize="10" fontWeight="600" fill="#17212B">
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="text-[11px] text-muted mt-1">
        5 cycle stages · binding constraint highlighted in red
      </p>
    </div>
  );
}
