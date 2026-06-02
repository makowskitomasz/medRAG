"use client";
import "./globals.css";
import { Inter, JetBrains_Mono, Poppins, IBM_Plex_Sans } from "next/font/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { useEffect } from "react";
import { useUIStore } from "@/store";
import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });
const poppins = Poppins({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-poppins" });
const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-plex" });

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

const MESSAGES = { en: enMessages, pl: plMessages };

// Separate component so Zustand hook runs only on client, but provider wraps from the start
function ThemeSync() {
  const { theme, accent, density, font, anim, locale } = useUIStore();
  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute("data-theme", theme);
    html.setAttribute("data-accent", accent);
    html.setAttribute("data-density", density);
    html.setAttribute("data-font", font);
    html.setAttribute("data-anim", anim);
    html.setAttribute("lang", locale);
  }, [theme, accent, density, font, anim, locale]);

  useEffect(() => {
    const existing = document.querySelector("link[rel~='icon']");
    if (existing) existing.remove();
    const link = document.createElement("link");
    link.rel = "icon";
    link.type = "image/svg+xml";
    link.href = "/favicon.svg";
    document.head.appendChild(link);
  }, []);

  return null;
}

function IntlWrapper({ children }: { children: React.ReactNode }) {
  // Read locale from Zustand — on SSR this returns the initial value ("en")
  const locale = useUIStore((s) => s.locale);
  const messages = MESSAGES[locale] ?? enMessages;
  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <ThemeSync />
      {children}
    </NextIntlClientProvider>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="light"
      data-accent="blue"
      data-density="comfortable"
      data-font="inter"
      data-anim="normal"
      className={`${inter.variable} ${mono.variable} ${poppins.variable} ${plex.variable}`}
      style={{ fontFamily: "var(--font)" }}
    >
      <body style={{ margin: 0, padding: 0, height: "100%" }}>
        <QueryClientProvider client={queryClient}>
          <IntlWrapper>
            {children}
          </IntlWrapper>
        </QueryClientProvider>
      </body>
    </html>
  );
}
