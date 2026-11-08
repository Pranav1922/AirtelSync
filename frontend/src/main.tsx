import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { I18nProvider } from "./i18n";
import { StoreProvider } from "./store";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import Landing from "./pages/Landing";
import Advisor from "./pages/Advisor";
import Plans from "./pages/Plans";
import Quote from "./pages/Quote";
import Checkout from "./pages/Checkout";
import Consent from "./pages/Consent";
import Kyc from "./pages/Kyc";
import Track from "./pages/Track";

const Console = lazy(() => import("./pages/Console")); // keeps chart code out of the customer bundle

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <StoreProvider>
        <BrowserRouter>
          <Layout>
            <Suspense fallback={<div className="mx-auto max-w-6xl px-4"><Spinner /></div>}>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/advisor" element={<Advisor />} />
                <Route path="/plans" element={<Plans />} />
                <Route path="/quote" element={<Quote />} />
                <Route path="/checkout" element={<Checkout />} />
                <Route path="/consent" element={<Consent />} />
                <Route path="/kyc" element={<Kyc />} />
                <Route path="/track" element={<Track />} />
                <Route path="/track/:no" element={<Track />} />
                <Route path="/console" element={<Console />} />
                <Route path="*" element={<Landing />} />
              </Routes>
            </Suspense>
          </Layout>
        </BrowserRouter>
      </StoreProvider>
    </I18nProvider>
  </StrictMode>,
);
