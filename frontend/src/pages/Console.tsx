import { useEffect, useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, AlertOctagon, ChevronDown, ClipboardCheck, Headset, Package, RefreshCw, Target, Users } from "lucide-react";
import { api, inr } from "../api";
import { Badge, Button, Card, ErrorNote, STATUS_META, Spinner, cx, inputCls } from "../components/ui";

const C = { opts: { console: true } };
const VIZ = { one: "#2a78d6", yes: "#2a78d6", partial: "#eb6834", no: "#1baf7a" };
const AXIS = { fontSize: 12, fill: "#64748b" };

// Proposed pilot targets. These are goals, not observed results.
const TARGETS = [
  { k: "conversion_pct", label: "Lead → activation", fmt: (v: number) => `${v}%`, target: "12%", why: "Remove visit and quote delays" },
  { k: "days_to_activate", label: "Lead → activation time", fmt: (v: number) => `${v} days`, target: "≤ 9 days", why: "Instant quote + KYC, parallel install" },
  { k: "blended_cac", label: "Blended acquisition cost", fmt: (v: number) => inr(v), target: "≤ ₹9,000", why: "Digital-first for micro; field force on high value" },
  { k: "needs_to_quote_pct", label: "Needs assessed → quote accepted", fmt: (v: number) => `${v}%`, target: "60%", why: "Plain-language, instant, budget-aware quote" },
  { k: "churn_6m_pct", label: "6-month churn", fmt: (v: number) => `${v}%`, target: "≤ 11%", why: "Right-sized bundles, fewer surprises" },
  { k: "follow_up_calls", label: "Status chases per customer", fmt: (v: number) => `${v}`, target: "≤ 1", why: "Live tracker with expected dates" },
];

type Tab = "overview" | "leads" | "kyc" | "orders" | "help";
const TABS: { k: Tab; label: string; icon: typeof Activity }[] = [
  { k: "overview", label: "Acquisition analytics", icon: Activity }, { k: "leads", label: "Lead priority", icon: Target },
  { k: "kyc", label: "KYC exceptions", icon: ClipboardCheck }, { k: "orders", label: "Orders", icon: Package },
  { k: "help", label: "Assistance queue", icon: Headset },
];

export default function Console() {
  const [tab, setTab] = useState<Tab>("overview");
  const [live, setLive] = useState<Record<string, number> | null>(null);
  const loadLive = () => api.get<Record<string, number>>("/api/console/live", C.opts).then(setLive);
  useEffect(() => { loadLive(); }, [tab]);
  const reset = async () => { if (confirm("Delete all demo sessions, quotes, orders and KYC cases?")) { await api.post("/api/demo/reset"); loadLive(); } };

  return (
    <div className="min-h-[calc(100dvh-4rem)] bg-slate-100/70">
      <div className="bg-ink-900 text-white">
        <div className="mx-auto max-w-7xl px-4 pb-0 pt-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.2em] text-brand-500">Accel Business · Sales & partners</p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">SYNC Intelligence Console</h1>
              <p className="mt-1 text-sm text-white/60">Historical figures from smb_leads.csv (Apr–Jun 2026, synthetic). Live figures from this prototype.</p>
            </div>
            {live && (
              <div className="flex flex-wrap gap-4 text-sm">
                {[["Sessions", live.advisor_sessions], ["Quotes", live.quotes], ["Orders", live.orders], ["Live", live.activated], ["KYC open", live.kyc_open_exceptions], ["Callbacks", live.handoffs_open]].map(([k, v]) => (
                  <div key={k as string}><div className="text-xl font-bold">{v}</div><div className="text-xs text-white/50">{k}</div></div>
                ))}
                <button onClick={reset} className="self-center rounded-md border border-white/20 px-2 py-1 text-xs text-white/70 hover:bg-white/10">Reset demo data</button>
              </div>
            )}
          </div>
          <nav className="mt-6 flex gap-1 overflow-x-auto" role="tablist">
            {TABS.map(({ k, label, icon: Icon }) => (
              <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                className={cx("flex shrink-0 items-center gap-2 rounded-t-lg px-4 py-2.5 text-sm font-semibold", tab === k ? "bg-slate-100 text-ink-900" : "text-white/70 hover:text-white")}>
                <Icon className="size-4" />{label}
              </button>
            ))}
          </nav>
        </div>
      </div>
      <div className="mx-auto max-w-7xl px-4 py-6">
        {tab === "overview" && <Overview />}
        {tab === "leads" && <Leads />}
        {tab === "kyc" && <KycQueue onChange={loadLive} />}
        {tab === "orders" && <Orders />}
        {tab === "help" && <Handoffs onChange={loadLive} />}
      </div>
    </div>
  );
}

