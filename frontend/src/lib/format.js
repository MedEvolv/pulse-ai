export const inr = (v) => {
  if (v === null || v === undefined) return "N/A";
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(2)}Cr`;
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return `₹${Math.round(v).toLocaleString("en-IN")}`;
};

export const inrFull = (v) =>
  v === null || v === undefined ? "N/A" : `₹${Math.round(v).toLocaleString("en-IN")}`;

export const pct = (v) => (v === null || v === undefined ? "N/A" : `${(v * 100).toFixed(1)}%`);

export const num = (v) => (v === null || v === undefined ? "N/A" : Number(v).toLocaleString("en-IN"));

export const mins = (v) => {
  if (v === null || v === undefined) return "N/A";
  if (v >= 60) return `${(v / 60).toFixed(1)}h`;
  return `${Math.round(v)}m`;
};

export const fmtValue = (format, v) => {
  switch (format) {
    case "inr": return inr(v);
    case "percent": return pct(v);
    case "number": return num(v);
    case "minutes": return mins(v);
    default: return num(v);
  }
};

export const fmtDelta = (format, delta) => {
  if (delta === null || delta === undefined) return null;
  if (format === "percent") return `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}pp`;
  if (format === "inr") return `${delta >= 0 ? "+" : ""}${inr(Math.abs(delta) * (delta < 0 ? -1 : 1)).replace("₹", "₹")}`;
  return `${delta >= 0 ? "+" : ""}${num(delta)}`;
};

export const titleCase = (s) =>
  (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const dt = (s) => {
  if (!s) return "";
  try {
    return new Date(s).toLocaleString("en-IN", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch { return s; }
};
