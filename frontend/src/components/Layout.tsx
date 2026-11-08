import { useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { Check, Headset, Languages, X } from "lucide-react";
import { LANGS, useT, type Lang } from "../i18n";
import { useJourney } from "../store";
import { api } from "../api";
import { Button, cx, inputCls } from "./ui";

export function Logo({ light }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden>
        <rect width="32" height="32" rx="8" fill={light ? "#fff" : "#0b1220"} />
        <path d="M21.5 10.5c-1.2-1.3-3-2-5.2-2-3.3 0-5.6 1.7-5.6 4.2 0 5.3 10.6 3.2 10.6 7.4 0 1.5-1.6 2.6-4.2 2.6-2.2 0-4-.8-5.3-2.2" fill="none" stroke="#e11d2e" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <span className="leading-none">
        <span className={cx("block text-[15px] font-extrabold tracking-[.18em]", light ? "text-white" : "text-ink-900")}>SYNC</span>
        <span className={cx("block text-[10px] font-semibold uppercase tracking-[.2em]", light ? "text-white/60" : "text-slate-500")}>Business</span>
      </span>
    </span>
  );
}

const SHORT: Record<Lang, string> = { en: "EN", hi: "हि", ta: "த" };

function LangSwitch() {
  const { lang, setLang } = useT();
  return (
    <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5" role="group" aria-label="Language">
      <Languages className="ml-1.5 hidden size-4 text-slate-400 sm:block" aria-hidden />
      {(Object.keys(LANGS) as Lang[]).map((l) => (
        <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l}
          className={cx("rounded-md px-2 py-1 text-xs font-semibold transition-colors", lang === l ? "bg-ink-900 text-white" : "text-slate-600 hover:bg-slate-100")}>
          <span className="sm:hidden">{SHORT[l]}</span><span className="hidden sm:inline">{LANGS[l]["lang.name"]}</span>
        </button>
      ))}
    </div>
  );
}

export function HelpDrawer({ open, onClose, step }: { open: boolean; onClose: () => void; step?: string }) {
  const { t, lang } = useT();
  const { j } = useJourney();
  const [reason, setReason] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!open) return null;
  const send = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ message: string }>("/api/handoff", { reason, language: lang, session_id: j.sessionId, order_id: j.orderId, step });
      setSent(r.message);
    } finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink-950/50 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={(e) => e.stopPropagation()}
        className="animate-rise w-full max-w-md rounded-t-2xl bg-white p-6 shadow-2xl sm:rounded-2xl">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-full bg-brand-50 text-brand-600"><Headset className="size-5" /></span>
            <div>
              <h2 id="help-title" className="font-bold text-ink-900">{t("help.title")}</h2>
              <p className="text-sm text-slate-600">{t("help.sub")}</p>
            </div>
          </div>
          <button onClick={onClose} aria-label={t("help.close")} className="rounded p-1 text-slate-400 hover:bg-slate-100"><X className="size-5" /></button>
        </div>
        {sent ? (
          <div className="mt-6 flex items-start gap-2 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800"><Check className="mt-0.5 size-4" />{t("help.sent")}</div>
        ) : (
          <div className="mt-5 space-y-3">
            <label className="block text-sm font-medium text-slate-700" htmlFor="help-reason">{t("help.reason")}</label>
            <textarea id="help-reason" value={reason} onChange={(e) => setReason(e.target.value)} rows={3}
              placeholder={t("help.reason.ph")} className={cx(inputCls, "h-auto py-2")} />
            <Button className="w-full" onClick={send} loading={busy} disabled={reason.trim().length < 2}>{t("help.send")}</Button>
          </div>
        )}
      </div>
    </div>
  );
}

const STEPS = [
  { key: "discover", path: "/advisor" }, { key: "plans", path: "/plans" }, { key: "quote", path: "/quote" },
  { key: "checkout", path: "/checkout" }, { key: "kyc", path: "/kyc" }, { key: "track", path: "/track" },
];

export function Stepper() {
  const { t } = useT();
  const { pathname } = useLocation();
  const idx = STEPS.findIndex((s) => pathname.startsWith(s.path) || (s.key === "kyc" && pathname.startsWith("/consent")));
  if (idx < 0) return null;
  return (
    <nav aria-label="Progress" className="border-b border-slate-200 bg-white">
      <ol className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 py-2.5 text-xs font-semibold sm:gap-2 sm:text-sm">
        {STEPS.map((s, i) => (
          <li key={s.key} className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <span className={cx("grid size-5 place-items-center rounded-full text-[10px] sm:size-6 sm:text-xs",
              i < idx ? "bg-ink-900 text-white" : i === idx ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-400")}>
              {i < idx ? <Check className="size-3" /> : i + 1}
            </span>
            <span className={cx(i === idx ? "text-ink-900" : "text-slate-400")}>{t(`steps.${s.key}`)}</span>
            {i < STEPS.length - 1 && <span className="mx-0.5 h-px w-3 bg-slate-200 sm:w-6" />}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { t } = useT();
  const [help, setHelp] = useState(false);
  const { pathname } = useLocation();
  const isConsole = pathname.startsWith("/console");
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4">
          <Link to="/" aria-label="SYNC Business home"><Logo /></Link>
          {isConsole && <span className="hidden rounded-md bg-ink-900 px-2 py-1 text-[11px] font-bold uppercase tracking-wider text-white sm:inline">Intelligence Console</span>}
          <nav className="ml-4 hidden items-center gap-1 md:flex">
            {[["/advisor", "nav.advisor"], ["/track", "nav.track"], ["/console", "nav.console"]].map(([to, k]) => (
              <NavLink key={to} to={to} className={({ isActive }) => cx("rounded-lg px-3 py-2 text-sm font-medium", isActive ? "bg-slate-100 text-ink-900" : "text-slate-600 hover:text-ink-900")}>{t(k)}</NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LangSwitch />
            {!isConsole && (
              <Button variant="outline" size="sm" onClick={() => setHelp(true)} aria-label={t("nav.help")}>
                <Headset className="size-4" /><span className="hidden sm:inline">{t("nav.help")}</span>
              </Button>
            )}
          </div>
        </div>
        <Stepper />
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <span>{t("footer.note")}</span>
          <nav className="flex gap-4 md:hidden">
            <Link to="/track" className="underline">{t("nav.track")}</Link>
            <Link to="/console" className="underline">{t("nav.console")}</Link>
          </nav>
        </div>
      </footer>
      <HelpDrawer open={help} onClose={() => setHelp(false)} step={pathname} />
    </div>
  );
}
