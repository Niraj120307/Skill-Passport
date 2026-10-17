import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ClipboardPaste, Loader2, Map, Target } from "lucide-react";
import { api, type JobMatch, type MatchItem } from "../lib/api";
import { usePassport } from "../lib/store";
import { useToast } from "../components/Toast";
import { DemoNotice, NeedPassport, PageHeader, PageSkeleton, StatusBadge } from "../components/ui";

const CREDIT_COLOR = (c: number) => (c >= 1 ? "#34d399" : c > 0 ? "#fbbf24" : "#f87171");

function Group({ title, items, empty, tone }: { title: string; items: MatchItem[]; empty: string; tone: string }) {
  return (
    <section className="card p-4">
      <h3 className={`mb-3 text-sm font-semibold ${tone}`}>{title} ({items.length})</h3>
      {items.length === 0 ? <p className="text-xs text-ink-400">{empty}</p> : (
        <ul className="space-y-2">
          {items.map((i) => (
            <li key={i.skill_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="text-white">{i.skill} <span className="text-xs text-ink-400">· {i.requirement}</span></span>
              <span className="mono text-ink-300">{i.points}/{i.weight}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function JobMatchPage() {
  const { passport, loading, refresh } = usePassport();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [result, setResult] = useState<JobMatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (passport?.latest_job_match) {
      setResult(passport.latest_job_match);
      setTitle(passport.latest_job_match.job_title);
      setJd(passport.latest_job_match.job_description);
    } else {
      setResult(null);
    }
  }, [passport?.id]);

  if (loading) return <PageSkeleton />;
  if (!passport) return <NeedPassport />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (title.trim().length < 2) return setError("Enter a job title.");
    if (jd.trim().length < 30) return setError("Paste the full job description (at least 30 characters).");
    setBusy(true);
    setError(null);
    try {
      const r = await api.matchJob(passport.id, title.trim(), jd);
      setResult(r);
      toast("success", `Match calculated: ${r.score}%`);
      void refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Matching failed";
      setError(msg);
      toast("error", msg);
    } finally {
      setBusy(false);
    }
  };

  const loadSample = async () => {
    try {
      const j = await api.demoJob();
      setTitle(j.job_title);
      setJd(j.job_description);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Could not load sample");
    }
  };

  const chart = result?.items.map((i) => ({ name: i.skill, earned: i.points, possible: i.weight, credit: i.credit })) ?? [];

  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader title="Job Match" subtitle="Compare a real job description against what your repository can actually prove." />
      <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
        <form onSubmit={submit} className="card space-y-4 p-5" noValidate>
          <div>
            <label htmlFor="jt" className="label">Job title</label>
            <input id="jt" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Backend Developer" maxLength={200} />
          </div>
          <div>
            <label htmlFor="jd" className="label">Job description</label>
            <textarea id="jd" className="input min-h-[260px] resize-y font-mono text-[12.5px] leading-relaxed" value={jd} onChange={(e) => setJd(e.target.value)} placeholder={"Requirements:\n- Python\n- REST APIs with FastAPI\n- Docker\n\nNice to have:\n- CI/CD"} maxLength={20000} />
            <p className="mt-1 text-xs text-ink-400">Lines under “Nice to have / Preferred” count as preferred (weight 1); everything else is required (weight 2).</p>
          </div>
          {error && <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-2.5 text-sm text-rose-200">{error}</p>}
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={busy} type="submit">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Target size={16} />} Analyze match
            </button>
            <button type="button" className="btn-ghost" onClick={loadSample}><ClipboardPaste size={16} /> Use sample JD</button>
          </div>
        </form>

        <div className="space-y-4">
          {!result ? (
            <div className="card grid-bg flex h-full min-h-[300px] flex-col items-center justify-center p-8 text-center text-sm text-ink-400">
              <Target size={28} className="mb-3 text-ink-600" /> Results appear here after you analyze a job description.
            </div>
          ) : (
            <>
              <section className="card p-5">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <div className="label">Evidence-backed match · {result.job_title}</div>
                    <div className="font-display text-5xl font-semibold text-white">{result.score}%</div>
                    <div className="mono mt-1 text-ink-400">{result.points_earned} / {result.points_possible} weighted points</div>
                  </div>
                  <Link to="/roadmap" className="btn-ghost"><Map size={16} /> View roadmap</Link>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-ink-700">
                  <div className="h-full bg-accent" style={{ width: `${result.score}%` }} />
                </div>
                <p className="mt-3 text-xs text-ink-400">{result.formula}</p>
              </section>
              <section className="card p-5">
                <h3 className="mb-3 text-sm font-semibold text-white">Skill gap visualization</h3>
                <div style={{ height: Math.max(160, chart.length * 34) }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chart} layout="vertical" margin={{ left: 10, right: 16 }}>
                      <CartesianGrid stroke="#232d3a" horizontal={false} />
                      <XAxis type="number" domain={[0, 2]} ticks={[0, 0.5, 1, 1.5, 2]} tick={{ fill: "#8a97a8", fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#b6c0cc", fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ background: "#131a23", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }} formatter={(v: number, k: string) => [v, k === "earned" ? "points earned" : "points possible"]} cursor={{ fill: "rgba(62,230,168,0.06)" }} />
                      <Bar dataKey="possible" fill="#232d3a" barSize={14} radius={[0, 3, 3, 0]} />
                      <Bar dataKey="earned" barSize={14} radius={[0, 3, 3, 0]}>
                        {chart.map((c, i) => <Cell key={i} fill={CREDIT_COLOR(c.credit)} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </>
          )}
        </div>
      </div>

      {result && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Group title="Supported" items={result.supported} empty="None yet." tone="text-emerald-300" />
            <Group title="Partially supported" items={result.partial} empty="None." tone="text-amber-300" />
            <Group title="Unverified claims" items={result.unverified_claims} empty="No resume-only claims for this job." tone="text-slate-300" />
            <Group title="Missing evidence" items={result.missing} empty="Nothing missing." tone="text-rose-300" />
          </div>
          <section className="card mt-6 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-ink-800 text-xs uppercase tracking-wider text-ink-400">
                <tr><th className="px-4 py-3">Skill</th><th className="px-4 py-3">Requirement</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Level</th><th className="px-4 py-3">Credit</th><th className="px-4 py-3">Found in JD</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-800">
                {result.items.map((i) => (
                  <tr key={i.skill_id} className="align-top">
                    <td className="px-4 py-2.5 font-medium text-white">{i.skill}</td>
                    <td className="px-4 py-2.5 text-ink-300">{i.requirement} (×{i.weight})</td>
                    <td className="px-4 py-2.5"><StatusBadge status={i.status} /></td>
                    <td className="px-4 py-2.5 text-ink-300">{i.estimated_level ?? "—"}</td>
                    <td className="mono px-4 py-2.5 text-ink-100">{i.credit}</td>
                    <td className="max-w-[260px] truncate px-4 py-2.5 text-xs text-ink-400" title={i.jd_snippet}>{i.jd_snippet}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          {result.not_requested.length > 0 && (
            <p className="mt-3 text-xs text-ink-400">Not requested by this job (not counted, no score inflation): {result.not_requested.join(", ")}</p>
          )}
        </>
      )}
    </>
  );
}
