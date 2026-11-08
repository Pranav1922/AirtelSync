import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CreditCard, ReceiptText } from "lucide-react";
import { api, inr, type Order, type Pricing } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Button, Card, ErrorNote, Field, PageTitle, Spinner, cx, inputCls } from "../components/ui";

export default function Checkout() {
  const { t, lang } = useT();
  const nav = useNavigate();
  const { j, set } = useJourney();
  const [q, setQ] = useState<{ pricing: Pricing; setup_total: number } | null>(null);
  const [form, setForm] = useState({ business_name: j.businessName ?? "", contact_name: j.contactName ?? "", contact_role: j.contactRole ?? "Owner", partner_code: "" });
  const [pay, setPay] = useState<"pay_now" | "on_first_bill">("on_first_bill");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!j.quoteId) { nav("/quote"); return; }
    api.get<any>(`/api/quotes/${j.quoteId}`).then(setQ);
  }, [j.quoteId]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const o = await api.post<Order>("/api/checkout", { quote_id: j.quoteId, ...form, partner_code: form.partner_code || null, language: lang, payment_mode: pay });
      set({ orderId: o.id, orderNo: o.order_no, businessName: form.business_name, contactName: form.contact_name });
      nav("/consent");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  if (!q) return <div className="mx-auto max-w-6xl px-4"><Spinner label={t("common.loading")} /></div>;
  const upd = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <PageTitle title={t("co.title")} sub={t("co.sub")} />
      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card className="space-y-5 p-6">
          <Field label={t("co.business")}><input required minLength={2} className={inputCls} value={form.business_name} onChange={upd("business_name")} autoComplete="organization" /></Field>
          <div className="grid gap-4 sm:grid-cols-[1fr_180px]">
            <Field label={t("co.signatory")}><input required minLength={2} className={inputCls} value={form.contact_name} onChange={upd("contact_name")} autoComplete="name" /></Field>
            <Field label={t("co.role")}>
              <select className={inputCls} value={form.contact_role} onChange={upd("contact_role")}>
                {["Owner", "Partner", "Manager", "Office admin"].map((r) => <option key={r}>{r}</option>)}
              </select>
            </Field>
          </div>
          <Field label={t("co.partner")} hint={t("co.partner.hint")}><input className={inputCls} maxLength={20} value={form.partner_code} onChange={upd("partner_code")} placeholder="e.g. CP-NAG-014" /></Field>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-700">{t("co.pay")} · {inr(q.setup_total)}</legend>
            {q.setup_total === 0 ? <p className="text-sm text-slate-600">{t("co.nosetup")}</p> : (
              <div className="grid gap-3 sm:grid-cols-2">
                {([["on_first_bill", ReceiptText, "co.pay.bill"], ["pay_now", CreditCard, "co.pay.now"]] as const).map(([v, Icon, k]) => (
                  <label key={v} className={cx("flex cursor-pointer gap-3 rounded-xl border p-4", pay === v ? "border-ink-900 ring-2 ring-ink-900/10" : "border-slate-200")}>
                    <input type="radio" name="pay" className="sr-only" checked={pay === v} onChange={() => setPay(v)} />
                    <Icon className="size-5 shrink-0 text-ink-900" />
                    <span><span className="block text-sm font-semibold text-ink-900">{t(k)}</span><span className="block text-xs text-slate-500">{t(`${k}.d`)}</span></span>
                  </label>
                ))}
              </div>
            )}
          </fieldset>
          {err && <ErrorNote msg={err} />}
        </Card>
        <aside>
          <Card className="p-5">
            <h2 className="font-bold text-ink-900">{t("co.summary")}</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {q.pricing.lines.map((l) => (
                <li key={l.product_id} className="flex justify-between gap-2"><span className="text-slate-600">{l.quantity}× {l.name}</span><span className="font-medium">{inr(l.monthly_min)}</span></li>
              ))}
            </ul>
            <div className="mt-4 border-t border-slate-100 pt-3 text-sm">
              <div className="flex justify-between font-bold text-ink-900"><span>{t("quote.monthly")}</span><span>{inr(q.pricing.monthly_min)}–{inr(q.pricing.monthly_max)}</span></div>
              <div className="mt-1 flex justify-between text-slate-600"><span>{t("quote.setup")}</span><span>{inr(q.pricing.setup_total)}</span></div>
            </div>
            <Button type="submit" size="lg" className="mt-5 w-full" loading={busy}>{t("co.place")}<ArrowRight className="size-4" /></Button>
          </Card>
        </aside>
      </form>
    </div>
  );
}
