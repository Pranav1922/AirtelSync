import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, Loader2, ShieldQuestion, XCircle } from "lucide-react";

export function cx(...c: (string | false | null | undefined)[]) { return c.filter(Boolean).join(" "); }

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "dark" | "ghost" | "outline"; size?: "sm" | "md" | "lg"; loading?: boolean };
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }: BtnProps) {
  const v = {
    primary: "bg-brand-500 text-white hover:bg-brand-600 shadow-sm shadow-brand-500/20",
    dark: "bg-ink-900 text-white hover:bg-ink-700",
    outline: "border border-slate-300 bg-white text-slate-800 hover:border-slate-400 hover:bg-slate-50",
    ghost: "text-slate-700 hover:bg-slate-100",
  }[variant];
  const s = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" }[size];
  return (
    <button {...rest} disabled={disabled || loading}
      className={cx("inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed disabled:opacity-50", v, s, className)}>
      {loading && <Loader2 className="size-4 animate-spin" />}{children}
    </button>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  // A caller-supplied background wins over the default white.
  const bg = /(^|\s)bg-/.test(className ?? "") ? "" : "bg-white";
  return <div className={cx("rounded-2xl border border-slate-200 shadow-[0_1px_2px_rgba(15,23,42,.04)]", bg, className)}>{children}</div>;
}

export function Badge({ tone = "slate", children, className }: { tone?: "slate" | "red" | "green" | "amber" | "blue" | "dark"; children: ReactNode; className?: string }) {
  const t = {
    slate: "bg-slate-100 text-slate-700", red: "bg-brand-50 text-brand-700 ring-1 ring-brand-100",
    green: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-100", amber: "bg-amber-50 text-amber-800 ring-1 ring-amber-100",
    blue: "bg-sky-50 text-sky-800 ring-1 ring-sky-100", dark: "bg-ink-900 text-white",
  }[tone];
  return <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", t, className)}>{children}</span>;
}

export function PageTitle({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl">{title}</h1>
        {sub && <p className="mt-1 max-w-2xl text-slate-600">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return <div className="flex items-center gap-2 py-10 text-slate-500"><Loader2 className="size-5 animate-spin" />{label}</div>;
}

export function ErrorNote({ msg, onRetry, retryLabel }: { msg: string; onRetry?: () => void; retryLabel?: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-brand-100 bg-brand-50 p-4 text-sm text-brand-700">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <div className="flex-1">{msg}</div>
      {onRetry && <button onClick={onRetry} className="font-semibold underline">{retryLabel ?? "Retry"}</button>}
    </div>
  );
}

export const STATUS_META = {
  pass: { icon: CheckCircle2, cls: "text-emerald-600", tone: "green" as const },
  fail: { icon: XCircle, cls: "text-brand-600", tone: "red" as const },
  review: { icon: ShieldQuestion, cls: "text-amber-600", tone: "amber" as const },
  info: { icon: Info, cls: "text-sky-600", tone: "blue" as const },
  demo: { icon: Info, cls: "text-slate-500", tone: "slate" as const },
};

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}
export const inputCls = "h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-[15px] text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20";
