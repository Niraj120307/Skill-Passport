import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BadgeCheck, FileText, Github, PlayCircle, ScanSearch, ShieldHalf, Target, RefreshCw } from "lucide-react";
import { api, type PassportListItem } from "../lib/api";
import { usePassport } from "../lib/store";
import { useToast } from "../components/Toast";
import { DemoNotice, EmptyState, PageHeader, PageSkeleton, Stat, StatusBadge } from "../components/ui";

const TRUST_LABEL: Record<string, { text: string; cls: string }> = {
  no_major_concerns: { text: "No major concerns", cls: "text-emerald-300" },
  review_recommended: { text: "Review recommended", cls: "text-orange-300" },
  minor_signals: { text: "Minor signals to review", cls: "text-yellow-300" },
  high_concern: { text: "High concern — human review", cls: "text-rose-300" },
  incomplete: { text: "Assessment incomplete", cls: "text-slate-300" },
};
export const trustLabel = (l: string) => TRUST_LABEL[l] ?? { text: l, cls: "text-ink-300" };

export default function Dashboard() {
  const { passport, loading, setPassport, selectPassport, error } = usePassport();
  const [recent, setRecent] = useState<PassportListItem[] | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const toast = useToast();
  const nav = useNavigate();

  const loadRecent = () => api.listPassports().then(setRecent).catch(() => setRecent([]));
  useEffect(() => {
    void loadRecent();
  }, [passport?.id]);

  const loadDemo = async () => {
    setDemoLoading(true);
    try {
      const p = await api.loadDemo();
      setPassport(p);
      toast("success", "Demo passport loaded (illustrative data).");
      nav("/passport");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Could not load demo");
    } finally {
      setDemoLoading(false);
    }
  };

  if (loading) return <PageSkeleton />;

  const recentList = recent && recent.length > 0 && (
    <section className="card mt-6 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display font-semibold text-white">Saved analyses</h2>
        <button className="btn-ghost px-2.5 py-1.5 text-xs" onClick={() => void loadRecent()}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>
      <ul className="divide-y divide-ink-800">
        {recent.map((r) => (
          <li key={r.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-medium text-white">
                {r.student_name}
                {r.is_demo && <span className="chip border-violet-400/40 text-violet-200">DEMO</span>}
                {passport?.id === r.id && <span className="chip border-accent/40 text-accent">current</span>}
              </div>
              <div className="mono truncate text-ink-400">{r.repository.replace("https://github.com/", "")}</div>
              <div className="text-xs text-ink-400">
                {new Date(r.created_at).toLocaleString()} · {r.summary.evidence_supported}/{r.summary.total_skills} supported ·{" "}
                <span className={trustLabel(r.trust_level).cls}>{trustLabel(r.trust_level).text}</span>
              </div>
            </div>
            {passport?.id !== r.id && (
              <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => void selectPassport(r.id).then(() => toast("info", "Switched passport."))}>
                Open
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );

  if (!passport) {
    return (
      <>
        <PageHeader title="Dashboard" subtitle="Turn real code into a verified, explainable skill profile." />
        {error && <p className="mb-4 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}
        <EmptyState
          icon={BadgeCheck}
          title="No Skill Passport yet"
          body="Connect a public GitHub repository and upload your resume. Every skill is linked to the file, line and commit that supports it."
          action={
            <>
              <Link to="/analyze" className="btn-primary"><ScanSearch size={16} /> Analyze my work</Link>
              <button className="btn-ghost" onClick={loadDemo} disabled={demoLoading}>
                <PlayCircle size={16} /> {demoLoading ? "Loading demo…" : "Load demo (sample data)"}
              </button>
            </>
          }
        />
        {recentList}
      </>
    );
  }

  const s = passport.summary;
  const t = trustLabel(passport.trust.level);
  const review = passport.skills.filter((k) => k.verification_status === "flagged_for_review" || k.verification_status === "unverified");
  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader
        title={`Hi, ${passport.student.name.split(" ")[0]}`}
        subtitle="Your latest analysis, persisted on the backend."
        actions={
          <>
            <Link to="/analyze" className="btn-ghost"><ScanSearch size={16} /> New analysis</Link>
            {!passport.is_demo && (
              <button className="btn-ghost" onClick={loadDemo} disabled={demoLoading}>
                <PlayCircle size={16} /> {demoLoading ? "Loading…" : "Demo"}
              </button>
            )}
          </>
        }
      />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-5 md:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <div className="label">Student</div>
              <div className="text-lg font-medium text-white">{passport.student.name}</div>
              <div className="mt-3 label">Repository</div>
              <div className="flex items-center gap-2 text-sm">
                <Github size={15} className="text-ink-400" />
                {passport.is_demo ? (
                  <span className="mono text-ink-300">{passport.repository.name}</span>
                ) : (
                  <a className="mono text-accent hover:underline" href={passport.repository.url} target="_blank" rel="noreferrer">
                    {passport.repository.owner}/{passport.repository.name}
                  </a>
                )}
              </div>
              <div className="mt-1 text-xs text-ink-400">
                {passport.repository.files_scanned} of {passport.repository.file_count} files scanned
                {passport.repository.is_fork && " · fork"}
              </div>
            </div>
            <div>
              <div className="label">Resume</div>
              {passport.resume ? (
                <div className="flex items-center gap-2 text-sm text-white">
                  <FileText size={15} className="text-ink-400" /> {passport.resume.filename}
                  <span className="text-xs text-ink-400">({passport.resume.claims.length} claims)</span>
                </div>
              ) : (
                <div className="text-sm text-ink-400">Not uploaded — only repository evidence used.</div>
              )}
              <div className="mt-3 label">Latest analysis</div>
              <div className="text-sm text-white">{new Date(passport.created_at).toLocaleString()}</div>
              <div className="mt-3 label">Trust assessment</div>
              <Link to="/trust" className={`inline-flex items-center gap-1.5 text-sm ${t.cls} hover:underline`}>
                <ShieldHalf size={15} /> {t.text}
              </Link>
            </div>
          </div>
        </div>
        <div className="card p-5">
          <div className="label">Latest job match</div>
          {passport.latest_job_match ? (
            <>
              <div className="font-display text-4xl font-semibold text-white">{passport.latest_job_match.score}%</div>
              <div className="mt-1 text-sm text-ink-300">{passport.latest_job_match.job_title}</div>
              <Link to="/job-match" className="btn-ghost mt-4 w-full text-xs">View breakdown</Link>
            </>
          ) : (
            <>
              <p className="text-sm text-ink-400">Paste a job description to see which skills you can prove.</p>
              <Link to="/job-match" className="btn-primary mt-4 w-full"><Target size={16} /> Match a job</Link>
            </>
          )}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Identified skills" value={s.total_skills} />
        <Stat label="Evidence-supported" value={s.evidence_supported} tone="text-emerald-300" />
        <Stat label="Partially supported" value={s.partially_supported} tone="text-amber-300" />
        <Stat label="Needs review" value={s.needs_review} tone="text-rose-300" hint="flagged + unverified claims" />
      </div>
      {review.length > 0 && (
        <section className="card mt-6 p-5">
          <h2 className="mb-3 font-display font-semibold text-white">Skills requiring review</h2>
          <ul className="flex flex-wrap gap-2">
            {review.map((k) => (
              <li key={k.id} className="flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-850 px-3 py-1.5 text-sm">
                {k.skill} <StatusBadge status={k.verification_status} />
              </li>
            ))}
          </ul>
        </section>
      )}
      {recentList}
    </>
  );
}
