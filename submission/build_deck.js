// Builds submission/SYNC_Business_Case.pptx on the supplied template backgrounds.
// The original "Submission Template_Sync.pptx" is never modified; its two background
// images were extracted to submission/assets/. Run: node submission/build_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");

const A = (f) => path.join(__dirname, "assets", f);
const INK = "0B1220", RED = "E11D2E", SLATE = "475569", MUTED = "64748B", LIGHT = "F1F5F9", WHITE = "FFFFFF", GREEN = "047857";
const FONT = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in, same aspect as the template
pres.title = "SYNC Business - Intelligent MSME Onboarding";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({ title: "COVER", background: { path: A("template_cover.jpg") } });
pres.defineSlideMaster({
  title: "CONTENT",
  background: { path: A("template_content.jpg") },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.72, w: 9, h: 0.55, fontSize: 24, bold: true, color: INK, fontFace: FONT, margin: 0, valign: "middle" }, text: "" } },
    { text: { text: "Synthetic data · Accel Business is fictional · Observed = dataset, Target = proposal", options: { x: 0.5, y: 5.2, w: 6.2, h: 0.25, fontSize: 8, color: MUTED, fontFace: FONT, margin: 0 } } },
  ],
  slideNumber: { x: 0.5, y: 4.95, w: 0.4, h: 0.22, fontSize: 8, color: MUTED, fontFace: FONT },
});

const T = (s, text, o) => s.addText(text, { isTextBox: true, fontFace: FONT, margin: 0, color: INK, ...o });
const card = (s, x, y, w, h, fill = LIGHT) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.08 });
const sub = (s, text) => T(s, text, { x: 0.5, y: 1.27, w: 9, h: 0.3, fontSize: 13, color: SLATE });
const stat = (s, x, y, w, big, label, color = INK) => {
  card(s, x, y, w, 1.15);
  T(s, big, { x: x + 0.15, y: y + 0.12, w: w - 0.3, h: 0.55, fontSize: 30, bold: true, color });
  T(s, label, { x: x + 0.15, y: y + 0.68, w: w - 0.3, h: 0.4, fontSize: 11, color: SLATE });
};
const bullets = (s, items, o) => T(s, items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })), { fontSize: 13, paraSpaceAfter: 6, valign: "top", ...o });
const table = (s, rows, o) => s.addTable(rows.map((r, i) => r.map((c) => ({
  text: String(c), options: { bold: i === 0, color: i === 0 ? WHITE : INK, fill: { color: i === 0 ? INK : i % 2 ? WHITE : LIGHT }, fontSize: o.fontSize ?? 11, fontFace: FONT, valign: "middle", margin: [2, 5, 2, 5] },
}))), { border: { type: "solid", pt: 0.5, color: "E2E8F0" }, ...o });

// 1 Cover
{
  const s = pres.addSlide({ masterName: "COVER" });
  T(s, "SYNC Business", { x: 0.65, y: 2.65, w: 4.6, h: 0.55, fontSize: 32, bold: true, color: WHITE });
  T(s, "From business discovery to digital activation in one seamless journey", { x: 0.65, y: 3.2, w: 4.3, h: 0.65, fontSize: 15, color: "E2E8F0" });
  T(s, "Enterprise Track A · Project Udyam Digital · Business case", { x: 0.65, y: 4.05, w: 4.5, h: 0.3, fontSize: 11, color: "CBD5E1" });
  s.addNotes("SYNC Business: an intelligent MSME acquisition and onboarding platform for the fictional operator Accel Business.");
}

