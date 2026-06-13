import React from "react";
import { HelpCircle } from "lucide-react";

export const Card = ({ children, className = "", ...rest }) => (
  <div className={`bg-surface border border-line rounded-card shadow-tile ${className}`} {...rest}>
    {children}
  </div>
);

export const CardHeader = ({ title, subtitle, right, testid }) => (
  <div className="flex items-start justify-between px-4 py-3 border-b border-line" data-testid={testid}>
    <div>
      <h3 className="text-[13px] font-semibold text-ink tracking-tight">{title}</h3>
      {subtitle && <p className="text-[11px] text-muted mt-0.5">{subtitle}</p>}
    </div>
    {right}
  </div>
);

export const Tooltip = ({ text, children }) => (
  <span className="tip-wrap">
    {children}
    <span className="tip">{text}</span>
  </span>
);

export const InfoDot = ({ text }) => (
  <Tooltip text={text}>
    <HelpCircle size={13} className="text-muted hover:text-info cursor-help" />
  </Tooltip>
);

const SEV_STYLES = {
  Critical: "bg-breach/10 text-breach border-breach/30",
  High: "bg-watch/10 text-watch border-watch/30",
  Medium: "bg-info/10 text-info border-info/30",
  Low: "bg-muted/10 text-muted border-line",
};

export const SeverityChip = ({ level, score, testid }) => (
  <span
    data-testid={testid}
    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${SEV_STYLES[level] || SEV_STYLES.Low}`}
  >
    <span className="w-1.5 h-1.5 rounded-full bg-current" />
    {level}{score !== undefined ? ` · ${score}` : ""}
  </span>
);

const STATUS_STYLES = {
  Detected: "bg-muted/10 text-muted",
  New: "bg-muted/10 text-muted",
  Reviewed: "bg-info/10 text-info",
  Assigned: "bg-accent/10 text-accent",
  "In Progress": "bg-info/15 text-info",
  "Proof Required": "bg-watch/15 text-watch",
  "Closure Claimed": "bg-accent/15 text-accent",
  Closed: "bg-healthy/10 text-healthy",
  Reopened: "bg-watch/10 text-watch",
  Rejected: "bg-breach/10 text-breach",
  Ready: "bg-healthy/10 text-healthy",
  Partial: "bg-watch/15 text-watch",
  Stale: "bg-watch/10 text-watch",
  Invalid: "bg-breach/10 text-breach",
  Missing: "bg-breach/10 text-breach",
};

export const StatusChip = ({ status, testid }) => (
  <span
    data-testid={testid}
    className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${STATUS_STYLES[status] || "bg-muted/10 text-muted"}`}
  >
    {status}
  </span>
);

const STATE_DOT = { healthy: "bg-healthy", watch: "bg-watch", breach: "bg-breach", neutral: "bg-muted" };
export const StateDot = ({ state }) => (
  <span className={`inline-block w-2 h-2 rounded-full ${STATE_DOT[state] || STATE_DOT.neutral}`} />
);

export const Avatar = ({ name, size = 24 }) => {
  const initials = (name || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-ink text-white font-semibold"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
      title={name}
    >
      {initials}
    </span>
  );
};

export const Button = ({ variant = "primary", className = "", children, ...rest }) => {
  const styles = {
    primary: "bg-ink text-white hover:bg-ink/90",
    accent: "bg-accent text-white hover:bg-accent/90",
    ghost: "bg-transparent text-ink border border-line hover:bg-canvas",
    danger: "bg-surface text-breach border border-breach/30 hover:bg-breach/5",
    info: "bg-info text-white hover:bg-info/90",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
};

export const Spinner = ({ label = "Loading" }) => (
  <div className="flex items-center justify-center gap-2 py-10 text-muted text-[13px]" data-testid="loading-state">
    <span className="w-4 h-4 border-2 border-line border-t-accent rounded-full animate-spin" />
    {label}…
  </div>
);

export const EmptyState = ({ title, hint }) => (
  <div className="text-center py-10 px-4" data-testid="empty-state">
    <p className="text-[13px] font-semibold text-ink">{title}</p>
    {hint && <p className="text-[12px] text-muted mt-1">{hint}</p>}
  </div>
);

export const ErrorState = ({ message, onRetry }) => (
  <div className="text-center py-10 px-4" data-testid="error-state">
    <p className="text-[13px] font-semibold text-breach">Something went wrong</p>
    <p className="text-[12px] text-muted mt-1">{message}</p>
    {onRetry && (
      <Button variant="ghost" className="mt-3" onClick={onRetry}>
        Retry
      </Button>
    )}
  </div>
);
