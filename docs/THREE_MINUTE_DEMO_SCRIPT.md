# Three-minute demo script

## Pre-flight checklist (5 minutes before recording)

1. Build and start: `npm --prefix frontend run build`, then `python3 -m uvicorn app.main:app --app-dir backend --port 8000`.
2. Seed the console: `python3 backend/seed_demo.py`. This resets all demo data, then creates the K01 travel agency (action required), the K10 Kaveri Stays case (manual review) and one Hindi call-back. Re-run it before every take; rehearsals leave orders behind.
3. Browser: Chrome, window 1440×900, zoom 100%, bookmarks bar hidden, notifications off. Open two tabs: **Tab 1** `http://localhost:8000` and **Tab 2** `http://localhost:8000/console`.
4. In Tab 1 open DevTools once → Application → Session storage → clear it (or use a fresh incognito window), so the journey starts empty. Language: English.
5. Warm the OCR cache with one throwaway run of the clinic journey, then run step 2 again. Without the warm-up, loading K02 takes about 1 second instead of instantly.
6. Recorder: 1080p, system audio off, mic on. Keep the cursor still while you talk.

Measured response times on this machine: advisor playback 5.4 s, plans 0.2 s, quote 0.3 s, checkout 0.3 s, load K02 1.1 s (cold OCR), verify 0.2 s, tracker 1.4 s. Nothing needs a cut.

## Script

| Time | Tab / screen | Say | Do |
|---|---|---|---|
| 0:00–0:15 | 1 · Landing | "Accel Business turns only 7.4% of small-business leads into customers. It takes 17.6 days and ₹15,053 to win each one. Owners drop out because nobody visits, quotes are slow and confusing, and the paperwork is painful. SYNC fixes that in one sitting." | Slowly hover the four stat cards |
| 0:15–0:45 | 1 · Advisor | "This is Harmony Dental Care, a real record from the dataset. The owner types the way they talk, in English, Hindi or Tamil, and every fact in a sentence is picked up." | Scroll to *Demo businesses* → Dental clinic → *Run this journey* → *Play demo conversation* (5 s). Point at the profile card filling in and the masked, registry-checked GSTIN |
| 0:45–1:05 | 1 · Plans | "Three plans built only from catalogue IDs. Each product says why it is there, with evidence like '41% of similar offices chose it'. Anything we can't sell is listed with the rule. We recommend Growth, not the most expensive plan that fits the budget." | *See my plans*. Hover a reason; open *Not included* on Advanced |
| 1:05–1:25 | 1 · Quote | "One monthly price: the catalogue minimum, with the maximum shown and no invented discount. If I remove the fibre line, the backend blocks Cloud Telephony, because it needs an internet connection." | Growth → *Customise this plan*. Click the bin on Biz Fibre 300 → red error → add Biz Fibre 300 back from *Add products* → *Accept quote* |
| 1:25–1:35 | 1 · Checkout + Consent | "We ask only what we need. Then a DPDP consent screen covering what we collect, why, who sees it, how long we keep it, and how to withdraw." | *Place order*. Tick the two required boxes → *I agree* |
| 1:35–2:05 | 1 · Smart KYC | "Four photos. Local OCR strips the specimen watermark, straightens this tilted GST certificate by 7 degrees, and checks the GSTIN checksum, registry status, names, address and a 90-day bill. Every result says where the evidence came from, and that no real government system was called." | Pack is pre-selected as K02 → *Load* → *Verify documents* → scroll the checks slowly; pause on "Straightened 7°" and the disclaimer |
| 2:05–2:20 | 1 · Tracker | "No more calling to chase. Every step has an expected date, and the slowest product sets the activation date." | *Go to order tracker* → *Simulate next step* twice |
| 2:20–2:40 | 2 · Console → KYC exceptions | "When documents don't line up, nothing is silently approved. This travel agency's GSTIN is cancelled and its Udyam number is blank, so the owner is told exactly what to fix. Here, the signatory isn't the declared owner, so it goes to a person, who must give a reason that is audited." | Switch to Tab 2 → *KYC exceptions*. Point at Vindhya Tours, then Kaveri Stays |
| 2:40–2:55 | 2 · Overview → Lead priority | "For sales and partners: the true funnel, acquisition cost calculated correctly, and why leads drop. 1,432 of those drops are removed by design, and 15% of past bundles broke catalogue rules. The priority queue tells partners whom to call and why, with every point explained." | *Acquisition analytics* (scroll to drop reasons and the compliance box) → *Lead priority* → expand the top row |
| 2:55–3:00 | — | "SYNC Business: from discovery to activation in one seamless journey, with the field force and partners in the loop." | Hold on the console |

## If something goes wrong

- **Advisor stalls** (should not happen offline): click *Start over* (↻) and press *Play demo conversation* again.
- **"Tell the advisor about your business first"** on Plans: session storage was stale. Go back to the Landing page and re-run the scenario.
- **The console looks empty or has extra rehearsal orders**: stop, re-run `python3 backend/seed_demo.py`, and restart the take.
- **Over time**: drop the quote dependency demo (1:05–1:25) and simply say "edit quantities live", then accept.

## Optional 10-second cutaway (if time allows in an edit)

Switch the language to हिन्दी or தமிழ் on the Advisor to show that the whole interface changes. Type `मेरी किराना दुकान है लुधियाना में` and the profile card fills in.