function Panel({ title, sub, children, className }: { title: string; sub?: string; children: ReactNode; className?: string }) {
  return (
    <Card className={cx("p-5", className)}>
      <h2 className="font-bold text-ink-900">{title}</h2>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
      <div className="mt-4">{children}</div>
    </Card>
  );
}

function useLoad<T>(path: string) {
  const [d, setD] = useState<T | null>(null);
  const [e, setE] = useState<string | null>(null);
  const load = () => api.get<T>(path, C.opts).then(setD).catch((x) => setE(x.message));
  useEffect(() => { load(); }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  return { d, e, load };
}

const tip = { contentStyle: { borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }, cursor: { fill: "rgba(15,23,42,.04)" } };

function Overview() {
  const { d, e } = useLoad<any>("/api/console/overview");
  if (e) return <ErrorNote msg={e} />;
  if (!d) return <Spinner label="Loading analytics…" />;
  const T = d.totals;
  const seg = d.dimensions.segment;
  const src = [...d.dimensions.lead_source].sort((a: any, b: any) => b.conversion_pct - a.conversion_pct);
  const drops = d.drop_reasons.slice(0, 14).map((r: any) => ({ ...r, short: r.reason.length > 34 ? r.reason.slice(0, 32) + "…" : r.reason }));
  const hv = d.historical_violations;

  return (
    <div className="space-y-6">
      <section>
        <div className="mb-3 flex items-baseline justify-between"><h2 className="font-bold text-ink-900">Success metrics</h2><span className="text-xs text-slate-500">Observed baseline → <b>proposed pilot target</b></span></div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {TARGETS.map((m) => (
            <Card key={m.k} className="p-4">
              <div className="text-xs font-medium text-slate-500">{m.label}</div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-extrabold tracking-tight text-ink-900">{m.fmt(T[m.k])}</span>
                <span className="text-xs text-slate-400">observed</span>
              </div>
              <div className="mt-2 flex items-center gap-2"><Badge tone="dark">Target {m.target}</Badge><span className="text-xs text-slate-500">{m.why}</span></div>
            </Card>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Acquisition funnel" sub="Leads reaching each stage (cumulative). Labels show % of the previous stage.">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={d.funnel} layout="vertical" margin={{ left: 10, right: 50 }}>
              <CartesianGrid horizontal={false} stroke="#eef2f7" />
              <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="stage" width={110} tick={AXIS} axisLine={false} tickLine={false} />
              <Tooltip {...tip} formatter={(v: number, _n, p: any) => [`${v.toLocaleString("en-IN")} leads (${p.payload.pct_of_previous}% of previous)`, "Reached"]} />
              <Bar dataKey="count" fill={VIZ.one} radius={[0, 4, 4, 0]} barSize={22}
                label={{ position: "right", fontSize: 11, fill: "#334155", formatter: (v: number) => v.toLocaleString("en-IN") }} />
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-600">Steepest drop: <b>needs assessed → quote accepted (43.6%)</b>. Overall {T.conversion_pct}% of leads activated; blended CAC <b>{inr(T.blended_cac)}</b> (total spend {inr(T.acquisition_spend)} ÷ {T.activated} activations). Mean cost recorded on activated leads alone is only {inr(d.mean_cac_activated_only)} — the wrong number to quote.</p>
        </Panel>

        <Panel title="Segment economics" sub="Conversion is activations ÷ leads in the segment.">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={seg} margin={{ top: 16 }}>
              <CartesianGrid vertical={false} stroke="#eef2f7" />
              <XAxis dataKey="key" tick={{ ...AXIS, fontSize: 11 }} tickFormatter={(v: string) => v.replace("Small ", "").replace(" & services", "").replace(" businesses", "")} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} unit="%" />
              <Tooltip {...tip} formatter={(v: number) => [`${v}%`, "Lead → activation"]} />
              <Bar dataKey="conversion_pct" fill={VIZ.one} radius={[4, 4, 0, 0]} barSize={36} label={{ position: "top", fontSize: 11, fill: "#334155", formatter: (v: number) => `${v}%` }} />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[520px] text-xs">
              <thead><tr className="text-left text-slate-500"><th className="py-1.5 font-medium">Segment</th><th className="text-right font-medium">Leads</th><th className="text-right font-medium">Live</th><th className="text-right font-medium">CAC</th><th className="text-right font-medium">Median ₹/mo</th><th className="text-right font-medium">6m churn</th><th className="text-right font-medium">NPS</th></tr></thead>
              <tbody>{seg.map((s: any) => (
                <tr key={s.key} className="border-t border-slate-100"><td className="py-1.5 font-medium text-ink-900">{s.key}</td><td className="text-right">{s.leads}</td><td className="text-right">{s.activated}</td><td className="text-right">{inr(s.blended_cac)}</td><td className="text-right">{inr(s.median_bundle_inr)}</td><td className="text-right">{s.churn_6m_pct}%</td><td className="text-right">{s.nps_mean}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
        <Panel title="Why leads drop" sub="Terminal drop reason, coloured by whether the digital journey addresses it.">
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={drops} layout="vertical" margin={{ left: 10, right: 40 }}>
              <CartesianGrid horizontal={false} stroke="#eef2f7" />
              <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="short" width={200} tick={{ ...AXIS, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...tip} formatter={(v: number, _n, p: any) => [`${v} leads · ${p.payload.stage}`, p.payload.lever || "Not addressed"]} />
              <Legend payload={[{ value: "Addressed", type: "square", color: VIZ.yes }, { value: "Partly addressed", type: "square", color: VIZ.partial }, { value: "Out of scope", type: "square", color: VIZ.no }]} wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16} label={{ position: "right", fontSize: 11, fill: "#334155" }}>
                {drops.map((r: any) => <Cell key={r.reason} fill={VIZ[r.addressable as "yes" | "partial" | "no"]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-slate-600"><b>{d.addressable_drops.toLocaleString("en-IN")}</b> drops are directly addressed (no visit, instant quote, instant document checks) and <b>{d.partially_addressable_drops.toLocaleString("en-IN")}</b> partly.</p>
        </Panel>

        <div className="space-y-6">
          <Panel title="Lead source" sub="Lead → activation and blended CAC per source.">
            <table className="w-full text-sm">
              <tbody>{src.map((s: any) => (
                <tr key={s.key} className="border-t border-slate-100 first:border-0">
                  <td className="py-2 font-medium text-ink-900">{s.key}</td>
                  <td className="w-32 py-2"><div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full" style={{ width: `${s.conversion_pct / 15 * 100}%`, background: VIZ.one }} /></div></td>
                  <td className="w-14 text-right tabular-nums">{s.conversion_pct}%</td>
                  <td className="w-20 text-right tabular-nums text-slate-600">{inr(s.blended_cac)}</td>
                </tr>
              ))}</tbody>
            </table>
          </Panel>
          <Panel title="Compliance leakage in manual selling" sub="Activated bundles re-checked against catalogue rules.">
            <div className="flex items-start gap-3 rounded-xl bg-brand-50 p-3 text-sm text-brand-700">
              <AlertOctagon className="mt-0.5 size-5 shrink-0" />
              <span><b>{hv.bundles_with_violations} of {hv.activated}</b> activated bundles break a catalogue rule; <b>{d.compliance.activated_with_inactive_gstin}</b> customers were activated on a cancelled or suspended GSTIN. The SYNC engine blocks all of these on the backend.</span>
            </div>
            <ul className="mt-3 space-y-1 text-xs text-slate-600">
              {hv.items.slice(0, 5).map((v: any) => <li key={v.rule + v.product_id} className="flex justify-between"><span>{v.rule} · {v.product_id}</span><b className="text-ink-900">{v.count}</b></li>)}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Leads() {
  const { d, e } = useLoad<any>("/api/console/leads");
  const [open, setOpen] = useState<string | null>(null);
  if (e) return <ErrorNote msg={e} />;
  if (!d) return <Spinner label="Scoring leads…" />;
  const bt = d.model.backtest;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 p-5">
          <h2 className="font-bold text-ink-900">Re-engagement queue</h2>
          <p className="text-xs text-slate-500">Dropped leads whose reason the digital journey can fix, ranked by propensity × opportunity × recoverability. Click a row to see why.</p>
        </div>
        <div className="divide-y divide-slate-100">
          {d.queue.map((l: any) => (
            <div key={l.lead_id}>
              <button onClick={() => setOpen(open === l.lead_id ? null : l.lead_id)} className="grid w-full grid-cols-[48px_1fr_auto] items-center gap-3 p-4 text-left hover:bg-slate-50 sm:grid-cols-[48px_1.4fr_1fr_120px_24px]" aria-expanded={open === l.lead_id}>
                <span className="grid size-11 place-items-center rounded-xl bg-ink-900 text-sm font-bold text-white">{l.priority_score}</span>
                <span className="min-w-0"><span className="block truncate font-semibold text-ink-900">{l.business_name}</span><span className="block truncate text-xs text-slate-500">{l.lead_id} · {l.city} · {l.segment}</span></span>
                <span className="hidden min-w-0 text-xs text-slate-600 sm:block"><span className="block truncate">{l.drop_reason}</span><span className="text-slate-400">at {l.stage_reached}</span></span>
                <span className="hidden sm:block"><Badge tone={l.owner === "Channel partner" ? "blue" : l.owner === "Field sales" ? "dark" : "slate"}>{l.owner}</Badge></span>
                <ChevronDown className={cx("size-4 text-slate-400 transition-transform", open === l.lead_id && "rotate-180")} />
              </button>
              {open === l.lead_id && (
                <div className="animate-rise grid gap-4 bg-slate-50 px-4 pb-4 sm:grid-cols-2 sm:px-16">
                  <div>
                    <div className="text-xs font-bold uppercase text-slate-500">Score drivers (points)</div>
                    <ul className="mt-2 space-y-1 text-sm">{l.why.map((w: any) => (
                      <li key={w.feature} className="flex items-center justify-between gap-2"><span className="text-slate-600">{w.feature}: <b className="text-ink-900">{w.value}</b></span>
                        <span className={cx("tabular-nums font-semibold", w.points > 0 ? "text-emerald-700" : w.points < 0 ? "text-brand-600" : "text-slate-400")}>{w.points > 0 ? "+" : ""}{w.points}</span></li>
                    ))}</ul>
                  </div>
                  <div className="text-sm">
                    <div className="text-xs font-bold uppercase text-slate-500">Recommended next action</div>
                    <p className="mt-2 text-slate-700">{l.next_action}</p>
                    <p className="mt-2 text-xs text-slate-500">Propensity {(l.propensity * 100).toFixed(0)}% · segment median bundle {inr(l.opportunity_inr)}/mo · source {l.lead_source}</p>
                    {l.compliance_hold && <Badge tone="red" className="mt-2">GSTIN not active: resolve before GST products</Badge>}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
      <aside className="space-y-4">
        <Card className="p-5">
          <h3 className="flex items-center gap-2 font-bold text-ink-900"><Users className="size-4" />How the score works</h3>
          <p className="mt-2 text-sm text-slate-600">Additive log-odds per signal (naive Bayes with smoothing), learned from historical activation. Every point shown is the actual weight.</p>
          <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <div>Train {bt.train} · test {bt.test} ({bt.test_leads.toLocaleString("en-IN")} leads)</div>
            <div className="mt-1 text-lg font-bold text-ink-900">AUC {bt.auc}</div>
            <div className="mt-1">{bt.note}</div>
          </div>
          <div className="mt-3 text-xs text-slate-600"><b>Signals used:</b> segment, lead source, GSTIN status, Udyam, current internet, turnover band, city tier.</div>
          <div className="mt-1 text-xs text-slate-600"><b>Never used:</b> preferred language, names, contact role, state or city.</div>
          <div className="mt-1 text-xs text-slate-600"><b>Guardrail:</b> cancelled / suspended GSTINs can only lower a score, even though history (wrongly) activated some.</div>
        </Card>
      </aside>
    </div>
  );
}

function KycQueue({ onChange }: { onChange: () => void }) {
  const { d, e, load } = useLoad<any[]>("/api/console/kyc");
  const [reason, setReason] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  if (e) return <ErrorNote msg={e} />;
  if (!d) return <Spinner />;
  const decide = async (id: string, decision: string) => {
    try { await api.post(`/api/console/kyc/${id}/decision`, { decision, reviewer: "KYC desk (demo)", reason: reason[id] ?? "" }, C.opts); setMsg(null); load(); onChange(); }
    catch (x: any) { setMsg(x.message); }
  };
  if (!d.length) return <Card className="p-10 text-center text-slate-500">No KYC cases yet. Run a demo journey to create one.</Card>;
  return (
    <div className="space-y-4">
      {msg && <ErrorNote msg={msg} />}
      {d.map((c) => {
        const open = c.status === "manual_review" || c.status === "action_required";
        return (
          <Card key={c.id} className="p-5">
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1"><div className="font-semibold text-ink-900">{c.business_name} <span className="text-sm font-normal text-slate-500">· {c.city} · {c.order_no}</span></div></div>
              <Badge tone={c.status === "passed_demo" || c.status === "approved" ? "green" : c.status === "manual_review" ? "amber" : "red"}>{c.status.replace("_", " ")}</Badge>
            </div>
            {c.issues.length > 0 && (
              <ul className="mt-3 space-y-2">{c.issues.map((i: any, n: number) => {
                const M = STATUS_META[i.status as "fail" | "review"]; const Icon = M.icon;
                return <li key={n} className="flex gap-2 text-sm"><Icon className={cx("mt-0.5 size-4 shrink-0", M.cls)} /><span><b className="text-ink-900">{i.label}.</b> <span className="text-slate-600">{i.detail}</span></span></li>;
              })}</ul>
            )}
            {open && (
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <input className={cx(inputCls, "h-10")} placeholder="Reason for decision (required, saved to audit log)" value={reason[c.id] ?? ""} onChange={(e) => setReason({ ...reason, [c.id]: e.target.value })} />
                <Button variant="dark" onClick={() => decide(c.id, "approved")}>Approve</Button>
                <Button variant="outline" onClick={() => decide(c.id, "rejected")}>Reject</Button>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function Orders() {
  const { d, e, load } = useLoad<any[]>("/api/console/orders");
  if (e) return <ErrorNote msg={e} />;
  if (!d) return <Spinner />;
  if (!d.length) return <Card className="p-10 text-center text-slate-500">No orders yet.</Card>;
  const advance = async (id: string) => { try { await api.post(`/api/orders/${id}/advance`, {}); } catch { /* KYC gate */ } load(); };
  return (
    <Card className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead><tr className="border-b border-slate-200 text-left text-xs text-slate-500"><th className="p-3 font-medium">Order</th><th className="font-medium">Business</th><th className="font-medium">Stage</th><th className="font-medium">KYC</th><th className="font-medium">From ₹/mo</th><th className="font-medium">Expected live</th><th className="font-medium">Delay</th><th /></tr></thead>
        <tbody>{d.map((o) => (
          <tr key={o.id} className="border-b border-slate-100">
            <td className="p-3 font-mono text-xs font-semibold"><a className="underline" href={`/track/${o.order_no}`}>{o.order_no}</a></td>
            <td><div className="font-medium text-ink-900">{o.business_name}</div><div className="text-xs text-slate-500">{o.city}</div></td>
            <td><Badge tone={o.stage === "activated" ? "green" : "slate"}>{o.stage.replace(/_/g, " ")}</Badge></td>
            <td className="text-xs">{o.kyc_status ?? "—"}</td>
            <td>{inr(o.monthly_min)}</td><td>{o.expected_activation}</td>
            <td className="max-w-48 truncate text-xs text-amber-700">{o.delay_reason ?? ""}</td>
            <td className="pr-3 text-right">{o.stage !== "activated" && <Button size="sm" variant="outline" onClick={() => advance(o.id)}><RefreshCw className="size-3.5" />Advance</Button>}</td>
          </tr>
        ))}</tbody>
      </table>
    </Card>
  );
}

function Handoffs({ onChange }: { onChange: () => void }) {
  const { d, e, load } = useLoad<any[]>("/api/console/handoffs");
  if (e) return <ErrorNote msg={e} />;
  if (!d) return <Spinner />;
  if (!d.length) return <Card className="p-10 text-center text-slate-500">No call-back requests. Customers raise them with “Talk to a person”.</Card>;
  const upd = async (id: string, status: string, assigned_to?: string) => { await api.patch(`/api/console/handoffs/${id}`, { status, assigned_to }, C.opts); load(); onChange(); };
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {d.map((h) => (
        <Card key={h.id} className="p-5">
          <div className="flex items-center justify-between"><Badge tone={h.status === "open" ? "red" : h.status === "assigned" ? "amber" : "green"}>{h.status}</Badge><span className="text-xs text-slate-500">{new Date(h.created_at).toLocaleString("en-IN")} · {h.language.toUpperCase()}</span></div>
          <p className="mt-3 font-medium text-ink-900">“{h.reason}”</p>
          <div className="mt-2 text-xs text-slate-500">Step: {h.context?.step ?? "—"}{h.context?.profile?.business_type && ` · ${h.context.profile.business_type}, ${h.context.profile.city ?? ""}, ${h.context.profile.employees ?? "?"} people`}</div>
          {h.assigned_to && <div className="mt-1 text-xs text-slate-600">Assigned to {h.assigned_to}</div>}
          <div className="mt-4 flex gap-2">
            {h.status === "open" && <Button size="sm" variant="dark" onClick={() => upd(h.id, "assigned", "Local channel partner")}>Assign to partner</Button>}
            {h.status !== "resolved" && <Button size="sm" variant="outline" onClick={() => upd(h.id, "resolved", h.assigned_to)}>Mark resolved</Button>}
          </div>
        </Card>
      ))}
    </div>
  );
}