// 2 Problem and opportunity
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Only 7.4% of small-business leads ever go live", { placeholder: "title" });
  sub(s, "Observed in 5,000 synthetic leads, Apr–Jun 2026");
  [["7.4%", "lead → activation (368 of 5,000)", RED], ["17.6 days", "lead to live service; 3 status-chasing calls", INK],
   ["₹15,053", "blended CAC = ₹55.4 L spend ÷ 368 (not ₹5,385)", INK], ["43.6%", "needs assessed → quote accepted: the steepest drop", RED]]
    .forEach(([b, l, c], i) => stat(s, 0.5 + i * 2.27, 1.7, 2.12, b, l, c));
  T(s, "Why they drop", { x: 0.5, y: 3.05, w: 4, h: 0.3, fontSize: 14, bold: true });
  bullets(s, ["827 visits never happened: owner had no time (531) or sales never scheduled (296)",
    "385 quotes too slow or too complex; 414 found the price too high",
    "220 lost in paperwork: missing GST/Udyam, long forms, mismatched details"], { x: 0.5, y: 3.35, w: 4.6, h: 1.5, fontSize: 12 });
  card(s, 5.4, 3.05, 4.1, 1.75, "FFF1F2");
  T(s, "The opportunity", { x: 5.6, y: 3.15, w: 3.7, h: 0.3, fontSize: 14, bold: true, color: "A10D25" });
  T(s, "1,432 drops (31%) are caused by steps a digital journey removes outright. And 56 of 368 activated bundles broke catalogue rules, 22 on a cancelled or suspended GSTIN.", { x: 5.6, y: 3.48, w: 3.75, h: 1.25, fontSize: 12, color: INK, valign: "top" });
}

// 3 Segmentation
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Prioritise professional offices, sell micro self-service", { placeholder: "title" });
  sub(s, "Observed segment economics → our priority and motion");
  table(s, [
    ["Priority", "Segment", "Leads", "Lead→live", "Blended CAC", "Median ₹/mo", "6-m churn", "Motion"],
    ["1", "Professional offices", "1,247", "11.1%", "₹10,695", "₹6,575", "13.8%", "Fully digital"],
    ["2", "Small multi-site", "755", "11.0%", "₹15,614", "₹28,080", "10.8%", "Digital + field survey"],
    ["3", "Micro retail & services", "2,709", "4.1%", "₹20,007", "₹2,470", "22.7%", "Self-service only"],
    ["4", "Small manufacturers", "289", "12.8%", "₹15,324", "₹15,910", "8.1%", "Digital + install engineer"],
  ], { x: 0.5, y: 1.7, w: 9, colW: [0.7, 1.9, 0.7, 0.9, 1.05, 1.1, 0.9, 1.75], fontSize: 11 });
  [["Professional", "Largest non-micro pool, lowest CAC, losses at quote and KYC: exactly what SYNC fixes."],
   ["Micro", "Field-selling a ₹2,470 bundle at ₹20,007 CAC destroys value. Essential plan, non-GST products, pay setup on first bill."],
   ["GST matters", "With GSTIN 9.6% go live vs 2.0% without; 10 of 25 products need an active GSTIN, so we check it in the chat."]]
    .forEach(([h, b], i) => { card(s, 0.5 + i * 3.05, 3.55, 2.9, 1.3); T(s, h, { x: 0.65 + i * 3.05, y: 3.63, w: 2.6, h: 0.3, fontSize: 13, bold: true, color: RED }); T(s, b, { x: 0.65 + i * 3.05, y: 3.93, w: 2.65, h: 0.88, fontSize: 11, color: SLATE, valign: "top" }); });
}

