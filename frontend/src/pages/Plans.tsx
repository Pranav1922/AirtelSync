import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Ban, CalendarClock, Check, Clock4, Sparkles, Wallet } from "lucide-react";
import { api, inr, type Recommendation } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Badge, Button, Card, ErrorNote, PageTitle, Spinner, cx } from "../components/ui";

export default function Plans() {
  const { t } = useT();
  const nav = useNavigate();
  const { j, set } = useJourney();
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);

  const load = () => {
    if (!j.sessionId) { nav("/advisor"); return; }
    setErr(null);
    api.get<Recommendation>(`/api/advisor/sessions/${j.sessionId}/recommendation`).then(setRec)
      .catch((e) => (e.status === 400 ? nav("/advisor") : setErr(e.message)));
  };
  useEffect(load, [j.sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return <div className="mx-auto max-w-6xl px-4 py-10"><ErrorNote msg={err} onRetry={load} retryLabel={t("common.retry")} /></div>;
  if (!rec) return <div className="mx-auto max-w-6xl px-4"><Spinner label={t("common.loading")} /></div>;

  const p = rec.profile;
  const choose = (level: string) => {
    const o = rec.options.find((x) => x.level === level)!;
    set({ level, items: Object.fromEntries(o.items.map((i) => [i.product_id, i.quantity])) });
    nav("/quote");
  };
  const best = rec.options.find((o) => o.level === rec.recommended)!;
  const allIds = [...new Set(rec.options.flatMap((o) => o.pricing.lines.map((l) => l.product_id)))];
  const names = Object.fromEntries(rec.options.flatMap((o) => o.pricing.lines.map((l) => [l.product_id, l.name])));

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageTitle title={t("plans.title", { name: j.businessName || p.business_type || "" })} sub={t("plans.sub")}
        right={<Link to="/advisor" className="text-sm font-semibold text-slate-600 underline">{t("plans.edit")}</Link>} />

      <div className="mb-6 flex flex-wrap gap-2 text-sm">
        {p.segment && <Badge tone="dark">{t(`seg.${p.segment}`)}</Badge>}
        {p.city && <Badge>{p.city} · {t("f.tier", { n: p.city_tier ?? "" })}</Badge>}
        <Badge>{p.employees} {t("f.employees").toLowerCase()} · {p.sites} {t("f.sites").toLowerCase()}</Badge>
        {p.gstin_status && p.gstin_status !== "none" && <Badge tone={p.gstin_status === "active" ? "green" : "red"}>GST {p.gstin_status}</Badge>}
        {p.budget ? <Badge tone="blue"><Wallet className="size-3" />{t("plans.budget")} {inr(p.budget)}</Badge> : null}
      </div>

      {rec.budget_note && <div className="mb-6"><ErrorNote msg={rec.budget_note} /></div>}

      <div className="mb-6 flex gap-3 rounded-2xl bg-ink-900 p-5 text-white">
        <Sparkles className="mt-0.5 size-5 shrink-0 text-brand-500" />
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-white/60">{t("plans.ai")}</div>
          <p className="mt-1 leading-relaxed text-white/90">
            {rec.ai_summary || `${t(`plans.level.${best.level}`)}: ${best.pitch} ${best.pricing.lines.map((l) => `${l.quantity}× ${l.name}`).join(", ")}. ${inr(best.pricing.monthly_min)}–${inr(best.pricing.monthly_max)}${t("plans.month")}, ${inr(best.pricing.setup_total)} ${t("plans.setup").toLowerCase()}.`}
          </p>
        </div>
      </div>

      <div className={cx("grid gap-5", rec.options.length === 3 ? "lg:grid-cols-3" : rec.options.length === 2 ? "lg:grid-cols-2" : "")}>
        {rec.options.map((o) => {
          const isRec = o.level === rec.recommended;
          return (
            <Card key={o.level} className={cx("relative flex flex-col p-6", isRec && "border-2 border-brand-500 shadow-lg shadow-brand-500/10")}>
              {isRec && <span className="absolute -top-3 left-6 rounded-full bg-brand-500 px-3 py-1 text-xs font-bold text-white">{t("plans.recommended")}</span>}
              <div className="text-sm font-bold uppercase tracking-wider text-slate-500">{t(`plans.level.${o.level}`)}</div>
              <p className="mt-1 min-h-10 text-sm text-slate-600">{o.pitch}</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-xs text-slate-500">{t("plans.from")}</span>
                <span className="text-4xl font-extrabold tracking-tight text-ink-900">{inr(o.pricing.monthly_min)}</span>
                <span className="text-sm text-slate-500">{t("plans.month")}</span>
              </div>
              <div className="text-xs text-slate-500">{t("plans.upto", { v: inr(o.pricing.monthly_max) })}</div>
              <dl className="mt-4 grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-xs">
                <div><dt className="flex items-center gap-1 text-slate-500"><Wallet className="size-3" />{t("plans.setup")}</dt><dd className="mt-0.5 font-semibold text-ink-900">{inr(o.pricing.setup_total)}</dd></div>
                <div><dt className="flex items-center gap-1 text-slate-500"><Clock4 className="size-3" />{t("plans.install")}</dt><dd className="mt-0.5 font-semibold text-ink-900">{t("plans.days", { n: o.pricing.install_days })}</dd></div>
                <div><dt className="flex items-center gap-1 text-slate-500"><CalendarClock className="size-3" />{t("plans.commit")}</dt><dd className="mt-0.5 font-semibold text-ink-900">{t("plans.months", { n: o.pricing.longest_commitment_months })}</dd></div>
              </dl>
              <ul className="mt-5 flex-1 space-y-3">
                {o.items.map((it) => {
                  const line = o.pricing.lines.find((l) => l.product_id === it.product_id)!;
                  return (
                    <li key={it.product_id} className="flex gap-2.5 text-sm">
                      <Check className="mt-0.5 size-4 shrink-0 text-emerald-600" />
                      <div className="min-w-0">
                        <div className="font-semibold text-ink-900">{it.quantity > 1 && `${it.quantity}× `}{line.name} <span className="font-normal text-slate-400">{it.product_id}</span></div>
                        <div className="text-slate-600">{it.reasons.join(" ")}</div>
                      </div>
                    </li>
                  );
                })}
              </ul>
              {o.notes.length > 0 && (
                <details className="mt-4 rounded-lg border border-slate-200 p-3 text-xs text-slate-600">
                  <summary className="cursor-pointer font-semibold text-slate-700">{t("plans.notes")} ({o.notes.length})</summary>
                  <ul className="mt-2 space-y-1">{o.notes.map((n) => <li key={n} className="flex gap-1.5"><Ban className="mt-0.5 size-3 shrink-0 text-slate-400" />{n}</li>)}</ul>
                </details>
              )}
              <Button className="mt-5 w-full" variant={isRec ? "primary" : "dark"} onClick={() => choose(o.level)}>{t("plans.choose")}<ArrowRight className="size-4" /></Button>
            </Card>
          );
        })}
      </div>

      <div className="mt-8">
        <Button variant="outline" onClick={() => setCompare(!compare)}>{compare ? t("plans.compare.hide") : t("plans.compare")}</Button>
        {compare && (
          <Card className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead><tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="p-3 font-medium">Product</th>
                {rec.options.map((o) => <th key={o.level} className="p-3 text-center font-semibold text-ink-900">{t(`plans.level.${o.level}`)}</th>)}
              </tr></thead>
              <tbody>
                {allIds.map((id) => (
                  <tr key={id} className="border-b border-slate-100">
                    <td className="p-3 text-slate-700">{names[id]} <span className="text-slate-400">{id}</span></td>
                    {rec.options.map((o) => {
                      const l = o.pricing.lines.find((x) => x.product_id === id);
                      return <td key={o.level} className="p-3 text-center">{l ? <span className="font-semibold text-ink-900">{l.quantity}×</span> : <span className="text-slate-300">—</span>}</td>;
                    })}
                  </tr>
                ))}
                <tr className="bg-slate-50 font-semibold"><td className="p-3">{t("quote.monthly")}</td>{rec.options.map((o) => <td key={o.level} className="p-3 text-center">{inr(o.pricing.monthly_min)}–{inr(o.pricing.monthly_max)}</td>)}</tr>
                <tr className="bg-slate-50"><td className="p-3">{t("plans.setup")}</td>{rec.options.map((o) => <td key={o.level} className="p-3 text-center">{inr(o.pricing.setup_total)}</td>)}</tr>
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </div>
  );
}
