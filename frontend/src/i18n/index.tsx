import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en, { type Key } from "./en";
import hi from "./hi";
import ta from "./ta";

// Add a language: create xx.ts with the same keys and register it here.
export const LANGS = { en, hi, ta } as const;
export type Lang = keyof typeof LANGS;

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: Key | string, vars?: Record<string, string | number>) => string };
const I18n = createContext<Ctx>(null!);

function load(): Lang {
  try {
    const v = localStorage.getItem("sync.lang");
    if (v && v in LANGS) return v as Lang;
  } catch { /* storage unavailable */ }
  return "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(load);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("sync.lang", l); } catch { /* ignore */ }
  };
  const t = (k: string, vars?: Record<string, string | number>) => {
    let s: string = (LANGS[lang] as Record<string, string>)[k] ?? (en as Record<string, string>)[k] ?? k;
    if (vars) for (const [a, b] of Object.entries(vars)) s = s.replace(`{${a}}`, String(b));
    return s;
  };
  return <I18n.Provider value={{ lang, setLang, t }}>{children}</I18n.Provider>;
}

export const useT = () => useContext(I18n);