// 4 Our solution
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("One journey on the phone, in the owner's language", { placeholder: "title" });
  sub(s, "Working prototype: customer app + Intelligence Console, English · हिन्दी · தமிழ்");
  const steps = [["Advisor", "5 questions, free text in EN/HI/TA"], ["Plans", "3 bundles of real catalogue IDs, a reason per product"], ["Quote", "One monthly price, min–max, no hidden discount"],
    ["Checkout", "Name, signatory, partner code"], ["Smart KYC", "4 photos, OCR + mock registry checks in seconds"], ["Tracker", "Expected date for every step"]];
  steps.forEach(([h, b], i) => {
    const x = 0.5 + i * 1.52;
    s.addShape(pres.shapes.OVAL, { x: x + 0.47, y: 1.75, w: 0.5, h: 0.5, fill: { color: i === 4 ? RED : INK }, line: { color: i === 4 ? RED : INK } });
    T(s, String(i + 1), { x: x + 0.47, y: 1.75, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle" });
    T(s, h, { x, y: 2.35, w: 1.44, h: 0.3, fontSize: 13, bold: true, align: "center" });
    T(s, b, { x, y: 2.65, w: 1.44, h: 0.75, fontSize: 10.5, color: SLATE, align: "center", valign: "top" });
  });
  card(s, 0.5, 3.6, 4.4, 1.25);
  T(s, "Human help everywhere", { x: 0.65, y: 3.68, w: 4.1, h: 0.3, fontSize: 13, bold: true });
  T(s, "“Talk to a person” creates a callback with the advisor profile and step, routed to the local partner or KYC desk.", { x: 0.65, y: 3.98, w: 4.1, h: 0.8, fontSize: 11, color: SLATE, valign: "top" });
  card(s, 5.1, 3.6, 4.4, 1.25, INK);
  T(s, "SYNC Intelligence Console", { x: 5.25, y: 3.68, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: WHITE });
  T(s, "True funnel and CAC, drop-off levers, KYC exception queue, orders, callbacks and an explainable lead-priority queue for field and partners.", { x: 5.25, y: 3.98, w: 4.1, h: 0.8, fontSize: 11, color: "CBD5E1", valign: "top" });
}

// 5 AI discovery and recommendations
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Explainable recommendations grounded in the catalogue", { placeholder: "title" });
  sub(s, "Deterministic engine decides; an optional LLM only phrases and parses");
  bullets(s, [
    "Understands every fact in one message: “dental clinic in Kochi with 12 staff” fills type, segment, city, tier, size",
    "Hard rules on the backend: city tier, min staff, min sites, active GSTIN, requires-one-of dependencies",
    "Essential = what you asked for at the lowest price; Growth adds the segment's most-attached tools; Advanced adds resilience",
    "Quantities from historical bundles (e.g. 2 CCTV per site); evidence in each reason",
    "Budget-aware: recommends Growth at most, never the priciest plan that fits",
    "Runs fully offline; no paid API needed",
  ], { x: 0.5, y: 1.7, w: 4.8, h: 3.2, fontSize: 12 });
  card(s, 5.55, 1.7, 3.95, 3.15);
  T(s, "Harmony Dental Care · Kolkata · 5 staff", { x: 5.7, y: 1.78, w: 3.7, h: 0.28, fontSize: 11, color: MUTED });
  T(s, "Growth  ₹5,868 – ₹7,993 /month", { x: 5.7, y: 2.06, w: 3.7, h: 0.35, fontSize: 15, bold: true, color: RED });
  table(s, [["Product", "Qty", "Why"], ["P02 Biz Fibre 300", "1", "Main line, 1 site"], ["P08 Postpaid 599", "2", "Team lines, one bill"], ["P16 Cloud Email", "3", "Asked for clinic email"],
    ["P20 Endpoint", "3", "Asked for antivirus"], ["P12 Cloud Telephony", "2", "Asked for call recording"], ["P17 Backup 1 TB", "1", "41% of similar offices"]],
  { x: 5.7, y: 2.45, w: 3.65, colW: [1.45, 0.4, 1.8], fontSize: 10 });
}

// 6 Smart KYC and privacy
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Smart KYC: instant, explained and honest", { placeholder: "title" });
  sub(s, "Local OCR + mock GSTIN/Udyam registries; no real government system is called");
  bullets(s, [
    "Watermark removal, 7° deskew, blur detection, per-field OCR confidence",
    "GSTIN checksum with OCR glyph repair (I↔T, J↔I) only when checksum and registry agree",
    "Registry status, names, address, 90-day bill (ref. 15 Jul 2026), signatory, completeness",
    "Uncertain → manual review with reason; every override audited",
  ], { x: 0.5, y: 1.7, w: 4.5, h: 1.8, fontSize: 12 });
  table(s, [["Pack", "Found by inspection", "Result"], ["K03 K08 K09 K12", "Clean", "Passed demo"], ["K02", "Tilted scan", "Deskewed, passed"],
    ["K01", "GSTIN cancelled; Udyam no. blank", "Action required"], ["K04", "Blurred GST certificate", "Manual review"], ["K05", "Udyam certificate missing", "Action required"],
    ["K06", "GSTIN digit altered (checksum)", "Action required"], ["K07", "Legal vs trade name mismatch", "Action required"], ["K10", "Signatory ≠ declared owner", "Manual review"],
    ["K11", "Bill 257 days old", "Action required"]], { x: 5.2, y: 1.7, w: 4.3, colW: [1.1, 1.95, 1.25], fontSize: 9.5 });
  card(s, 0.5, 3.6, 4.5, 1.25, "ECFDF5");
  T(s, "DPDP-first by design", { x: 0.65, y: 3.68, w: 4.2, h: 0.3, fontSize: 13, bold: true, color: GREEN });
  T(s, "Purpose-wise consent before upload · minimum data · identifiers masked in UI and logs · images deleted after 30 days or on withdrawal.", { x: 0.65, y: 3.98, w: 4.2, h: 0.8, fontSize: 11, color: INK, valign: "top" });
}

