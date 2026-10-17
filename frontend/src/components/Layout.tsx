import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, ScanSearch, BadgeCheck, ShieldHalf, Target, Map, Share2, Menu, X } from "lucide-react";
import { usePassport } from "../lib/store";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/analyze", label: "Analyze Work", icon: ScanSearch },
  { to: "/passport", label: "Skill Passport", icon: BadgeCheck },
  { to: "/trust", label: "Trust Analysis", icon: ShieldHalf },
  { to: "/job-match", label: "Job Match", icon: Target },
  { to: "/roadmap", label: "Learning Roadmap", icon: Map },
  { to: "/share", label: "Share Passport", icon: Share2 },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid h-8 w-8 place-items-center rounded-lg border border-accent/40 bg-accent/10">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
          <path d="M5 12.5l4.2 4.2L19 7" stroke="#3ee6a8" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="font-display text-[15px] font-semibold text-white">Skill Passport</div>
        <div className="text-[11px] text-ink-400">verified skills from real work</div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { passport } = usePassport();
  const [open, setOpen] = useState(false);
  const nav = (
    <nav className="flex flex-col gap-1" aria-label="Main">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              isActive ? "bg-accent/10 text-accent" : "text-ink-300 hover:bg-ink-800 hover:text-white"
            }`
          }
        >
          <Icon size={17} /> {label}
        </NavLink>
      ))}
    </nav>
  );
  const current = passport && (
    <div className="mt-6 rounded-lg border border-ink-700 bg-ink-850 p-3 text-xs">
      <div className="text-ink-400">Current passport</div>
      <div className="mt-1 truncate font-medium text-white">{passport.student.name}</div>
      <div className="mono truncate text-ink-400">{passport.repository.owner}/{passport.repository.name}</div>
      {passport.is_demo && <span className="chip mt-2 border-violet-400/40 bg-violet-500/10 text-violet-200">DEMO DATA</span>}
    </div>
  );
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-ink-800 bg-ink-900/60 p-5 lg:block">
        <div className="sticky top-5">
          <Logo />
          <div className="mt-8">{nav}</div>
          {current}
          <p className="mt-6 text-[11px] leading-relaxed text-ink-600">Team Beetles · Code Apex prototype</p>
        </div>
      </aside>
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-ink-800 bg-ink-950/90 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button className="btn-ghost px-2.5 py-2" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen(!open)}>
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </header>
      {open && (
        <div className="border-b border-ink-800 bg-ink-900 p-4 lg:hidden">
          {nav}
          {current}
        </div>
      )}
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
        <Outlet />
      </main>
    </div>
  );
}
