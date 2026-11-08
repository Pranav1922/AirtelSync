import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Bot, CheckCircle2, Play, RotateCcw, Send, ShieldAlert, Sparkles } from "lucide-react";
import { api, inr, type Profile, type Scenario } from "../api";
import { useT } from "../i18n";
import { useJourney } from "../store";
import { Badge, Button, Card, cx } from "../components/ui";

// The owner may type a GSTIN; show it masked once sent, as everywhere else in the product.
const maskIds = (s: string) => s.replace(/\b(\d{2})[A-Z0-9]{9}([A-Z0-9]{4})\b/gi, (_m, a, b) => `${a}•••••••••${b}`);
type Msg = { role: "advisor" | "user"; text: string; tags?: string[]; tone?: "ok" | "warn" };
type Turn = { profile: Profile; understood: boolean; extracted: Record<string, any>; next: string | null; chips: string[]; done: boolean; gstin_status?: string };

const NEED_KEYS = ["pos", "whatsapp", "email", "cctv", "failover", "endpoint", "data_backup", "wifi", "website", "telephony",
  "sms", "tollfree", "firewall", "iot", "fleet", "multisite_mgmt", "static_ip", "mobile"];

export default function Advisor() {
  const { t, lang } = useT();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const { j, set, reset } = useJourney();
  const [sid, setSid] = useState<string | undefined>(j.sessionId);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [next, setNext] = useState<string | null>("business_type");
  const [chips, setChips] = useState<string[]>([]);
  const [profile, setProfile] = useState<Profile>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [needs, setNeeds] = useState<string[]>([]);
  const [script, setScript] = useState<string[] | null>(null);
  const [playing, setPlaying] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  const start = async () => {
    const s = await api.post<{ session_id: string; chips: string[] }>("/api/advisor/sessions", { language: lang, scenario: params.get("demo") });
    setSid(s.session_id); set({ sessionId: s.session_id, profile: {}, items: undefined, quoteId: undefined, orderId: undefined, caseId: undefined });
    setMsgs([{ role: "advisor", text: t("adv.hello") }, { role: "advisor", text: t("adv.q.business_type") }]);
    setChips(s.chips); setNext("business_type"); setProfile({}); setNeeds([]);
    return s.session_id;
  };

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const demo = params.get("demo");
    if (j.sessionId && !demo) {
      // Coming back from "Change answers": keep the conversation's facts and continue.
      api.get<Turn>(`/api/advisor/sessions/${j.sessionId}`).then((r) => {
        setProfile(r.profile); setNext(r.next); setChips(r.chips);
        setMsgs([{ role: "advisor", text: t("adv.hello") }, { role: "advisor", text: r.done ? t("adv.done") : t(`adv.q.${r.next}`) }]);
      }).catch(() => start());
    } else start();
    if (demo) api.get<Scenario[]>("/api/scenarios").then((all) => setScript(all.find((x) => x.id === demo)?.script ?? null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs, busy]);

  const ack = (r: Turn): Msg | null => {
    const e = r.extracted;
    const tags: string[] = [];
    if (e.business_type) tags.push(e.business_type);
    if (e.segment) tags.push(t(`seg.${e.segment}`));
    if (e.city) tags.push(e.city);
    if (e.employees) tags.push(`${e.employees} ${t("f.employees").toLowerCase()}`);
    if (e.sites) tags.push(`${e.sites} ${t("f.sites").toLowerCase()}`);
    if (e.current_internet) tags.push(t(`chip.${e.current_internet}`));
    (e.needs ?? []).forEach((n: string) => tags.push(t(`need.${n}`)));
    if (e.budget) tags.push(inr(e.budget));
    if (e.has_gstin === true && !e.gstin) tags.push("GST ✓");
    if (e.has_gstin === false) tags.push("GST ✗");
    if (e.gstin) {
      const st = r.gstin_status;
      return st === "active" ? { role: "advisor", text: t("adv.gst.active"), tags, tone: "ok" }
        : { role: "advisor", text: t("adv.gst.bad", { status: st ?? "unknown" }), tags, tone: "warn" };
    }
    return tags.length ? { role: "advisor", text: t("adv.got"), tags } : null;
  };

  const apply = (r: Turn) => {
    setProfile(r.profile); setNext(r.next); setChips(r.chips); set({ profile: r.profile });
    const out: Msg[] = [];
    const a = ack(r);
    if (!r.understood) out.push({ role: "advisor", text: t("adv.not_understood") });
    else if (a) out.push(a);
    out.push({ role: "advisor", text: r.done ? t("adv.done") : t(`adv.q.${r.next}`) });
    setMsgs((m) => [...m, ...out]);
  };

  const send = async (text: string, session = sid) => {
    if (!text.trim() || !session) return;
    setMsgs((m) => [...m, { role: "user", text: maskIds(text) }]); setInput(""); setBusy(true);
    try {
      apply(await api.post<Turn>(`/api/advisor/sessions/${session}/messages`, { text, expecting: next }));
    } finally { setBusy(false); }
  };

  const sendNeeds = async () => {
    if (!sid) return;
    setMsgs((m) => [...m, { role: "user", text: needs.map((n) => t(`need.${n}`)).join(", ") || "—" }]); setBusy(true);
    try {
      const r = await api.put<{ profile: Profile; next: string | null }>(`/api/advisor/sessions/${sid}/profile`,
        { profile: { needs: [...new Set([...(profile.needs ?? []), ...needs])], needs_asked: true } });
      apply({ profile: r.profile, understood: true, extracted: { needs }, next: r.next, chips: chipsFor(r.next), done: r.next === null });
    } finally { setBusy(false); }
  };
  const chipsFor = (slot: string | null) => (slot === "gstin" ? ["yes", "no"] : slot === "budget" ? ["Under Rs 3,000", "Rs 3,000-10,000", "Rs 10,000-30,000", "Above Rs 30,000", "Not sure"] : []);

  // Replays the scenario's scripted messages with the same API a typing user would hit.
  const play = async () => {
    if (!script) return;
    setPlaying(true);
    const s = await start();
    let expecting: string | null = "business_type";
    for (const line of script) {
      await new Promise((r) => setTimeout(r, 700));
      setMsgs((m) => [...m, { role: "user", text: maskIds(line) }]); setBusy(true);
      const r: Turn = await api.post<Turn>(`/api/advisor/sessions/${s}/messages`, { text: line, expecting });
      await new Promise((res) => setTimeout(res, 350));
      setBusy(false); apply(r); expecting = r.next;
    }
    setPlaying(false);
  };

  const done = next === null && !!profile.segment;
  const chipLabel = (c: string) => {
    const k = `chip.${c}`; const v = t(k); return v === k ? c : v;
  };

  return (
    <div className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-[1fr_340px]">
      <Card className="flex h-[calc(100dvh-12rem)] min-h-[520px] flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <span className="grid size-10 place-items-center rounded-full bg-ink-900 text-white"><Bot className="size-5" /></span>
          <div className="min-w-0 flex-1">
            <h1 className="font-bold text-ink-900">{t("adv.title")}</h1>
            <p className="truncate text-xs text-slate-500">{t("adv.sub")}</p>
          </div>
          {script && <Button size="sm" variant="primary" onClick={play} loading={playing}>{!playing && <Play className="size-4" />}<span className="hidden sm:inline">{playing ? t("adv.playing") : t("adv.play")}</span></Button>}
          <Button size="sm" variant="ghost" onClick={() => { reset(); start(); }} aria-label={t("adv.restart")}><RotateCcw className="size-4" /></Button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50/60 px-4 py-5 sm:px-6" aria-live="polite">
          {msgs.map((m, i) => (
            <div key={i} className={cx("animate-rise flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div className={cx("max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed",
                m.role === "user" ? "rounded-tr-sm bg-ink-900 text-white" : "rounded-tl-sm border border-slate-200 bg-white text-slate-800",
                m.tone === "warn" && "border-amber-200 bg-amber-50", m.tone === "ok" && "border-emerald-200 bg-emerald-50")}>
                {m.tone === "warn" && <ShieldAlert className="mb-0.5 mr-1.5 inline size-4 text-amber-600" />}
                {m.tone === "ok" && <CheckCircle2 className="mb-0.5 mr-1.5 inline size-4 text-emerald-600" />}
                {m.text}
                {m.tags && <div className="mt-2 flex flex-wrap gap-1.5">{m.tags.map((x) => <Badge key={x} tone="slate">{x}</Badge>)}</div>}
              </div>
            </div>
          ))}
          {busy && <div className="flex gap-1 px-2 text-slate-400"><span className="dot">●</span><span className="dot">●</span><span className="dot">●</span></div>}
          <div ref={bottom} />
        </div>

        <div className="border-t border-slate-100 bg-white p-3 sm:p-4">
          {done ? (
            <Button size="lg" className="w-full" onClick={() => nav("/plans")}>{t("adv.see_plans")}<ArrowRight className="size-4" /></Button>
          ) : (
            <>
              {next === "needs" ? (
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2">
                    {NEED_KEYS.map((n) => (
                      <button key={n} onClick={() => setNeeds((s) => s.includes(n) ? s.filter((x) => x !== n) : [...s, n])} aria-pressed={needs.includes(n)}
                        className={cx("rounded-full border px-3 py-1.5 text-sm font-medium transition-colors", needs.includes(n) ? "border-ink-900 bg-ink-900 text-white" : "border-slate-300 bg-white text-slate-700 hover:border-slate-400")}>
                        {t(`need.${n}`)}
                      </button>
                    ))}
                  </div>
                  <Button size="sm" variant="dark" className="mt-3" onClick={sendNeeds} disabled={busy || playing}>{t("adv.needs.done")}</Button>
                </div>
              ) : chips.length > 0 && (
                <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                  {chips.map((c) => (
                    <button key={c} onClick={() => send(c)} disabled={busy || playing}
                      className="shrink-0 rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:border-brand-500 hover:text-brand-600 disabled:opacity-50">
                      {chipLabel(c)}
                    </button>
                  ))}
                </div>
              )}
              <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); send(input); }}>
                <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t("adv.placeholder")} aria-label={t("adv.placeholder")}
                  className="h-12 min-w-0 flex-1 rounded-xl border border-slate-300 px-4 text-[15px] focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20" disabled={playing} />
                <Button type="submit" size="lg" disabled={!input.trim() || busy || playing} aria-label={t("adv.send")}><Send className="size-4" /></Button>
              </form>
            </>
          )}
        </div>
      </Card>

      <aside className="space-y-4">
        <ProfileCard profile={profile} />
        <p className="flex items-start gap-2 px-1 text-xs text-slate-500"><Sparkles className="mt-0.5 size-3.5 shrink-0" />{t("adv.offline")}</p>
      </aside>
    </div>
  );
}