// 7 Architecture
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Architecture and technology", { placeholder: "title" });
  sub(s, "React 19 · TypeScript · Tailwind · FastAPI · pandas · SQLite · Tesseract · 45 automated tests");
  const box = (x, y, w, h, title, body, fill = LIGHT, tc = INK) => { card(s, x, y, w, h, fill); T(s, title, { x: x + 0.12, y: y + 0.08, w: w - 0.24, h: 0.28, fontSize: 12, bold: true, color: tc }); T(s, body, { x: x + 0.12, y: y + 0.38, w: w - 0.24, h: h - 0.45, fontSize: 10, color: tc === WHITE ? "CBD5E1" : SLATE, valign: "top" }); };
  box(0.5, 1.7, 2.2, 1.35, "Customer app", "Advisor, plans, quote, checkout, consent, KYC, tracker. Mobile-first, EN/HI/TA files.");
  box(0.5, 3.2, 2.2, 1.35, "Intelligence Console", "Analytics, lead priority, KYC queue, orders, callbacks. Key-protected.");
  box(3.0, 1.7, 3.0, 2.85, "SYNC API (FastAPI)", "advisor · recommend · quote · orders · consent · KYC pipeline · analytics · lead score · optional LLM. Prices and eligibility re-validated server-side at checkout. Identifier masking log filter.", INK, WHITE);
  box(6.3, 1.7, 3.2, 0.85, "Supplied CSVs", "Catalogue, 5,000 leads, GSTIN + Udyam mock registries");
  box(6.3, 2.65, 3.2, 0.85, "SQLite", "Quotes, orders, events, consent, KYC, audit log");
  box(6.3, 3.6, 3.2, 0.95, "Future adapters (not connected)", "GSP / Udyam API, DigiLocker, e-sign, payments, field ops", "FFF1F2");
  s.addShape(pres.shapes.LINE, { x: 2.7, y: 2.37, w: 0.3, h: 0, line: { color: MUTED, width: 1.5, endArrowType: "triangle" } });
  s.addShape(pres.shapes.LINE, { x: 2.7, y: 3.87, w: 0.3, h: 0, line: { color: MUTED, width: 1.5, endArrowType: "triangle" } });
  s.addShape(pres.shapes.LINE, { x: 6.0, y: 3.1, w: 0.3, h: 0, line: { color: MUTED, width: 1.5, endArrowType: "triangle" } });
}

// 8 Commercial model and impact
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Commercial model and expected impact", { placeholder: "title" });
  sub(s, "Catalogue prices only · setup on first bill option · pilot targets are proposals");
  s.addChart(pres.charts.BAR, [{ name: "Activations per quarter", labels: ["Observed", "Pilot target"], values: [368, 600] }], {
    x: 0.5, y: 1.65, w: 4.3, h: 3.2, barDir: "col", chartColors: [INK, RED], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "Activations from 5,000 leads / quarter", titleFontSize: 12, titleFontFace: "+mn-lt", showLegend: false,
    catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, varyColors: true,
  });
  table(s, [["Metric", "Observed", "Target"], ["Lead → activation", "7.4%", "12%"], ["New MRR / quarterly cohort", "₹45.4 L", "₹74.1 L"], ["Acquisition spend / quarter", "₹55.4 L", "≈ ₹43.5 L"],
    ["Blended CAC", "₹15,053", "≤ ₹9,000"], ["Days to activate", "17.6", "≤ 9"]], { x: 5.1, y: 1.7, w: 4.4, colW: [2.2, 1.1, 1.1], fontSize: 11 });
  T(s, "Assumes unchanged lead mix and mean bundle (₹12,351/mo); 894 micro field visits (₹1,601 each) move to digital at web-form cost (₹274). Upside ≈ ₹3.4 cr ARR per quarter of leads if targets hold.", { x: 5.1, y: 3.95, w: 4.4, h: 0.9, fontSize: 10.5, color: SLATE, valign: "top" });
}

