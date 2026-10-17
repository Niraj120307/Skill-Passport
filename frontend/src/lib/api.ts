// Typed API client. All business logic lives in the backend; this only calls it.
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the backend. Is it running on port 8000?", 0);
  }
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data?.detail;
    throw new ApiError(typeof detail === "string" ? detail : `Request failed (HTTP ${res.status})`, res.status);
  }
  return data as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type Status = "evidence_supported" | "partially_supported" | "unverified" | "flagged_for_review";
export type Severity = "info" | "low" | "medium" | "high";

export interface EvidenceItem {
  id?: number;
  evidence_type: string;
  source: "repository" | "resume";
  repo_url: string | null;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  commit_sha: string | null;
  url: string | null;
  page: number | null;
  snippet: string | null;
  detail: string;
  weight: number;
  illustrative: boolean;
}

export interface Skill {
  id: number;
  skill: string;
  skill_id: string;
  category: string;
  estimated_level: "Beginner" | "Intermediate" | "Advanced" | null;
  verification_status: Status;
  evidence_strength: number;
  explanation: string;
  limitations: string[];
  resume_claimed: boolean;
  metrics: { strong_weight: number; weak_weight: number; strong_files: number; features: string[]; evidence_count: number };
  evidence: EvidenceItem[];
}

export interface TrustSignal {
  id: number;
  signal_type: string;
  severity: Severity;
  title: string;
  description: string;
  evidence: { label: string; url?: string | null }[];
  limitations: string;
  recommendation: string;
}

export interface Commit {
  sha: string;
  url: string | null;
  date: string;
  author_login: string | null;
  author_name: string | null;
  message: string;
}

export interface MatchItem {
  skill: string;
  skill_id: string;
  requirement: "required" | "preferred";
  weight: number;
  status: Status | "missing";
  credit: number;
  points: number;
  estimated_level: string | null;
  evidence_strength: number;
  jd_snippet: string;
}

export interface RoadmapItem {
  skill: string;
  skill_id: string;
  current_status: string;
  priority: "high" | "medium";
  why_it_matters: string;
  gap_reason: string;
  steps: string[];
  mini_project: string;
  acceptance_criteria: string[];
  evidence_needed: string;
}

export interface JobMatch {
  id: number;
  passport_id: string;
  job_title: string;
  job_description: string;
  score: number;
  created_at: string;
  formula: string;
  points_earned: number;
  points_possible: number;
  items: MatchItem[];
  supported: MatchItem[];
  partial: MatchItem[];
  unverified_claims: MatchItem[];
  missing: MatchItem[];
  important_gaps: MatchItem[];
  not_requested: string[];
  roadmap: RoadmapItem[];
}

export interface Passport {
  id: string;
  is_demo: boolean;
  created_at: string;
  student: { id: number; name: string };
  repository: {
    url: string;
    owner: string;
    name: string;
    description: string | null;
    default_branch: string;
    head_sha: string | null;
    is_fork: boolean;
    parent_full_name: string | null;
    parent_url: string | null;
    stars: number;
    languages: Record<string, number>;
    file_count: number;
    files_scanned: number;
    scan_notes: string[];
    fetched_at: string;
    is_demo: boolean;
  };
  resume: null | {
    id: number;
    filename: string;
    page_count: number;
    claims: { skill: string; skill_id: string; page: number; section: string; snippet: string }[];
    projects: { title: string; page: number; details: string[]; technologies: string[] }[];
    experience: { title: string; page: number; details: string[]; technologies: string[] }[];
    notes: string[];
  };
  summary: {
    total_skills: number;
    evidence_supported: number;
    partially_supported: number;
    unverified: number;
    flagged_for_review: number;
    needs_review: number;
    generated_at: string;
  };
  skills: Skill[];
  trust: {
    level: "no_major_concerns" | "review_recommended" | "high_concern" | "incomplete" | string;
    meta: {
      is_fork: boolean;
      parent_full_name: string | null;
      parent_url: string | null;
      commits_analyzed: number;
      owner_commits: number;
      owner_share: number | null;
      history_complete: boolean;
      assessment_complete: boolean;
      timeline: { date: string; commits: number; owner_commits: number }[];
      recent_commits: Commit[];
      contributors: { login: string; contributions: number }[];
      limitations: string[];
    };
    signals: TrustSignal[];
  };
  sharing: { is_public: boolean; public_id: string | null; public_url: string | null };
  latest_job_match: JobMatch | null;
}

export interface PassportListItem {
  id: string;
  student_name: string;
  repository: string;
  is_demo: boolean;
  created_at: string;
  summary: Passport["summary"];
  trust_level: string;
}

export interface RepoSummary {
  repository_id: number;
  url: string;
  name: string;
  file_count: number;
  files_scanned: number;
  findings_count: number;
  commits_fetched: number;
  skills_detected: string[];
  notes: string[];
}

export interface ResumeUpload {
  resume_id: number;
  filename: string;
  page_count: number;
  claims: { skill: string; page: number }[];
  notes: string[];
}

export interface PublicPassport {
  public_id: string;
  is_demo: boolean;
  student_name: string;
  repository: { url: string | null; name: string; languages: Record<string, number>; is_fork: boolean };
  generated_at: string;
  summary: Passport["summary"];
  trust: { level: string; severity_counts: Record<string, number>; signals: { severity: Severity; title: string }[] };
  skills: Skill[];
}

export interface Roadmap {
  passport_id: string;
  based_on: "job_match" | "passport_gaps";
  job_title: string | null;
  job_match_id: number | null;
  items: RoadmapItem[];
}

export const api = {
  health: () => request<{ status: string; github_token_configured: boolean }>("/api/health"),
  uploadResume: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<ResumeUpload>("/api/resume/upload", { method: "POST", body: fd });
  },
  analyzeGithub: (repo_url: string) => request<RepoSummary>("/api/github/analyze", json({ repo_url })),
  analyze: (body: { name: string; repository_id?: number; repo_url?: string; resume_id?: number | null }) =>
    request<Passport>("/api/analyze", json(body)),
  listPassports: () => request<PassportListItem[]>("/api/passports?limit=10"),
  getPassport: (id: string) => request<Passport>(`/api/passports/${encodeURIComponent(id)}`),
  getEvidence: (id: string) =>
    request<{ count: number; evidence: (EvidenceItem & { skill: string; verification_status: Status })[] }>(
      `/api/passports/${encodeURIComponent(id)}/evidence`,
    ),
  matchJob: (passport_id: string, job_title: string, job_description: string) =>
    request<JobMatch>("/api/match-job", json({ passport_id, job_title, job_description })),
  roadmap: (id: string) => request<Roadmap>(`/api/roadmap/${encodeURIComponent(id)}`),
  share: (id: string, enabled: boolean) =>
    request<Passport["sharing"]>(`/api/passports/${encodeURIComponent(id)}/share`, json({ enabled })),
  publicPassport: (publicId: string) => request<PublicPassport>(`/api/public/passports/${encodeURIComponent(publicId)}`),
  loadDemo: () => request<Passport>("/api/demo/load", { method: "POST" }),
  demoJob: () => request<{ job_title: string; job_description: string }>("/api/demo/job"),
};