export function ProfileCard({ profile: p }: { profile: Profile }) {
  const { t } = useT();
  const rows: [string, React.ReactNode][] = [];
  if (p.business_type) rows.push([t("f.business_type"), p.business_type]);
  if (p.segment) rows.push([t("f.segment"), t(`seg.${p.segment}`)]);
  if (p.city) rows.push([t("f.city"), <>{p.city} {p.city_tier && <Badge>{t("f.tier", { n: p.city_tier })}</Badge>}</>]);
  if (p.employees) rows.push([t("f.employees"), p.employees]);
  if (p.sites) rows.push([t("f.sites"), p.sites]);
  if (p.current_internet) rows.push([t("f.current_internet"), t(`chip.${p.current_internet}`)]);
  if (p.needs?.length) rows.push([t("f.needs"), <div className="flex flex-wrap justify-end gap-1">{p.needs.map((n) => <Badge key={n}>{t(`need.${n}`)}</Badge>)}</div>]);
  if (p.gstin_status && p.gstin_status !== "none")
    rows.push([t("f.gstin"), <Badge tone={p.gstin_status === "active" ? "green" : p.gstin_status === "unverified" ? "slate" : "red"}>{p.gstin_masked || ""} {p.gstin_status}</Badge>]);
  else if (p.has_gstin === false) rows.push([t("f.gstin"), <Badge>—</Badge>]);
  if (p.budget) rows.push([t("f.budget"), inr(p.budget)]);
  return (
    <Card className="p-5">
      <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t("adv.profile")}</h2>
      {rows.length === 0 ? <p className="mt-3 text-sm text-slate-500">{t("adv.profile.empty")}</p> : (
        <dl className="mt-3 divide-y divide-slate-100">
          {rows.map(([k, v]) => (
            <div key={k} className="animate-rise flex items-start justify-between gap-3 py-2 text-sm">
              <dt className="shrink-0 text-slate-500">{k}</dt><dd className="text-right font-medium text-ink-900">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}