// 9 GTM and roadmap
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Go-to-market: digital first, field force and partners in the loop", { placeholder: "title" });
  sub(s, "The journey adds to the sales channel instead of competing with it");
  [["Partners", "Partner code at checkout gives credit for digital orders; consented install leads; callback queue in their language."],
   ["Field sales", "Freed from micro visits; owns multi-site surveys, leased-line installs and high-value manufacturers from the priority queue."],
   ["Digital", "Website and WhatsApp leads land in the advisor instantly instead of waiting for a callback (only 41–55% are contacted today)."]]
    .forEach(([h, b], i) => { card(s, 0.5 + i * 3.05, 1.7, 2.9, 1.45); T(s, h, { x: 0.65 + i * 3.05, y: 1.78, w: 2.6, h: 0.3, fontSize: 13, bold: true, color: RED }); T(s, b, { x: 0.65 + i * 3.05, y: 2.08, w: 2.65, h: 1.0, fontSize: 11, color: SLATE, valign: "top" }); });
  table(s, [["Phase", "When", "Scope", "Exit criteria"],
    ["0 Harden", "6 weeks", "Real GSP/Udyam/DigiLocker/e-sign/payment adapters, SSO console", "Security + DPDP legal review"],
    ["1 Pilot", "3 months", "4 cities, professional + micro self-serve, EN/HI/TA, A/B vs control", "Metric deltas on targets"],
    ["2 Expand", "3 months", "Multi-site + manufacturers, WhatsApp front end, 4 more languages", "CAC and days targets met"],
    ["3 Scale", "Then", "National rollout, partner portal, voice advisor", ""]], { x: 0.5, y: 3.3, w: 9, colW: [1.1, 0.9, 4.4, 2.6], fontSize: 10.5 });
}

// 10 Metrics, risks, conclusion
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText("Success metrics, risks and the ask", { placeholder: "title" });
  sub(s, "Baselines from the dataset; targets are pilot proposals");
  table(s, [["Metric", "Baseline", "Target"], ["Lead → activation", "7.4%", "12%"], ["Lead → activation time", "17.6 d", "≤ 9 d"], ["Blended CAC", "₹15,053", "≤ ₹9,000"],
    ["Needs → quote accepted", "43.6%", "60%"], ["6-month churn", "15.2%", "≤ 11%"]], { x: 0.5, y: 1.7, w: 4.3, colW: [2.1, 1.1, 1.1], fontSize: 11 });
  table(s, [["Risk", "Mitigation"], ["OCR errors on real photos", "Field confidence, checksum, manual review"], ["Channel conflict", "Partner codes, priority queue to partners"],
    ["Price range uncertainty", "Min headline + max ceiling, no hidden discount"], ["Model bias", "Protected proxies excluded, human decides"], ["Tier-2 install capacity", "Dates up front, AirFiber fallback"]],
  { x: 5.1, y: 1.7, w: 4.4, colW: [1.8, 2.6], fontSize: 10.5 });
  card(s, 0.5, 4.0, 9, 0.85, INK);
  T(s, "Ask: a 3-month, 4-city A/B pilot of SYNC Business with professional offices and micro self-service, with field and partner teams on the console.", { x: 0.7, y: 4.07, w: 8.6, h: 0.72, fontSize: 13, bold: true, color: WHITE, valign: "middle" });
}

pres.writeFile({ fileName: path.join(__dirname, "SYNC_Business_Case.pptx") }).then((f) => console.log("wrote", f));
