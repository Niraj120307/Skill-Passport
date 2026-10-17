import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ShieldHalf, ShieldQuestion, ShieldAlert, type LucideIcon } from "lucide-react";
import type { Severity, Status } from "../lib/api";

export const STATUS_META: Record<Status | "missing", { label: string; cls: string; icon: LucideIcon; hint: string }> = {
  evidence_supported: { label: "Evidence-supported", cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300", icon: ShieldCheck, hint: "Enough independent code evidence across files" },
  partially_supported: { label: "Partially supported", cls: "border-amber-500/40 bg-amber-500/10 text-amber-300", icon: ShieldHalf, hint: "Some evidence, below the supported threshold" },
  unverified: { label: "Unverified claim", cls: "border-slate-500/40 bg-slate-500/10 text-slate-300", icon: ShieldQuestion, hint: "Claimed on resume only — no repository evidence" },
  flagged_for_review: { label: "Flagged for review", cls: "border-rose-500/40 bg-rose-500/10 text-rose-300", icon: ShieldAlert, hint: "Evidence exists, but authorship needs human review" },
  missing: { label: "Missing", cls: "border-ink-600 bg-ink-800 text-ink-400", icon: ShieldQuestion, hint: "No evidence and no claim" },
};

export function StatusBadge({ status }: { status: Status | "missing" }) {
  const m = STATUS_META[status];
  const Icon = m.icon;
  return (
    <span className={`chip ${m.cls}`} title={m.hint}>
      <Icon size={13} /> {m.label}
    </span>
  );
}

export function LevelBadge({ level }: { level: string | null }) {
  if (!level) return <span className="chip border-ink-700 text-ink-400">Level not assessed</span>;
  const dots = { Beginner: 1, Intermediate: 2, Advanced: 3 }[level] ?? 0;
  return (
    <span className="chip border-ink-700 text-ink-100" title="Estimated from evidence breadth and implementation features">
      <span className="flex gap-0.5">
        {[1, 2, 3].map((i) => (
          <span key={i} className={`h-1.5 w-1.5 rounded-full ${i <= dots ? "bg-accent" : "bg-ink-600"}`} />
        ))}
      </span>
      {level}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cls = {
    info: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    low: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
    medium: "border-orange-500/40 bg-orange-500/10 text-orange-300",
    high: "border-rose-500/50 bg-rose-500/15 text-rose-300",
  }[severity];
  return <span className={`chip uppercase tracking-wide ${cls}`}>{severity}</span>;
}

export function StrengthBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "bg-emerald-400" : pct >= 35 ? "bg-amber-400" : "bg-slate-500";
  return (
    <div className="flex items-center gap-2" aria-label={`Evidence strength ${pct}%`}>
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-ink-700">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="mono text-ink-300">{pct}%</span>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-white sm:text-[28px]">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-ink-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} />;
}

export function PageSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <Skeleton className="h-8 w-64" />
      <div className="grid gap-4 sm:grid-cols-3">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

export function EmptyState({ icon: Icon, title, body, action }: { icon: LucideIcon; title: string; body: string; action?: ReactNode }) {
  return (
    <div className="card grid-bg flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-4 rounded-xl border border-ink-700 bg-ink-850 p-3 text-accent">
        <Icon size={26} />
      </div>
      <h2 className="font-display text-lg font-semibold text-white">{title}</h2>
      <p className="mt-1 max-w-md text-sm text-ink-400">{body}</p>
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function NeedPassport() {
  return (
    <EmptyState
      icon={ShieldQuestion}
      title="No passport selected"
      body="Analyze a GitHub repository (and optionally your resume) or load the demo to see this page."
      action={
        <>
          <Link to="/analyze" className="btn-primary">Analyze my work</Link>
          <Link to="/" className="btn-ghost">Go to dashboard</Link>
        </>
      }
    />
  );
}

export function Stat({ label, value, hint, tone = "text-white" }: { label: string; value: ReactNode; hint?: string; tone?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-ink-400">{label}</div>
      <div className={`mt-1 font-display text-3xl font-semibold ${tone}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-400">{hint}</div>}
    </div>
  );
}

export function DemoNotice() {
  return (
    <div className="mb-5 rounded-lg border border-violet-400/40 bg-violet-500/10 px-4 py-2.5 text-sm text-violet-200">
      <strong className="font-semibold">Demo mode:</strong> this passport uses illustrative sample data. Its evidence is not a live verification of any real repository.
    </div>
  );
}
