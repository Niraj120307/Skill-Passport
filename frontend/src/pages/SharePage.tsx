import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Copy, ExternalLink, EyeOff, Globe, Loader2, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { usePassport } from "../lib/store";
import { useToast } from "../components/Toast";
import { DemoNotice, NeedPassport, PageHeader, PageSkeleton } from "../components/ui";

export default function SharePage() {
  const { passport, loading, refresh } = usePassport();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (loading) return <PageSkeleton />;
  if (!passport) return <NeedPassport />;
  const { is_public, public_id } = passport.sharing;
  const url = public_id ? `${window.location.origin}/p/${public_id}` : null;

  const toggle = async (enabled: boolean) => {
    setBusy(true);
    try {
      await api.share(passport.id, enabled);
      await refresh();
      toast(enabled ? "success" : "info", enabled ? "Public link enabled." : "Public link disabled — it now returns 404.");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Could not update sharing");
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      toast("success", "Link copied.");
    } catch {
      toast("error", "Clipboard unavailable — select the link and copy it manually.");
    }
  };

  return (
    <>
      {passport.is_demo && <DemoNotice />}
      <PageHeader title="Share Passport" subtitle="Sharing is off until you turn it on. The public page is read-only and sanitized." />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <section className="card p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 font-display text-lg font-semibold text-white">
                {is_public ? <Globe size={18} className="text-accent" /> : <EyeOff size={18} className="text-ink-400" />}
                {is_public ? "Public link is active" : "Passport is private"}
              </div>
              <p className="mt-1 text-sm text-ink-400">{is_public ? "Anyone with the link can view the sanitized passport." : "Nobody else can see this passport."}</p>
            </div>
            <button
              role="switch"
              aria-checked={is_public}
              aria-label="Public sharing"
              disabled={busy}
              onClick={() => void toggle(!is_public)}
              className={`relative h-7 w-12 shrink-0 rounded-full transition ${is_public ? "bg-accent" : "bg-ink-600"} disabled:opacity-50`}
            >
              <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${is_public ? "left-6" : "left-1"}`} />
              {busy && <Loader2 size={12} className="absolute -right-5 top-2 animate-spin text-ink-400" />}
            </button>
          </div>
          {is_public && url && (
            <div className="mt-6">
              <label htmlFor="purl" className="label">Public URL</label>
              <div className="flex gap-2">
                <input id="purl" readOnly value={url} className="input font-mono text-[12.5px]" onFocus={(e) => e.target.select()} />
                <button className="btn-ghost" onClick={copy} aria-label="Copy link"><Copy size={16} /></button>
                <a className="btn-ghost" href={url} target="_blank" rel="noreferrer" aria-label="Open public page"><ExternalLink size={16} /></a>
              </div>
            </div>
          )}
          <div className="mt-6 rounded-lg border border-ink-800 p-4 text-sm">
            <div className="mb-2 flex items-center gap-2 font-medium text-white"><ShieldCheck size={16} className="text-accent" /> What is shared</div>
            <ul className="grid gap-x-6 gap-y-1 text-ink-300 sm:grid-cols-2">
              <li>✓ Your name and repository</li>
              <li>✓ Supported / partial / flagged skills</li>
              <li>✓ Repository evidence references</li>
              <li>✓ Trust signal summary</li>
              <li className="text-ink-400">✗ Resume, file name & claims</li>
              <li className="text-ink-400">✗ Resume-only (unverified) skills</li>
              <li className="text-ink-400">✗ Job descriptions & match scores</li>
              <li className="text-ink-400">✗ Internal IDs or credentials</li>
            </ul>
          </div>
        </section>
        <section className="card flex flex-col items-center p-6 text-center">
          {is_public && url ? (
            <>
              <div className="rounded-xl bg-white p-4"><QRCodeSVG value={url} size={220} level="M" /></div>
              <p className="mt-4 text-sm text-ink-300">Scan to open the read-only passport.</p>
              <p className="mt-1 text-xs text-ink-400">On another device, use your PC's network address instead of localhost.</p>
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center py-10 text-sm text-ink-400">
              <EyeOff size={28} className="mb-3 text-ink-600" /> Turn on sharing to generate a QR code.
            </div>
          )}
        </section>
      </div>
    </>
  );
}
