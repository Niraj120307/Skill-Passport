import { useEffect, useState } from "react";
import { ChevronDown, ExternalLink, FileCode2, FileText, GitCommit, Info, Table2, LayoutGrid } from "lucide-react";
import { api, type EvidenceItem, type Skill, type Status } from "../lib/api";
import { usePassport } from "../lib/store";
import { DemoNotice, LevelBadge, NeedPassport, PageHeader, PageSkeleton, STATUS_META, StatusBadge, StrengthBar } from "../components/ui";

const TYPE_LABEL: Record<string, string> = {
  code_usage: "Code usage", source_file: "Source file", test: "Test", config: "Config", commit_history: "Commit",
  code_import: "Import only", dependency_manifest: "Dependency", documentation: "README", resume_claim: "Resume claim",
};

export function EvidenceRow({ e }: { e: EvidenceItem }) {
  const loc = e.file_path ? `${e.file_path}${e.line_start ? `:${e.line_start}${e.line_end && e.line_end !== e.line_start ? `-${e.line_end}` : ""}` : ""}` : null;
  const Icon = e.source === "resume" ? FileText : e.evidence_type === "commit_history" ? GitCommit : FileCode2;
  return (
    <li className="rounded-lg border border-ink-800 bg-ink-950/60 p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Icon size={14} className="text-ink-400" />
        <span className="chip border-ink-700 text-ink-300">{TYPE_LABEL[e.evidence_type] ?? e.evidence_type}</span>
        {loc && <span className="mono break-all text-ink-100">{loc}</span>}
        {e.source === "resume" && e.page && <span className="text-ink-300">resume page {e.page}</span>}
        {e.commit_sha && <span className="mono text-ink-400">@{e.commit_sha.slice(0, 7)}</span>}
        {e.weight > 0 && <span className="text-ink-400">weight {e.weight}</span>}
        {e.illustrative && <span className="chip border-violet-400/40 text-violet-200">illustrative</span>}
        {e.url && (
          <a href={e.url} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-accent hover:underline">
            {e.evidence_type === "commit_history" ? "Open commit" : "Open on GitHub"} <ExternalLink size={12} />
          </a>
        )}
      </div>
      {e.detail && <div className="mt-1.5 text-xs text-ink-300">{e.detail}</div>}
      {e.snippet && <pre className="mono mt-2 overflow-x-auto whitespace-pre rounded bg-ink-900 px-2.5 py-1.5 text-ink-300">{e.snippet}</pre>}
    </li>
  );
}

