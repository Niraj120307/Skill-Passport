import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckSquare, FolderGit2, Lightbulb, ListOrdered, Map, Target } from "lucide-react";
import { api, type Roadmap } from "../lib/api";
import { usePassport } from "../lib/store";
import { DemoNotice, EmptyState, NeedPassport, PageHeader, PageSkeleton, Skeleton, StatusBadge } from "../components/ui";

export default function RoadmapPage() {
  const { passport, loading } = usePassport();
  const [data, setData] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!passport) return;
    setData(null);
    setError(null);
    api.roadmap(passport.id).then(setData).catch((e) => setError(e.message));
  }, [passport?.id, passport?.latest_job_match?.id]);

  if (loading) return <PageSkeleton />;
  if (!passport) return <NeedPassport />;
  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader
        title="Learning Roadmap"
        subtitle={data?.based_on === "job_match" ? `Built from your gaps for “${data.job_title}”.` : "Built from skills that are not yet evidence-supported. Match a job for a targeted plan."}
        actions={<Link to="/job-match" className="btn-ghost"><Target size={16} /> {data?.based_on === "job_match" ? "Change job" : "Match a job"}</Link>}
      />
      {error && <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
      {!data && !error && <div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-72" /><Skeleton className="h-72" /></div>}
      {data && data.items.length === 0 && (
        <EmptyState icon={Map} title="No gaps to close" body="Every requested skill is evidence-supported. Try a more demanding job description." />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.items.map((r) => (
          <article key={r.skill_id} className="card flex flex-col p-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="font-display text-lg font-semibold text-white">{r.skill}</h3>
                <p className="text-xs text-ink-400">{r.gap_reason}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <StatusBadge status={r.current_status as never} />
                <span className={`chip ${r.priority === "high" ? "border-rose-500/40 text-rose-300" : "border-ink-700 text-ink-300"}`}>{r.priority} priority</span>
              </div>
            </div>
            <p className="mt-3 flex gap-2 text-sm text-ink-300"><Lightbulb size={16} className="mt-0.5 shrink-0 text-amber-300" /> {r.why_it_matters}</p>
            <div className="mt-4">
              <div className="label flex items-center gap-1.5"><ListOrdered size={13} /> Learning steps</div>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-ink-100">{r.steps.map((s) => <li key={s}>{s}</li>)}</ol>
            </div>
            <div className="mt-4 rounded-lg border border-accent/30 bg-accent/5 p-3">
              <div className="label flex items-center gap-1.5 text-accent"><FolderGit2 size={13} /> Mini-project</div>
              <p className="text-sm text-white">{r.mini_project}</p>
            </div>
            <div className="mt-4">
              <div className="label flex items-center gap-1.5"><CheckSquare size={13} /> Acceptance criteria</div>
              <ul className="space-y-1 text-sm text-ink-300">{r.acceptance_criteria.map((a) => <li key={a} className="flex gap-2"><span className="text-accent">✓</span>{a}</li>)}</ul>
            </div>
            <p className="mt-4 border-t border-ink-800 pt-3 text-xs text-ink-400"><span className="font-medium text-ink-300">Evidence needed: </span>{r.evidence_needed}</p>
          </article>
        ))}
      </div>
    </>
  );
}
