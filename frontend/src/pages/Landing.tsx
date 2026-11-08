import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Building2, Factory, FileCheck2, MessageSquareText, PackageCheck, ShieldAlert, Store, Stethoscope, Truck } from "lucide-react";
import { api, type Scenario } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Button, Card } from "../components/ui";

const SEG_ICON: Record<string, typeof Store> = {
  "micro-salon": Store, "prof-clinic": Stethoscope, "multi-retail": Building2, "mfg-workshop": Factory, "kyc-exception": ShieldAlert,
};

export default function Landing() {
  const { t } = useT();
  const nav = useNavigate();
  const { reset, set } = useJourney();
  const [scen, setScen] = useState<Scenario[]>([]);
  useEffect(() => { api.get<Scenario[]>("/api/scenarios").then(setScen).catch(() => setScen([])); }, []);

  const start = (s?: Scenario) => {
    reset();
    if (s) set({ scenarioId: s.id, kycPack: s.kyc_pack, businessName: s.business_name, contactName: s.contact_name, contactRole: s.contact_role });
    nav(s ? `/advisor?demo=${s.id}` : "/advisor");
  };

  const stats = [
    { v: "7.4%", k: "landing.stat.activation" }, { v: "17.6", k: "landing.stat.days" },
    { v: "₹15,053", k: "landing.stat.cac" }, { v: "9.6% vs 2.0%", k: "landing.stat.gst" },
  ];
  const how = [
    { i: MessageSquareText, k: "1" }, { i: PackageCheck, k: "2" }, { i: FileCheck2, k: "3" }, { i: Truck, k: "4" },
  ];

  return (
    <div>
      <section className="relative overflow-hidden bg-ink-900 text-white">
        <div aria-hidden className="pointer-events-none absolute -right-40 -top-40 size-[520px] rounded-full bg-brand-500/20 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[.07] [background-image:linear-gradient(#fff_1px,transparent_1px),linear-gradient(90deg,#fff_1px,transparent_1px)] [background-size:44px_44px]" />
        <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:py-24 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
          <div className="animate-rise">
            <p className="mb-4 inline-flex rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-white/80">{t("landing.eyebrow")}</p>
            <h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">{t("landing.title")}</h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-white/75">{t("landing.sub")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" onClick={() => start()}>{t("landing.cta")}<ArrowRight className="size-4" /></Button>
              <Button size="lg" variant="outline" className="border-white/20 bg-white/5 text-white hover:bg-white/10" onClick={() => document.getElementById("demos")?.scrollIntoView({ behavior: "smooth" })}>{t("landing.demo")}</Button>
            </div>
          </div>
          <ChatPreview />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <h2 className="text-xl font-bold text-ink-900">{t("landing.why")}</h2>
        <p className="text-sm text-slate-500">{t("landing.why.sub")}</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <Card key={s.k} className="p-5">
              <div className="text-3xl font-extrabold tracking-tight text-ink-900">{s.v}</div>
              <div className="mt-1 text-sm text-slate-600">{t(s.k)}</div>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <h2 className="text-xl font-bold text-ink-900">{t("landing.how")}</h2>
          <ol className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {how.map(({ i: Icon, k }, n) => (
              <li key={k} className="relative">
                <span className="grid size-11 place-items-center rounded-xl bg-ink-900 text-white"><Icon className="size-5" /></span>
                <span className="absolute left-14 top-2.5 text-xs font-bold text-brand-500">0{n + 1}</span>
                <h3 className="mt-4 font-semibold text-ink-900">{t(`landing.how.${k}`)}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">{t(`landing.how.${k}d`)}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="demos" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-14">
        <h2 className="text-xl font-bold text-ink-900">{t("landing.scenarios")}</h2>
        <p className="text-sm text-slate-500">{t("landing.scenarios.sub")}</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {scen.map((s) => {
            const Icon = SEG_ICON[s.id] ?? Store;
            const exc = s.id === "kyc-exception";
            return (
              <Card key={s.id} className="group flex flex-col p-5 transition-shadow hover:shadow-md">
                <div className="flex items-start gap-3">
                  <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${exc ? "bg-amber-50 text-amber-700" : "bg-brand-50 text-brand-600"}`}><Icon className="size-5" /></span>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{s.title}</div>
                    <div className="truncate font-semibold text-ink-900">{s.business_name}</div>
                    <div className="text-xs text-slate-500">{s.city} · {s.segment} · {s.lead_id} · KYC {s.kyc_pack}</div>
                  </div>
                </div>
                <p className="mt-3 flex-1 text-sm text-slate-600">{s.focus}</p>
                <Button variant="dark" size="sm" className="mt-4 self-start" onClick={() => start(s)}>{t("landing.scenario.run")}<ArrowRight className="size-4" /></Button>
              </Card>
            );
          })}
        </div>
        <Card className="mt-8 flex flex-col gap-3 bg-ink-900 p-6 text-white sm:flex-row sm:items-center sm:justify-between">
          <span className="font-semibold">{t("landing.console")}</span>
          <Link to="/console"><Button variant="primary">{t("landing.console.cta")}<ArrowRight className="size-4" /></Button></Link>
        </Card>
      </section>
    </div>
  );
}

function ChatPreview() {
  const { t } = useT();
  return (
    <div className="animate-rise mx-auto w-full max-w-sm rounded-[28px] border border-white/10 bg-white p-4 text-slate-800 shadow-2xl shadow-black/40 [animation-delay:.1s]">
      <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-3">
        <span className="grid size-8 place-items-center rounded-full bg-ink-900 text-xs font-bold text-white">S</span>
        <div className="text-sm font-semibold">{t("adv.title")}</div>
        <span className="ml-auto size-2 rounded-full bg-emerald-500" />
      </div>
      <div className="space-y-2 text-sm">
        <p className="max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">{t("adv.q.business_type")}</p>
        <p className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-ink-900 px-3 py-2 text-white">Dental clinic in Kolkata, 5 staff</p>
        <p className="max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">{t("adv.q.needs")}</p>
        <div className="rounded-xl border border-slate-200 p-3">
          <div className="flex items-baseline justify-between"><span className="text-xs font-bold uppercase text-brand-600">{t("plans.level.growth")}</span><span className="text-lg font-extrabold">₹5,868<span className="text-xs font-medium text-slate-500">{t("plans.month")}</span></span></div>
          <div className="mt-1 text-xs text-slate-500">Biz Fibre 300 · 2× Postpaid 599 · Cloud Email · Endpoint Security · Cloud Telephony · Backup</div>
        </div>
      </div>
    </div>
  );
}
