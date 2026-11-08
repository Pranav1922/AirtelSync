import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, Info, Minus, Plus, Trash2 } from "lucide-react";
import { api, inr, type Pricing, type Product } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Badge, Button, Card, PageTitle, Spinner, cx } from "../components/ui";

type Err = { product_id: string | null; rule: string; message: string };

export default function Quote() {
  const { t } = useT();
  const nav = useNavigate();
  const { j, set } = useJourney();
  const [items, setItems] = useState<Record<string, number>>(j.items ?? {});
  const [cat, setCat] = useState<Product[]>([]);
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [errors, setErrors] = useState<Err[]>([]);
  const [eligibility, setEligibility] = useState<Record<string, string | null>>({});
  const [busy, setBusy] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  useEffect(() => { if (!j.sessionId || !j.items) nav("/plans"); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { api.get<Product[]>("/api/catalogue").then(setCat); }, []);

  // Live price + backend validation on every change.
  useEffect(() => {
    const h = setTimeout(() => {
      api.post<{ pricing: Pricing; errors: Err[] }>("/api/quote/price", { session_id: j.sessionId, items })
        .then((r) => { setPricing(r.pricing); setErrors(r.errors); });
    }, 150);
    set({ items });
    return () => clearTimeout(h);
  }, [items]); // eslint-disable-line react-hooks/exhaustive-deps

  // Ask the backend, once, which catalogue products this business can buy at all.
  useEffect(() => {
    if (!cat.length || !j.sessionId) return;
    api.post<Record<string, string | null>>("/api/eligibility", { session_id: j.sessionId, items: {} }).then(setEligibility);
  }, [cat, j.sessionId]);

  const setQty = (id: string, q: number) => setItems((s) => {
    const n = { ...s };
    if (q <= 0) delete n[id]; else n[id] = Math.min(q, 500);
    return n;
  });
  const byId = useMemo(() => Object.fromEntries(cat.map((p) => [p.id, p])), [cat]);
  const groups = useMemo(() => cat.reduce<Record<string, Product[]>>((g, p) => ((g[p.category] ??= []).push(p), g), {}), [cat]);
  const errFor = (id: string) => errors.filter((e) => e.product_id === id);

  const accept = async () => {
    setBusy(true); setSaveErr(null);
    try {
      const r = await api.post<{ quote_id: string }>("/api/quotes", { session_id: j.sessionId, items, level: j.level });
      set({ quoteId: r.quote_id }); nav("/checkout");
    } catch (e: any) { setSaveErr(e.message); } finally { setBusy(false); }
  };

  if (!pricing) return <div className="mx-auto max-w-6xl px-4"><Spinner label={t("common.loading")} /></div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageTitle title={t("quote.title")} sub={t("quote.sub")} />
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <Card className="divide-y divide-slate-100">
            {pricing.lines.map((l) => {
              const errs = errFor(l.product_id);
              return (
                <div key={l.product_id} className={cx("p-4 sm:p-5", errs.length > 0 && "bg-brand-50/50")}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink-900">{l.name}</span>
                        <Badge>{l.product_id}</Badge><Badge tone="blue">{l.category}</Badge>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {inr(l.unit_price_min)}–{inr(l.unit_price_max)} {l.unit} · {t("quote.line.contract", { n: l.contract_months })} · {t("quote.line.install", { n: l.install_days })}
                        {l.setup > 0 && ` · ${inr(l.setup)} ${t("quote.setup").toLowerCase()}`}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center rounded-lg border border-slate-300" role="group" aria-label={`${t("quote.qty")} ${l.name}`}>
                        <button className="grid size-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => setQty(l.product_id, l.quantity - 1)} aria-label="−"><Minus className="size-4" /></button>
                        <input className="h-9 w-12 border-x border-slate-300 text-center text-sm font-semibold" inputMode="numeric" value={l.quantity}
                          onChange={(e) => setQty(l.product_id, parseInt(e.target.value || "0", 10) || 0)} aria-label={t("quote.qty")} />
                        <button className="grid size-9 place-items-center text-slate-600 hover:bg-slate-50" onClick={() => setQty(l.product_id, l.quantity + 1)} aria-label="+"><Plus className="size-4" /></button>
                      </div>
                      <div className="w-28 text-right">
                        <div className="font-bold text-ink-900">{inr(l.monthly_min)}</div>
                        <div className="text-xs text-slate-500">– {inr(l.monthly_max)}</div>
                      </div>
                      <button onClick={() => setQty(l.product_id, 0)} className="rounded p-2 text-slate-400 hover:bg-slate-100 hover:text-brand-600" aria-label={`${t("quote.remove")} ${l.name}`}><Trash2 className="size-4" /></button>
                    </div>
                  </div>
                  {errs.map((e) => <p key={e.message} className="mt-2 flex items-center gap-1.5 text-sm font-medium text-brand-700"><AlertTriangle className="size-4" />{e.message}</p>)}
                </div>
              );
            })}
          </Card>

          <div>
            <h2 className="mb-3 font-bold text-ink-900">{t("quote.add")}</h2>
            <div className="space-y-5">
              {Object.entries(groups).map(([g, ps]) => (
                <div key={g}>
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">{g}</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {ps.filter((p) => !items[p.id]).map((p) => {
                      const why = eligibility[p.id];
                      const dep = p.requires_one_of.length && !p.requires_one_of.some((d) => items[d]);
                      return (
                        <button key={p.id} disabled={!!why} onClick={() => setQty(p.id, 1)}
                          className="group flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left transition-colors hover:border-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-70">
                          <span className={cx("mt-0.5 grid size-6 shrink-0 place-items-center rounded-md", why ? "bg-slate-200 text-slate-400" : "bg-ink-900 text-white")}><Plus className="size-3.5" /></span>
                          <span className="min-w-0 flex-1">
                            <span className="flex items-baseline justify-between gap-2">
                              <span className="text-sm font-semibold text-ink-900">{p.name}</span>
                              <span className="shrink-0 text-xs font-semibold text-slate-600">{inr(p.price_min)}+</span>
                            </span>
                            <span className="block text-xs text-slate-500">{p.description}</span>
                            {why && <span className="mt-1 block text-xs font-medium text-slate-600">{t("quote.unavailable")}: {why}</span>}
                            {!why && dep ? <span className="mt-1 block text-xs font-medium text-amber-700">{t("quote.needs", { list: p.requires_one_of.map((d) => byId[d]?.name ?? d).join(", ") })}</span> : null}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="lg:sticky lg:top-32 lg:self-start">
          <Card className="overflow-hidden">
            <div className="bg-ink-900 p-5 text-white">
              <div className="text-xs font-bold uppercase tracking-wider text-white/60">{t("quote.monthly")}</div>
              <div className="mt-1 text-4xl font-extrabold tracking-tight">{inr(pricing.monthly_min)}<span className="text-base font-medium text-white/60">{t("plans.month")}</span></div>
              <div className="mt-1 text-sm text-white/70">{t("quote.range", { min: inr(pricing.monthly_min), max: inr(pricing.monthly_max) })}</div>
            </div>
            <dl className="space-y-2.5 p-5 text-sm">
              {[[t("quote.setup"), inr(pricing.setup_total)], [t("quote.first"), inr(pricing.first_bill_min)],
                [t("quote.commit"), t("plans.months", { n: pricing.longest_commitment_months })],
                [t("quote.install"), t("plans.days", { n: pricing.install_days })]].map(([k, v]) => (
                <div key={k} className="flex justify-between"><dt className="text-slate-600">{k}</dt><dd className="font-semibold text-ink-900">{v}</dd></div>
              ))}
            </dl>
            <details className="border-t border-slate-100 px-5 py-4 text-sm">
              <summary className="flex cursor-pointer items-center gap-1.5 font-semibold text-slate-700"><Info className="size-4" />{t("quote.explain")}</summary>
              <p className="mt-2 leading-relaxed text-slate-600">{pricing.explanation}</p>
            </details>
            <div className="border-t border-slate-100 p-5">
              <Badge tone="green" className="mb-3">{t("quote.nodiscount")}</Badge>
              {errors.length > 0 && <p className="mb-3 text-sm font-medium text-brand-700">{t("quote.fix")}</p>}
              {saveErr && <p className="mb-3 text-sm font-medium text-brand-700">{saveErr}</p>}
              <Button size="lg" className="w-full" onClick={accept} loading={busy} disabled={errors.length > 0 || pricing.lines.length === 0}>{t("quote.accept")}<ArrowRight className="size-4" /></Button>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
