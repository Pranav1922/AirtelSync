import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Camera, Database, FileScan, FlaskConical, Headset, ScanLine, ShieldAlert, ShieldCheck } from "lucide-react";
import { api, type KycCase } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { HelpDrawer } from "../components/Layout";
import { Badge, Button, Card, ErrorNote, PageTitle, STATUS_META, Spinner, cx, inputCls } from "../components/ui";

const DOCS = ["gst_certificate", "udyam_certificate", "address_proof", "signatory_id"];
const SRC_ICON: Record<string, typeof Database> = { extracted: ScanLine, mock_registry: Database, demo_rule: FlaskConical };

export default function Kyc() {
  const { t } = useT();
  const nav = useNavigate();
  const { j } = useJourney();
  const [c, setC] = useState<KycCase | null>(null);
  const [packs, setPacks] = useState<{ applicant: string; documents: string[] }[]>([]);
  const [pack, setPack] = useState(j.kycPack ?? "K03");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [help, setHelp] = useState(false);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const refresh = () => j.caseId && api.get<KycCase>(`/api/kyc/${j.caseId}`).then(setC);
  useEffect(() => {
    if (!j.caseId) { nav("/consent"); return; }
    refresh(); api.get<typeof packs>("/api/kyc/specimens").then(setPacks);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label); setErr(null);
    try { await fn(); await refresh(); } catch (e: any) { setErr(e.message); } finally { setBusy(null); }
  };
  const upload = (type: string, f: File) => run(type, () => {
    const fd = new FormData(); fd.append("doc_type", type); fd.append("file", f);
    return api.post(`/api/kyc/${j.caseId}/documents`, fd);
  });
  const loadPack = () => run("pack", () => api.post(`/api/kyc/${j.caseId}/specimen`, { applicant: pack }));
  const verify = () => run("verify", () => api.post(`/api/kyc/${j.caseId}/verify`));

  if (!c) return <div className="mx-auto max-w-6xl px-4"><Spinner label={t("common.loading")} /></div>;
  const s = c.summary;
  const docOf = (type: string) => c.documents.find((d) => d.declared_type === type);
  const statusTone = s?.status === "passed_demo" || c.status === "approved" ? "green" : s?.status === "manual_review" ? "amber" : "red";

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageTitle title={t("kyc.title")} sub={t("kyc.sub")} />
      <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-600" /><p>{t("kyc.disclaimer")}</p>
      </div>

      <Card className="mb-6 flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <FileScan className="hidden size-5 text-slate-500 sm:block" />
        <div className="flex-1"><div className="text-sm font-semibold text-ink-900">{t("kyc.specimen")}</div><div className="text-xs text-slate-500">{t("kyc.specimen.d")}</div></div>
        <div className="flex gap-2">
          <select className={cx(inputCls, "h-10 w-28")} value={pack} onChange={(e) => setPack(e.target.value)} aria-label={t("kyc.specimen")}>
            {packs.map((p) => <option key={p.applicant} value={p.applicant}>{p.applicant} ({p.documents.length})</option>)}
          </select>
          <Button variant="dark" onClick={loadPack} loading={busy === "pack"}>{t("kyc.load")}</Button>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {DOCS.map((type) => {
          const d = docOf(type);
          return (
            <Card key={type} className="overflow-hidden">
              <div className="flex items-center gap-3 border-b border-slate-100 p-4">
                <span className={cx("grid size-9 place-items-center rounded-lg", d ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500")}>{d ? <ShieldCheck className="size-4" /> : <Camera className="size-4" />}</span>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-ink-900">{t(`kyc.doc.${type}`)}</div>
                  {d ? <div className="flex flex-wrap gap-1.5 pt-0.5">
                    <Badge tone={d.ocr_confidence >= 70 ? "green" : "amber"}>{t("kyc.confidence")} {Math.round(d.ocr_confidence)}%</Badge>
                    {d.quality?.skew_corrected_deg ? <Badge tone="blue">{t("kyc.skew", { n: Math.abs(d.quality.skew_corrected_deg) })}</Badge> : null}
                    {d.quality?.blurred && <Badge tone="amber">{t("kyc.blur")}</Badge>}
                    {d.quality?.specimen && <Badge>SPECIMEN</Badge>}
                  </div> : <div className="text-xs text-slate-500">{t("kyc.missing")}</div>}
                </div>
                <input ref={(el) => { fileRefs.current[type] = el; }} type="file" accept="image/png,image/jpeg" capture="environment" className="sr-only"
                  onChange={(e) => e.target.files?.[0] && upload(type, e.target.files[0])} aria-label={t(`kyc.doc.${type}`)} />
                <Button size="sm" variant="outline" loading={busy === type} onClick={() => fileRefs.current[type]?.click()}>{d ? t("kyc.replace") : t("kyc.upload")}</Button>
              </div>
              {d && (
                <div className="grid gap-4 p-4 sm:grid-cols-[120px_1fr]">
                  {!d.purged && <img src={`/api/kyc/${c.id}/documents/${d.id}/image`} alt="" className="h-36 w-full rounded-lg border border-slate-200 object-cover object-top sm:h-40" />}
                  <dl className="space-y-1.5 text-xs">
                    <div className="mb-1 font-bold uppercase tracking-wide text-slate-400">{t("kyc.extracted")}</div>
                    {Object.entries(d.fields).map(([k, f]) => (
                      <div key={k} className="grid grid-cols-[96px_1fr_36px] items-start gap-2">
                        <dt className="text-slate-500">{k.replace(/_/g, " ")}</dt>
                        <dd className="break-words font-medium text-ink-900">{f.value}</dd>
                        <span className={cx("text-right tabular-nums", f.conf >= 80 ? "text-emerald-600" : f.conf >= 60 ? "text-amber-600" : "text-brand-600")}>{Math.round(f.conf)}</span>
                      </div>
                    ))}
                    {Object.keys(d.fields).length === 0 && <p className="text-slate-500">—</p>}
                  </dl>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {err && <div className="mt-4"><ErrorNote msg={err} /></div>}
      <div className="mt-6 flex flex-wrap gap-3">
        <Button size="lg" onClick={verify} loading={busy === "verify"} disabled={c.documents.length === 0}>{busy === "verify" ? t("kyc.verifying") : t("kyc.verify")}</Button>
        <Button size="lg" variant="outline" onClick={() => setHelp(true)}><Headset className="size-4" />{t("kyc.help")}</Button>
      </div>

      {s && (
        <section className="animate-rise mt-8">
          <Card className="overflow-hidden">
            <div className={cx("flex flex-col gap-3 p-5 sm:flex-row sm:items-center",
              statusTone === "green" ? "bg-emerald-50" : statusTone === "amber" ? "bg-amber-50" : "bg-brand-50")}>
              <div className="flex-1">
                <Badge tone={statusTone}>{t(`kyc.status.${c.status}`)}</Badge>
                <p className="mt-1.5 text-sm text-slate-700">{c.status === "approved" ? c.decision_reason : s.message}</p>
              </div>
              <div className="flex gap-3 text-center text-xs">
                {(["pass", "review", "fail", "info"] as const).map((k) => (
                  <div key={k}><div className="text-xl font-bold text-ink-900">{s.counts[k] ?? 0}</div><div className="text-slate-500">{t(`kyc.check.${k}`)}</div></div>
                ))}
              </div>
            </div>
            <ul className="divide-y divide-slate-100">
              {[...s.checks].sort((a, b) => ["fail", "review", "info", "pass", "demo"].indexOf(a.status) - ["fail", "review", "info", "pass", "demo"].indexOf(b.status)).map((ch, i) => {
                const m = STATUS_META[ch.status]; const Icon = m.icon; const Src = SRC_ICON[ch.source] ?? Database;
                return (
                  <li key={i} className="flex gap-3 p-4">
                    <Icon className={cx("mt-0.5 size-5 shrink-0", m.cls)} aria-label={t(`kyc.check.${ch.status}`)} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-ink-900">{ch.label}</span>
                        <Badge tone={m.tone}>{t(`kyc.check.${ch.status}`)}</Badge>
                        <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Src className="size-3" />{t(`kyc.src.${ch.source}`)}</span>
                      </div>
                      <p className="mt-0.5 text-sm text-slate-600">{ch.detail}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="border-t border-slate-100 bg-slate-50 p-4 text-xs text-slate-500">{s.disclaimer}</p>
          </Card>
          <Button size="lg" className="mt-6" onClick={() => nav(`/track/${j.orderNo}`)}>{t("kyc.track")}<ArrowRight className="size-4" /></Button>
        </section>
      )}
      <HelpDrawer open={help} onClose={() => setHelp(false)} step="kyc" />
    </div>
  );
}