function SkillCard({ s }: { s: Skill }) {
  const [open, setOpen] = useState(false);
  const top = s.evidence.find((e) => e.source === "repository" && e.file_path);
  const commitEv = s.evidence.find((e) => e.url);
  return (
    <article className="card flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-white">{s.skill}</h3>
          <div className="text-xs text-ink-400">{s.category}{s.resume_claimed && " · claimed on resume"}</div>
        </div>
        <StatusBadge status={s.verification_status} />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
        <LevelBadge level={s.estimated_level} />
        <StrengthBar value={s.evidence_strength} />
      </div>
      <dl className="mt-4 space-y-1.5 text-xs">
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-ink-400">Top evidence</dt>
          <dd className="mono break-all text-ink-100">
            {top ? `${top.file_path}${top.line_start ? `:${top.line_start}${top.line_end && top.line_end !== top.line_start ? `-${top.line_end}` : ""}` : ""}` : "—"}
          </dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-ink-400">Commit link</dt>
          <dd>
            {commitEv?.url ? (
              <a className="inline-flex items-center gap-1 text-accent hover:underline" href={commitEv.url} target="_blank" rel="noreferrer">
                {commitEv.commit_sha ? commitEv.commit_sha.slice(0, 7) : "view"} <ExternalLink size={11} />
              </a>
            ) : (
              <span className="text-ink-400">not available</span>
            )}
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-sm leading-relaxed text-ink-300">{s.explanation}</p>
      <button className="mt-4 inline-flex items-center gap-1 self-start text-sm text-accent hover:underline" onClick={() => setOpen(!open)} aria-expanded={open}>
        <ChevronDown size={16} className={`transition ${open ? "rotate-180" : ""}`} /> {open ? "Hide" : "Show"} evidence ({s.evidence.length})
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <ul className="space-y-2">{s.evidence.map((e, i) => <EvidenceRow key={e.id ?? i} e={e} />)}</ul>
          <div className="rounded-lg border border-ink-800 p-3 text-xs text-ink-400">
            <div className="mb-1 flex items-center gap-1 font-medium text-ink-300"><Info size={13} /> Limitations</div>
            <ul className="list-disc space-y-0.5 pl-5">{s.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
            <div className="mt-2 mono text-ink-400">
              strong weight {s.metrics.strong_weight} · weak {s.metrics.weak_weight} · {s.metrics.strong_files} strong file(s)
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function EvidenceTable({ id }: { id: string }) {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof api.getEvidence>>["evidence"] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.getEvidence(id).then((r) => setRows(r.evidence)).catch((e) => setErr(e.message));
  }, [id]);
  if (err) return <p className="text-sm text-rose-300">{err}</p>;
  if (!rows) return <div className="skeleton h-64 rounded-xl" />;
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-ink-800 text-xs uppercase tracking-wider text-ink-400">
          <tr>
            <th className="px-4 py-3">Skill</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Location</th>
            <th className="px-4 py-3">Detail</th><th className="px-4 py-3">Link</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-800">
          {rows.map((r, i) => (
            <tr key={i} className="align-top">
              <td className="px-4 py-2.5 text-white">{r.skill}</td>
              <td className="px-4 py-2.5 text-ink-300">{TYPE_LABEL[r.evidence_type] ?? r.evidence_type}</td>
              <td className="mono px-4 py-2.5 text-ink-100">{r.file_path ? `${r.file_path}${r.line_start ? `:${r.line_start}` : ""}` : r.page ? `resume p.${r.page}` : "—"}</td>
              <td className="px-4 py-2.5 text-xs text-ink-300">{r.detail}</td>
              <td className="px-4 py-2.5">{r.url ? <a className="text-accent hover:underline" href={r.url} target="_blank" rel="noreferrer">open</a> : <span className="text-ink-600">—</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PassportPage() {
  const { passport, loading } = usePassport();
  const [filter, setFilter] = useState<Status | "all">("all");
  const [view, setView] = useState<"cards" | "table">("cards");
  if (loading) return <PageSkeleton />;
  if (!passport) return <NeedPassport />;
  const skills = passport.skills.filter((s) => filter === "all" || s.verification_status === filter);
  const counts = passport.skills.reduce<Record<string, number>>((a, s) => ({ ...a, [s.verification_status]: (a[s.verification_status] ?? 0) + 1 }), {});
  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader
        title="Skill Passport"
        subtitle={`${passport.student.name} · ${passport.repository.owner}/${passport.repository.name} · generated ${new Date(passport.created_at).toLocaleString()}`}
        actions={
          <div className="flex rounded-lg border border-ink-700 p-0.5">
            <button className={`btn px-3 py-1.5 ${view === "cards" ? "bg-ink-800 text-white" : "text-ink-400"}`} onClick={() => setView("cards")} aria-pressed={view === "cards"}><LayoutGrid size={15} /> Cards</button>
            <button className={`btn px-3 py-1.5 ${view === "table" ? "bg-ink-800 text-white" : "text-ink-400"}`} onClick={() => setView("table")} aria-pressed={view === "table"}><Table2 size={15} /> All evidence</button>
          </div>
        }
      />
      {view === "table" ? (
        <EvidenceTable id={passport.id} />
      ) : (
        <>
          <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Filter by status">
            {(["all", "evidence_supported", "partially_supported", "flagged_for_review", "unverified"] as const).map((k) => (
              <button
                key={k}
                role="tab"
                aria-selected={filter === k}
                onClick={() => setFilter(k)}
                className={`chip px-3 py-1.5 text-sm ${filter === k ? "border-accent/60 bg-accent/10 text-accent" : "border-ink-700 text-ink-300 hover:text-white"}`}
              >
                {k === "all" ? "All" : STATUS_META[k].label} <span className="text-ink-400">{k === "all" ? passport.skills.length : counts[k] ?? 0}</span>
              </button>
            ))}
          </div>
          {skills.length === 0 ? (
            <p className="card p-8 text-center text-sm text-ink-400">No skills in this category.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">{skills.map((s) => <SkillCard key={s.id} s={s} />)}</div>
          )}
          {passport.repository.scan_notes.length > 0 && (
            <div className="mt-6 rounded-lg border border-ink-800 p-4 text-xs text-ink-400">
              <div className="mb-1 font-medium text-ink-300">Scan notes</div>
              <ul className="list-disc space-y-0.5 pl-5">{passport.repository.scan_notes.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
          )}
        </>
      )}
    </>
  );
}
