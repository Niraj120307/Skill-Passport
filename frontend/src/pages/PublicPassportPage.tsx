import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { api, type PublicPassport } from "../lib/api";
import { Logo } from "../components/Layout";
import { EmptyState, LevelBadge, PageSkeleton, SeverityBadge, StatusBadge, StrengthBar } from "../components/ui";
import { EvidenceRow } from "./PassportPage";
import { trustLabel } from "./Dashboard";

export default function PublicPassportPage() {
  const { publicId = "" } = useParams();
  const [data, setData] = useState<PublicPassport | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.publicPassport(publicId).then(setData).catch((e) => setError(e.message));
  }, [publicId]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <header className="mb-8 flex items-center justify-between">
        <Logo />
        <span className="chip border-ink-700 text-ink-300">Read-only</span>
      </header>
      {error && <EmptyState icon={ShieldOff} title="Passport unavailable" body={error} />}
      {!data && !error && <PageSkeleton />}
      {data && (
        <>
          {data.is_demo && (
            <div className="mb-5 rounded-lg border border-violet-400/40 bg-violet-500/10 px-4 py-2.5 text-sm text-violet-200">
              Demo passport — illustrative sample data, not a live verification.
            </div>
          )}
          <section className="card grid-bg p-6">
            <div className="label">Skill Passport</div>
            <h1 className="font-display text-3xl font-semibold text-white">{data.student_name}</h1>
            <p className="mt-1 text-sm text-ink-400">
              Repository: {data.repository.url ? <a className="mono text-accent hover:underline" href={data.repository.url} target="_blank" rel="noreferrer">{data.repository.url.replace("https://github.com/", "")}</a> : <span className="mono">{data.repository.name}</span>}
              {" · "}generated {new Date(data.generated_at).toLocaleDateString()}
            </p>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <span className="text-emerald-300">{data.summary.evidence_supported} evidence-supported</span>
              <span className="text-amber-300">{data.summary.partially_supported} partial</span>
              {data.summary.flagged_for_review > 0 && <span className="text-rose-300">{data.summary.flagged_for_review} flagged</span>}
              <span className={trustLabel(data.trust.level).cls}>Trust: {trustLabel(data.trust.level).text}</span>
            </div>
            {data.trust.signals.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-2">
                {data.trust.signals.map((s, i) => <li key={i} className="flex items-center gap-1.5 text-xs text-ink-300"><SeverityBadge severity={s.severity} /> {s.title}</li>)}
              </ul>
            )}
          </section>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {data.skills.map((s) => (
              <details key={s.id} className="card group p-5">
                <summary className="cursor-pointer list-none">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-display text-lg font-semibold text-white">{s.skill}</h2>
                    <StatusBadge status={s.verification_status} />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-4"><LevelBadge level={s.estimated_level} /><StrengthBar value={s.evidence_strength} /></div>
                  <p className="mt-3 text-sm text-ink-300">{s.explanation}</p>
                  <span className="mt-2 inline-block text-xs text-accent group-open:hidden">Show evidence ({s.evidence.length})</span>
                </summary>
                <ul className="mt-3 space-y-2">{s.evidence.map((e, i) => <EvidenceRow key={i} e={e} />)}</ul>
              </details>
            ))}
          </div>
          <p className="mt-8 text-center text-xs text-ink-600">Static analysis of public repository data. Evidence shows skills used in the repository, not proof of individual authorship.</p>
        </>
      )}
    </div>
  );
}
