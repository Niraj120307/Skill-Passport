import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ExternalLink, GitFork, Info, Users } from "lucide-react";
import { usePassport } from "../lib/store";
import { DemoNotice, NeedPassport, PageHeader, PageSkeleton, SeverityBadge, Stat } from "../components/ui";
import { trustLabel } from "./Dashboard";

const SEV_ORDER = { high: 0, medium: 1, low: 2, info: 3 } as const;

export default function Trust() {
  const { passport, loading } = usePassport();
  if (loading) return <PageSkeleton />;
  if (!passport) return <NeedPassport />;
  const { meta, signals, level } = passport.trust;
  const t = trustLabel(level);
  const sorted = [...signals].sort((a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity]);
  const flags = sorted.filter((s) => s.severity !== "info");
  const infos = sorted.filter((s) => s.severity === "info");
  const owner = passport.repository.owner;
  const timeline = meta.timeline.map((d) => ({ date: d.date.slice(5), Owner: d.owner_commits, Others: d.commits - d.owner_commits }));

  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader title="Trust Analysis" subtitle="Authorship Guard explains what in the repository's history deserves a closer look. It never declares fraud and does not detect AI-generated code." />
      <div className={`card mb-4 flex flex-col gap-1 border-l-4 p-5 ${level === "high_concern" ? "border-l-rose-500" : level === "review_recommended" ? "border-l-orange-400" : level === "minor_signals" ? "border-l-yellow-400" : level === "incomplete" ? "border-l-slate-400" : "border-l-emerald-400"}`}>
        <div className="label">Overall assessment</div>
        <div className={`font-display text-xl font-semibold ${t.cls}`}>{t.text}</div>
        {!meta.assessment_complete && <p className="text-sm text-ink-300">Commit history was not available, so this assessment is incomplete.</p>}
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Fork" value={meta.is_fork ? "Yes" : "No"} hint={meta.parent_full_name ? `of ${meta.parent_full_name}` : undefined} tone={meta.is_fork ? "text-orange-300" : "text-white"} />
        <Stat label="Commits analysed" value={meta.commits_analyzed} hint={meta.history_complete ? "full history" : "recent history only"} />
        <Stat label={`By ${owner}`} value={meta.owner_commits} hint={meta.owner_share != null ? `${Math.round(meta.owner_share * 100)}% of analysed` : "—"} />
        <Stat label="Contributors" value={meta.contributors.length} hint="linked GitHub accounts" />
      </div>

      <section className="card mt-6 p-5">
        <h2 className="mb-1 font-display font-semibold text-white">Commit timeline</h2>
        <p className="mb-4 text-xs text-ink-400">Commits per active day. Tall isolated bars are bursts — common before deadlines, worth a quick look.</p>
        {timeline.length === 0 ? (
          <p className="py-10 text-center text-sm text-ink-400">No commit history available.</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline} margin={{ left: -20, right: 8 }}>
                <CartesianGrid stroke="#232d3a" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#8a97a8", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#334155" }} />
                <YAxis allowDecimals={false} tick={{ fill: "#8a97a8", fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "#131a23", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }} cursor={{ fill: "rgba(62,230,168,0.06)" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Owner" stackId="a" fill="#3ee6a8" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Others" stackId="a" fill="#64748b" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section>
          <h2 className="mb-3 font-display font-semibold text-white">Signals requiring attention ({flags.length})</h2>
          {flags.length === 0 && <p className="card p-5 text-sm text-ink-400">No warning-level signals were found.</p>}
          <div className="space-y-3">
            {flags.map((s) => (
              <article key={s.id} className="card p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={s.severity} />
                  <h3 className="font-medium text-white">{s.title}</h3>
                </div>
                <p className="mt-2 text-sm text-ink-300">{s.description}</p>
                {s.evidence.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {s.evidence.map((e, i) => (
                      <li key={i} className="mono text-ink-300">
                        {e.url ? <a className="inline-flex items-center gap-1 text-accent hover:underline" href={e.url} target="_blank" rel="noreferrer">{e.label} <ExternalLink size={11} /></a> : e.label}
                      </li>
                    ))}
                  </ul>
                )}
                {s.recommendation && <p className="mt-2 text-sm text-ink-100"><span className="text-ink-400">Recommended review: </span>{s.recommendation}</p>}
                {s.limitations && <p className="mt-1 text-xs text-ink-400">Limitation: {s.limitations}</p>}
              </article>
            ))}
          </div>
          {infos.length > 0 && (
            <>
              <h2 className="mb-3 mt-6 font-display font-semibold text-white">Context</h2>
              <ul className="space-y-2">
                {infos.map((s) => (
                  <li key={s.id} className="card p-3.5 text-sm">
                    <div className="flex items-center gap-2"><SeverityBadge severity="info" /><span className="font-medium text-white">{s.title}</span></div>
                    <p className="mt-1 text-ink-300">{s.description}</p>
                    {s.evidence.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-x-3">
                        {s.evidence.map((e, i) => e.url ? <a key={i} className="mono text-accent hover:underline" href={e.url} target="_blank" rel="noreferrer">{e.label}</a> : <span key={i} className="mono text-ink-400">{e.label}</span>)}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
        <aside className="space-y-6">
          {meta.is_fork && meta.parent_url && (
            <a href={meta.parent_url} target="_blank" rel="noreferrer" className="card flex items-center gap-3 p-4 text-sm hover:border-ink-600">
              <GitFork size={18} className="text-orange-300" /> Upstream: <span className="mono text-accent">{meta.parent_full_name}</span>
            </a>
          )}
          <section className="card p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white"><Users size={15} /> Recent commits</h3>
            {meta.recent_commits.length === 0 ? <p className="text-sm text-ink-400">None available.</p> : (
              <ul className="space-y-2">
                {meta.recent_commits.slice(0, 10).map((c) => (
                  <li key={c.sha} className="text-xs">
                    <div className="flex items-center gap-2">
                      {c.url ? <a href={c.url} target="_blank" rel="noreferrer" className="mono text-accent hover:underline">{c.sha.slice(0, 7)}</a> : <span className="mono text-ink-400">{c.sha.slice(0, 7)}</span>}
                      <span className="text-ink-400">{(c.date || "").slice(0, 10)}</span>
                      <span className={c.author_login === owner ? "text-emerald-300" : "text-ink-300"}>{c.author_login ?? c.author_name ?? "unknown"}</span>
                    </div>
                    <div className="truncate text-ink-300">{c.message}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="card p-4 text-xs text-ink-400">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-white"><Info size={15} /> Limitations & human review</h3>
            <ul className="list-disc space-y-1 pl-5">{meta.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
            <p className="mt-3 text-ink-300">Use these signals to guide a short technical conversation — e.g. ask the candidate to walk through a flagged file.</p>
          </section>
        </aside>
      </div>
    </>
  );
}
