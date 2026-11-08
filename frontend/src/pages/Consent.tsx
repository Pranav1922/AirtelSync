import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Clock, Eye, FileText, HelpCircle, Lock, Undo2 } from "lucide-react";
import { api } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Button, Card, ErrorNote, PageTitle, cx } from "../components/ui";

const SECTIONS = [
  { k: "what", i: FileText }, { k: "why", i: HelpCircle }, { k: "how", i: Lock },
  { k: "who", i: Eye }, { k: "keep", i: Clock }, { k: "withdraw", i: Undo2 },
];

export default function Consent() {
  const { t, lang } = useT();
  const nav = useNavigate();
  const { j, set } = useJourney();
  const [notice, setNotice] = useState<{ version: string; purposes: Record<string, { required: boolean }> } | null>(null);
  const [choices, setChoices] = useState<Record<string, boolean>>({ kyc_verification: false, service_delivery: false, partner_installation: true, product_updates: false });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { if (!j.orderId) nav("/checkout"); api.get<any>("/api/consent/notice").then(setNotice); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const required = Object.entries(notice?.purposes ?? {}).filter(([, v]) => v.required).map(([k]) => k);
  const ok = required.every((k) => choices[k]);

  const agree = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api.post<{ case_id: string }>(`/api/orders/${j.orderId}/consent`, { choices, language: lang });
      set({ caseId: r.case_id }); nav("/kyc");
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageTitle title={t("consent.title")} sub={t("consent.sub")} />
      <div className="grid gap-3 sm:grid-cols-2">
        {SECTIONS.map(({ k, i: Icon }) => (
          <Card key={k} className="flex gap-3 p-4">
            <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-ink-900"><Icon className="size-4" /></span>
            <div><h2 className="text-sm font-bold text-ink-900">{t(`consent.${k}`)}</h2><p className="mt-0.5 text-sm leading-relaxed text-slate-600">{t(`consent.${k}.d`)}</p></div>
          </Card>
        ))}
      </div>
      <Card className="mt-6 divide-y divide-slate-100">
        {Object.entries(notice?.purposes ?? {}).map(([k, v]) => (
          <label key={k} className="flex cursor-pointer items-center gap-4 p-4">
            <input type="checkbox" className="size-5 accent-brand-500" checked={!!choices[k]} onChange={(e) => setChoices({ ...choices, [k]: e.target.checked })} />
            <span className={cx("text-sm", v.required ? "font-semibold text-ink-900" : "text-slate-700")}>{t(`consent.p.${k}`)}</span>
          </label>
        ))}
      </Card>
      {err && <div className="mt-4"><ErrorNote msg={err} /></div>}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-xs text-slate-500">{notice && t("consent.version", { v: notice.version })}</span>
        <Button size="lg" onClick={agree} disabled={!ok} loading={busy}>{t("consent.agree")}<ArrowRight className="size-4" /></Button>
      </div>
    </div>
  );
}
