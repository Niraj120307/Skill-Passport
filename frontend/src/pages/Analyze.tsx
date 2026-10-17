import { useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Circle, FileUp, Github, Loader2, ScanSearch, XCircle, Lock } from "lucide-react";
import { api, type RepoSummary, type ResumeUpload } from "../lib/api";
import { usePassport } from "../lib/store";
import { useToast } from "../components/Toast";
import { PageHeader } from "../components/ui";

type StepState = "idle" | "running" | "done" | "error" | "skipped";
const REPO_RE = /^(https?:\/\/)?(www\.)?github\.com\/[A-Za-z0-9-]{1,39}\/[A-Za-z0-9._-]{1,100}\/?$/;
const MAX_MB = 5;

export default function Analyze() {
  const { setPassport } = usePassport();
  const toast = useToast();
  const nav = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [steps, setSteps] = useState<Record<string, StepState>>({ resume: "idle", repo: "idle", verify: "idle" });
  const [stepMsg, setStepMsg] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [fatal, setFatal] = useState<string | null>(null);

  const setStep = (k: string, v: StepState, msg?: string) => {
    setSteps((s) => ({ ...s, [k]: v }));
    if (msg !== undefined) setStepMsg((m) => ({ ...m, [k]: msg }));
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = "Enter your name.";
    if (!REPO_RE.test(repoUrl.trim())) e.repo = "Use a public repository URL like https://github.com/owner/repo";
    if (file) {
      if (!file.name.toLowerCase().endsWith(".pdf")) e.file = "Only PDF files are accepted.";
      else if (file.size > MAX_MB * 1024 * 1024) e.file = `File must be under ${MAX_MB} MB.`;
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onSubmit = async (ev: FormEvent) => {
    ev.preventDefault();
    if (!validate()) return;
    setRunning(true);
    setFatal(null);
    setSteps({ resume: file ? "idle" : "skipped", repo: "idle", verify: "idle" });
    setStepMsg({});
    let resume: ResumeUpload | null = null;
    let repo: RepoSummary;
    try {
      if (file) {
        setStep("resume", "running");
        try {
          resume = await api.uploadResume(file);
          setStep("resume", "done", `${resume.claims.length} skill claim(s) extracted from ${resume.page_count} page(s)`);
        } catch (e) {
          setStep("resume", "error", e instanceof Error ? e.message : "Resume failed");
          throw e;
        }
      } else setStepMsg((m) => ({ ...m, resume: "No resume uploaded — skipped" }));

      setStep("repo", "running");
      try {
        repo = await api.analyzeGithub(repoUrl.trim());
        setStep("repo", "done", `${repo.files_scanned} files scanned · ${repo.commits_fetched} commits · ${repo.skills_detected.length} skill signals`);
      } catch (e) {
        setStep("repo", "error", e instanceof Error ? e.message : "Repository failed");
        throw e;
      }

      setStep("verify", "running");
      try {
        const p = await api.analyze({ name: name.trim(), repository_id: repo.repository_id, resume_id: resume?.resume_id ?? null });
        setStep("verify", "done", `${p.summary.total_skills} skills assessed`);
        setPassport(p);
        toast("success", "Skill Passport generated.");
        setTimeout(() => nav("/passport"), 600);
      } catch (e) {
        setStep("verify", "error", e instanceof Error ? e.message : "Verification failed");
        throw e;
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      setFatal(msg);
      toast("error", msg);
    } finally {
      setRunning(false);
    }
  };

  const STEPS = [
    { key: "resume", title: "Parse resume", desc: "Extract claimed skills with page numbers (PDF is not stored)" },
    { key: "repo", title: "Fetch & scan repository", desc: "Metadata, commits, archive download, AST + pattern analysis" },
    { key: "verify", title: "Verify skills & authorship", desc: "Score evidence, estimate levels, run Authorship Guard" },
  ];

  return (
    <>
      <PageHeader title="Analyze Work" subtitle="We read your repository as data — code is parsed, never executed. Resume claims are recorded but never count as evidence on their own." />
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <form onSubmit={onSubmit} className="card space-y-5 p-6" noValidate>
          <div>
            <label htmlFor="name" className="label">Your name</label>
            <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Kedar Nimbalkar" maxLength={120} aria-invalid={!!errors.name} />
            {errors.name && <p className="mt-1 text-xs text-rose-300">{errors.name}</p>}
          </div>
          <div>
            <label htmlFor="repo" className="label">Public GitHub repository URL</label>
            <div className="relative">
              <Github size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
              <input id="repo" className="input pl-9 font-mono text-[13px]" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repository" aria-invalid={!!errors.repo} />
            </div>
            {errors.repo && <p className="mt-1 text-xs text-rose-300">{errors.repo}</p>}
          </div>
          <div>
            <span className="label">Resume (PDF, optional, max {MAX_MB} MB)</span>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files?.[0];
                if (f) setFile(f);
              }}
              className="flex w-full flex-col items-center gap-2 rounded-lg border border-dashed border-ink-600 bg-ink-950 px-4 py-6 text-sm text-ink-300 transition hover:border-accent/60"
            >
              <FileUp size={22} className="text-ink-400" />
              {file ? <span className="font-medium text-white">{file.name} · {(file.size / 1024).toFixed(0)} KB</span> : <span>Click or drop a PDF here</span>}
            </button>
            <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label="Resume PDF" />
            {file && (
              <button type="button" className="mt-2 text-xs text-ink-400 hover:text-white" onClick={() => { setFile(null); if (fileRef.current) fileRef.current.value = ""; }}>
                Remove file
              </button>
            )}
            {errors.file && <p className="mt-1 text-xs text-rose-300">{errors.file}</p>}
            <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-400"><Lock size={12} /> Only extracted skill claims are stored; your resume is never shared publicly.</p>
          </div>
          <button type="submit" className="btn-primary w-full" disabled={running}>
            {running ? <Loader2 size={16} className="animate-spin" /> : <ScanSearch size={16} />}
            {running ? "Analyzing…" : "Analyze"}
          </button>
        </form>

        <section className="card p-6" aria-live="polite">
          <h2 className="mb-4 font-display font-semibold text-white">Progress</h2>
          <ol className="space-y-5">
            {STEPS.map((s) => {
              const st = steps[s.key];
              const Icon = st === "done" ? CheckCircle2 : st === "error" ? XCircle : st === "running" ? Loader2 : Circle;
              const tone = st === "done" ? "text-emerald-400" : st === "error" ? "text-rose-400" : st === "running" ? "text-accent" : "text-ink-600";
              return (
                <li key={s.key} className="flex gap-3">
                  <Icon size={20} className={`mt-0.5 shrink-0 ${tone} ${st === "running" ? "animate-spin" : ""}`} />
                  <div>
                    <div className={`text-sm font-medium ${st === "skipped" ? "text-ink-400 line-through" : "text-white"}`}>{s.title}</div>
                    <div className="text-xs text-ink-400">{s.desc}</div>
                    {stepMsg[s.key] && <div className={`mt-1 text-xs ${st === "error" ? "text-rose-300" : "text-ink-300"}`}>{stepMsg[s.key]}</div>}
                  </div>
                </li>
              );
            })}
          </ol>
          {fatal && <p className="mt-5 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">{fatal}</p>}
          <div className="mt-6 border-t border-ink-800 pt-4 text-xs leading-relaxed text-ink-400">
            Unauthenticated GitHub access allows ~60 requests/hour (≈ 6–10 per analysis). Add a free <span className="mono">GITHUB_TOKEN</span> to <span className="mono">backend/.env</span> for more.
          </div>
        </section>
      </div>
    </>
  );
}
