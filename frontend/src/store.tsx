import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Profile } from "./api";

// One journey per browser tab: the IDs that tie advisor, quote, order and KYC together.
export type Journey = {
  sessionId?: string; scenarioId?: string; kycPack?: string; profile?: Profile;
  level?: string; items?: Record<string, number>; quoteId?: string; orderId?: string; orderNo?: string; caseId?: string;
  businessName?: string; contactName?: string; contactRole?: string;
};
type Ctx = { j: Journey; set: (p: Partial<Journey>) => void; reset: () => void };
const Store = createContext<Ctx>(null!);
const KEY = "sync.journey";

function load(): Journey {
  try { return JSON.parse(sessionStorage.getItem(KEY) || "{}"); } catch { return {}; }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [j, setJ] = useState<Journey>(load);
  useEffect(() => { try { sessionStorage.setItem(KEY, JSON.stringify(j)); } catch { /* ignore */ } }, [j]);
  return (
    <Store.Provider value={{ j, set: (p) => setJ((s) => ({ ...s, ...p })), reset: () => setJ({}) }}>
      {children}
    </Store.Provider>
  );
}
export const useJourney = () => useContext(Store);
