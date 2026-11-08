const CONSOLE_KEY = "demo-console";

export class ApiError extends Error {
  constructor(message: string, public status: number, public body: unknown) { super(message); }
}

async function req<T>(method: string, path: string, body?: unknown, opts: { console?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (opts.console) headers["X-Console-Key"] = CONSOLE_KEY;
  const r = await fetch(path, {
    method, headers,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    const d = data?.detail;
    const msg = typeof d === "string" ? d : d?.errors?.[0]?.message ?? (Array.isArray(d) ? d[0]?.msg : null) ?? `Request failed (${r.status})`;
    throw new ApiError(msg, r.status, data);
  }
  return data as T;
}

export const api = {
  get: <T,>(p: string, o?: { console?: boolean }) => req<T>("GET", p, undefined, o),
  post: <T,>(p: string, b?: unknown, o?: { console?: boolean }) => req<T>("POST", p, b ?? {}, o),
  put: <T,>(p: string, b: unknown) => req<T>("PUT", p, b),
  patch: <T,>(p: string, b: unknown, o?: { console?: boolean }) => req<T>("PATCH", p, b, o),
};

export const inr = (n: number | null | undefined) =>
  n == null ? "—" : "₹" + Math.round(n).toLocaleString("en-IN");

// ---- shared types (mirrors backend responses)
export type Profile = Record<string, any> & {
  segment?: string; business_type?: string; city?: string; city_tier?: number; employees?: number; sites?: number;
  current_internet?: string; needs?: string[]; has_gstin?: boolean; gstin_status?: string; gstin_masked?: string; budget?: number | null;
};
export type Line = {
  product_id: string; name: string; category: string; unit: string; quantity: number; unit_price_min: number;
  unit_price_max: number; monthly_min: number; monthly_max: number; setup: number; contract_months: number; install_days: number;
};
export type Pricing = {
  lines: Line[]; monthly_min: number; monthly_max: number; setup_total: number; first_bill_min: number;
  longest_commitment_months: number; contract_value_min: number; install_days: number; explanation: string;
};
export type Option = { level: string; pitch: string; items: { product_id: string; quantity: number; reasons: string[] }[]; notes: string[]; pricing: Pricing };
export type Recommendation = { profile: Profile; options: Option[]; recommended: string; budget_note: string | null; ai_summary?: string | null };
export type Product = {
  id: string; category: string; name: string; description: string; unit: string; price_min: number; price_max: number;
  setup_fee: number; min_contract_months: number; city_tiers: number[]; min_employees: number; min_sites: number;
  requires_gstin: boolean; requires_one_of: string[]; install_days: number; target_segments: string[];
};
export type Scenario = { id: string; title: string; focus: string; business_name: string; contact_name: string; contact_role: string; segment: string; city: string; lead_id: string; kyc_pack: string; script: string[] };
export type Check = { code: string; label: string; status: "pass" | "fail" | "review" | "info" | "demo"; detail: string; source: string; document?: string };
export type KycCase = {
  id: string; order_id: string; status: string; decision?: string; decision_reason?: string; missing: string[];
  documents: { id: string; declared_type: string; label: string; detected_type: string | null; ocr_confidence: number; quality: any; purge_after: string; purged: boolean; fields: Record<string, { value: string; conf: number }> }[];
  summary: { status: string; message: string; checks: Check[]; counts: Record<string, number>; disclaimer: string } | null;
};
export type Order = {
  id: string; order_no: string; stage: string; payment_status: string; expected_activation: string; delay_reason: string | null;
  kyc_case_id: string | null; created_at: string; customer: { business_name: string; contact_name: string; city: string };
  quote: { pricing: Pricing; install_days: number; profile: Profile }; events: { stage: string; note: string; actor: string; at: string }[];
  timeline: { stage: string; label: string; expected: string; state: "done" | "current" | "upcoming" }[];
  pending_actions: string[]; kyc: { id: string; status: string } | null; consents?: any[];
};
