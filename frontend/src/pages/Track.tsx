import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, CalendarCheck, Check, CircleDot, FastForward, PartyPopper, Search, Timer, Trash2 } from "lucide-react";
import { api, inr, type Order } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Badge, Button, Card, ErrorNote, Spinner, cx, inputCls } from "../components/ui";

const fmt = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

export default function Track() {
  const { t } = useT();
  const { no } = useParams();
  const nav = useNavigate();
  const { j } = useJourney();
  const [o, setO] = useState<Order | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const key = no ?? j.orderNo;

  const load = () => key && api.get<Order>(`/api/orders/${key}`).then((x) => { setO(x); setErr(null); }).catch((e) => setErr(e.message));
  useEffect(() => { setO(null); load(); }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (body: object) => {
    setBusy(true); setErr(null);
    try { setO(await api.post<Order>(`/api/orders/${o!.id}/advance`, body)); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  const withdraw = async () => {
    if (!confirm(t("track.withdraw.confirm"))) return;
    await api.post(`/api/orders/${o!.id}/consent/withdraw`); load();
  };

  if (!key) return (
    <div className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-2xl font-bold text-ink-900">{t("track.find")}</h1>
      <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); q.trim() && nav(`/track/${q.trim().toUpperCase()}`); }}>
        <input className={inputCls} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("track.find.ph")} aria-label={t("track.find")} />
        <Button type="submit"><Search className="size-4" />{t("track.find.go")}</Button>
      </form>
    </div>
  );
  if (err && !o) return <div className="mx-auto max-w-3xl px-4 py-10"><ErrorNote msg={err} /></div>;
  if (!o) return <div className="mx-auto max-w-6xl px-4"><Spinner label={t("common.loading")} /></div>;

  const live = o.stage === "activated";
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm text-slate-500">{o.customer.business_name} · {o.customer.city}</div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl">{t("track.title", { no: o.order_no })}</h1>
        </div>
        <Badge tone="slate">{t(`track.pay.${o.payment_status}`)}</Badge>
      </div>

      {live && <Card className="animate-rise mb-6 flex items-center gap-3 border-emerald-200 bg-emerald-50 p-5 text-emerald-900"><PartyPopper className="size-6" /><span className="font-semibold">{t("track.live")}</span></Card>}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-5"><div className="text-xs font-bold uppercase tracking-wide text-slate-500">{t("track.status")}</div><div className="mt-1 text-lg font-bold text-ink-900">{t(`track.st.${o.stage}`)}</div></Card>
            <Card className="p-5"><div className="flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-slate-500"><CalendarCheck className="size-3.5" />{t("track.expected")}</div><div className="mt-1 text-lg font-bold text-ink-900">{fmt(o.expected_activation)}</div></Card>
          </div>
          {o.delay_reason && <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><AlertTriangle className="mt-0.5 size-4 shrink-0" /><span><b>{t("track.delay")}:</b> {o.delay_reason}</span></div>}

          <Card className="p-5 sm:p-6">
            <ol className="relative space-y-0">
              {o.timeline.map((s, i) => (
                <li key={s.stage} className="relative flex gap-4 pb-6 last:pb-0">
                  {i < o.timeline.length - 1 && <span className={cx("absolute left-[15px] top-8 h-[calc(100%-2rem)] w-0.5", s.state === "done" ? "bg-ink-900" : "bg-slate-200")} />}
                  <span className={cx("relative z-10 grid size-8 shrink-0 place-items-center rounded-full",
                    s.state === "done" ? "bg-ink-900 text-white" : s.state === "current" ? "bg-brand-500 text-white ring-4 ring-brand-100" : "border-2 border-slate-200 bg-white text-slate-300")}>
                    {s.state === "done" ? <Check className="size-4" /> : s.state === "current" ? <CircleDot className="size-4" /> : <Timer className="size-4" />}
                  </span>
                  <div className="flex flex-1 items-baseline justify-between gap-3 pt-1">
                    <span className={cx("font-semibold", s.state === "upcoming" ? "text-slate-400" : "text-ink-900")}>{t(`track.st.${s.stage}`)}</span>
                    <span className="text-xs text-slate-500">{fmt(s.expected)}</span>
                  </div>
                </li>
              ))}
            </ol>
          </Card>

          {o.pending_actions.length > 0 && (
            <Card className="p-5">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t("track.pending")}</h2>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">{o.pending_actions.map((a) => <li key={a}>• {a}</li>)}</ul>
              {o.stage === "kyc" && o.kyc_case_id && <Link to="/kyc" className="mt-3 inline-block text-sm font-semibold text-brand-600 underline">{t("track.kyc")}</Link>}
            </Card>
          )}

          <Card className="p-5">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t("track.history")}</h2>
            <ul className="mt-3 space-y-3">
              {[...o.events].reverse().map((e, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="w-24 shrink-0 text-xs text-slate-400">{new Date(e.at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                  <span className="text-slate-700"><b className="font-semibold text-ink-900">{t(`track.st.${e.stage}`)}</b> — {e.note}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card className="p-5">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t("track.products")}</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {o.quote.pricing.lines.map((l) => (
                <li key={l.product_id} className="flex justify-between gap-2"><span>{l.quantity}× {l.name}</span><span className="text-xs text-slate-500">~{l.install_days}d</span></li>
              ))}
            </ul>
            <div className="mt-3 border-t border-slate-100 pt-3 text-sm font-bold text-ink-900">{inr(o.quote.pricing.monthly_min)}–{inr(o.quote.pricing.monthly_max)}{t("plans.month")}</div>
          </Card>
          {!live && (
            <Card className="border-dashed p-5">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t("track.demo")}</h2>
              <div className="mt-3 flex flex-col gap-2">
                <Button variant="dark" onClick={() => act({})} loading={busy}><FastForward className="size-4" />{t("track.demo.next")}</Button>
                <Button variant="outline" onClick={() => act({ delay_reason: "Engineer visit rescheduled by 2 days" })} disabled={busy}>{t("track.demo.delay")}</Button>
              </div>
              {err && <p className="mt-2 text-xs font-medium text-brand-700">{err}</p>}
            </Card>
          )}
          {o.kyc_case_id && o.kyc?.status !== "withdrawn" && (
            <button onClick={withdraw} className="flex items-center gap-1.5 px-1 text-xs text-slate-500 underline hover:text-brand-600"><Trash2 className="size-3.5" />{t("track.withdraw")}</button>
          )}
        </aside>
      </div>
    </div>
  );
}
