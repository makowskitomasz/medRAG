# Handoff: medRAG — frontend produkcyjny

> **Dla developera / Claude Code:** Pliki w folderze `reference/` to **prototyp designerski w HTML + React (Babel in‑browser)**. Nie kopiuj ich 1:1 do produkcji. Twoje zadanie: **odtworzyć ten design w produkcyjnym stacku** (rekomendacja niżej), używając prawdziwego API backendu (specyfikacja: `API_CONTRACT.md`).

---

## 1. Co to jest

medRAG to **pacjencki asystent medyczny RAG** w języku polskim. Użytkownik zadaje pytanie po polsku, system przeszukuje jego prywatne dokumenty medyczne (PDF: wytyczne, ChPL, wyniki badań) i odpowiada **z cytatami źródeł** — każde zdanie ma odnośnik `[1]`, `[2]` do konkretnego fragmentu PDF z numerem strony i procentem trafności.

Cztery tryby AI: **Vanilla** (szybkie wyszukiwanie), **HyDE** (pogłębione), **Self‑Reflection** (AI sprawdza się sam), **Multi‑Agent** (Badacz + Krytyk + Redaktor).

## 2. Fidelity

**Hi‑fi.** Mockupy są pixel‑perfect — kolory, typografia, spacing, animacje są ostateczne. Odtwórz je dokładnie, korzystając z bibliotek wskazanego stacku.

## 3. Rekomendowany stack docelowy

| Warstwa            | Wybór                                       | Uzasadnienie                                                                          |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------- |
| Framework          | **Next.js 14+ (App Router) + TypeScript**   | SSR dla login/landing, RSC dla list, routing, middleware do auth                      |
| Styling            | **Tailwind CSS** + CSS variables (z tokens) | Tokens już są w `reference/styles.css` — przenieś 1:1 do `globals.css` + tailwind config |
| Komponenty UI      | **shadcn/ui** (Radix pod spodem)            | Dialog, Popover, DropdownMenu, Tooltip, Collapsible, Tabs                              |
| Ikony              | **lucide-react**                            | Już pasują do designu (linijka 1.5px, 14–16px)                                         |
| State servera      | **TanStack Query v5**                       | Cache projektów, rozmów, dokumentów                                                   |
| State lokalny      | **Zustand**                                 | Tweaks (theme/accent/density), aktywny projekt, sidebar collapsed                     |
| Streaming          | **`fetch` + `ReadableStream`** (nie EventSource — bo POST z body) | Patrz `API_CONTRACT.md` § 4                                                           |
| Forms              | **react-hook-form + zod**                   | Login, edycja profilu, dodawanie dokumentów                                          |
| Auth (frontend)    | **NextAuth (Credentials provider)** lub własny JWT w httpOnly cookie | Bez Google / IKP — sam login + hasło                                                  |
| Markdown w odpowiedzi | **react-markdown** + custom renderer dla `[N]` | W prototypie ręczny parser w `chat.jsx` — w produkcji użyj react-markdown z `rehype` |
| Persystencja Tweaks | `localStorage`                             | Identycznie jak w prototypie                                                          |
| Testy              | Vitest + Playwright (e2e na flow login → zapytanie → cytat) |                                                                                       |

> **Alternatywa:** Vite + React Router 6 jeśli SSR nie jest potrzebny. Cała reszta stacku zostaje.

## 4. Struktura plików (proponowana)

```
app/
├── (auth)/
│   └── login/page.tsx
├── (app)/
│   ├── layout.tsx                 # Sidebar + topbar shell
│   ├── chat/
│   │   ├── page.tsx               # Nowa rozmowa
│   │   └── [conversationId]/page.tsx
│   ├── history/page.tsx
│   └── admin/
│       ├── projects/page.tsx
│       └── documents/page.tsx
├── api/                           # Tylko proxy do backendu — jeśli potrzebne
└── globals.css                    # Tokens z reference/styles.css

components/
├── chat/
│   ├── ChatThread.tsx
│   ├── ChatComposer.tsx
│   ├── ModeSelector.tsx
│   ├── MessageUser.tsx
│   ├── MessageAi.tsx
│   ├── SearchingState.tsx
│   ├── ReflectPanel.tsx
│   ├── MultiAgentPanel.tsx
│   └── citations/
│       ├── CitationsCards.tsx     # ← DEFAULT layout
│       ├── CitationsSidebar.tsx
│       └── CitationsInline.tsx
├── sidebar/
│   ├── AppSidebar.tsx
│   ├── ProjectSwitcher.tsx
│   └── ConversationList.tsx
└── ui/                            # shadcn/ui

hooks/
├── useChatStream.ts               # SSE/stream → phase machine
├── useTweaks.ts
└── useProjects.ts

lib/
├── api/
│   ├── client.ts                  # fetch wrapper z auth
│   ├── auth.ts
│   ├── projects.ts
│   ├── conversations.ts
│   └── stream.ts                  # parser strumienia
├── tokens.ts                      # Wartości designu (TS)
└── types.ts                       # Project, Conversation, Citation, AiMode

store/
└── tweaks.ts                      # Zustand
```

## 5. Ekrany (każdy = jedna trasa)

### 5.1 `/login` — Logowanie
**Plik referencyjny:** `reference/screens/login.jsx` + `reference/screens/login.css`

- Layout dwukolumnowy: **lewy panel** (brand + 3 feature cards + dekoracyjna grid SVG); **prawy** (form, max-width ~440px, wycentrowany)
- Pola: `email` (required, email), `password` (required, min 8), checkbox "Zostań zalogowana", link "Zapomniałam hasła"
- **Brak** logowania przez Google ani IKP — tylko email + hasło
- Po submit: `POST /auth/login`, przy sukcesie zapisz token w **httpOnly cookie** (preferowane) lub `localStorage`, redirect do `/chat`
- Stan loading: spinner w przycisku + tekst "Sprawdzamy..." (900ms minimum żeby user widział feedback)
- "Pomiń login (tryb demo)" — usuń w produkcji **lub** zostaw gated env-flagiem `NEXT_PUBLIC_DEMO_MODE=true`

### 5.2 `/chat/[id]` — Główny ekran (najważniejszy)
**Plik referencyjny:** `reference/screens/chat.jsx` + `reference/screens/chat.css` + `reference/components/*`

Grid 3-strefowy: **sidebar (280px, zwijany do 64px)** | **wątek** | (opcjonalna sidebar cytatów, jeśli tweak === sidebar)

**Sidebar (lewy):**
- Logo medRAG + przycisk collapse
- Project switcher (dropdown z listą projektów)
- "Nowa rozmowa" — primary button + skrót ⌘N
- Search w rozmowach + skrót ⌘K
- Lista rozmów pogrupowana po `group` (Dzisiaj / Wczoraj / Ten tydzień / Wcześniej) — `GET /conversations`
- Stopka z avatarem usera + linkiem do ustawień

**Top bar:**
- Breadcrumb: [projekt] › [tytuł rozmowy]
- Toggle theme (light/dark)
- Settings (otwiera Tweaks panel — patrz §7)

**Wątek (środkowa kolumna, max-width 880px, scroll):**
- Banner disclaimer "medRAG nie zastępuje konsultacji z lekarzem"
- Wiadomość usera (right-aligned, accent-soft bubble)
- Wiadomość AI z fazami (state machine — patrz §6)
  - Header: avatar + nazwa + mode pill + status czasu
  - Faza `searching`: `<SearchingState>` z animowanym skanerem dokumentów (progress 0→1)
  - Faza `thinking` (tylko Reflect/Multi): `<ReflectPanel>` lub `<MultiAgentPanel>` — kroki dochodzące jeden po drugim
  - Faza `streaming`: tekst odpowiedzi pojawia się token-po-tokenie, blinking cursor na końcu
  - Faza `done`: pełna odpowiedź + akcje (Kopiuj / Wygeneruj ponownie / 👍 / 👎) + follow-up chips
- Cytaty pod odpowiedzią (domyślnie **cards**, 2 kolumny) — `<CitationsCards>`
- **Auto-collapse:** po `phase === "done"`, panel rozumowania i sekcja cytatów same się zwijają. Klik w nagłówek rozwija z powrotem.

**Composer (dół):**
- `<ModeSelector>` (segmented control: Vanilla / HyDE / Reflect / Multi) z hover popoverem opisującym tryb
- Textarea (auto-grow do 200px), Enter = wyślij, Shift+Enter = nowa linia
- Tools: ikonka załącz dokument, dyktuj
- Chip z aktywnym projektem
- Send button → uruchamia stream. Podczas generowania zamienia się w stop button (`POST /conversations/:id/cancel`)

### 5.3 `/history` — Pełna historia rozmów
**Plik referencyjny:** `reference/screens/history.jsx` + `reference/screens/history-admin.css`

Lista wszystkich rozmów z filtrami (projekt, tryb AI, data), search, sortowanie. Każdy wiersz → klik → `/chat/[id]`.

### 5.4 `/admin/projects` + `/admin/documents` — Zarządzanie
**Plik referencyjny:** `reference/screens/admin.jsx`

- Lista projektów (CRUD)
- Lista dokumentów: nazwa, rozmiar, strony, status (`indexed` / `processing` / `pending` / `failed`), pasek postępu dla processing
- Upload PDF → `POST /documents` → backend ingestuje async, frontend pollinguje status albo subskrybuje WS

## 6. State machine wiadomości AI (KRYTYCZNE)

To serce ekranu. W prototypie jest zasymulowana w `chat.jsx` przez `setTimeout`. W produkcji **przepisz na hook `useChatStream`** który mapuje eventy z `POST /conversations/:id/messages` (stream) na ten sam state:

```ts
type Phase = "idle" | "searching" | "thinking" | "streaming" | "done"

interface ChatStreamState {
  phase: Phase
  searchProgress: number           // 0..1, dla SearchingState
  scannedDocs: ScannedDoc[]        // dla SearchingState
  thinkSteps: ThinkStep[]          // dla ReflectPanel/MultiAgentPanel
  activeStep: number               // który krok się dzieje teraz
  streamedText: string             // tekst odpowiedzi (rośnie token po tokenie)
  citationsRevealed: number        // ile cytatów już można pokazać (= max [N] w streamedText)
  citations: Citation[]            // pełne dane cytatów (przychodzą równolegle ze strumieniem)
  messageId?: string               // przyznane przez backend po `done`
  timing?: { total: number; search: number; think: number; stream: number }
  error?: string
}
```

Pełny kontrakt eventów: **`API_CONTRACT.md` § 4**.

Po `phase === "done"` (lub `error`): pokaż akcje wiadomości i follow-up chips. Pamiętaj o **auto-collapse** thinking panelu i cytatów (UX po zakończeniu).

## 7. Tweaks (panel ustawień)

W prototypie zewnętrzny panel (host protocol), w produkcji: prosty **Sheet** (shadcn/ui) z linkiem w sidebarze.

Zmienne przechowywane w `localStorage` (Zustand persist):
- `theme`: `"light" | "dark"`
- `accent`: `"blue" | "mint" | "navy" | "lavender"`
- `density`: `"comfortable" | "compact"`
- `font`: `"inter" | "poppins" | "plex"`
- `anim`: `"off" | "subtle" | "normal" | "playful"`
- `citationLayout`: `"cards" | "sidebar" | "inline"` (**default: `"cards"`**)

Mechanika: ustaw atrybut na `<html>` (`data-theme`, `data-accent`, itd.) — reszta dzieje się przez CSS variables (patrz `reference/styles.css`).

## 8. Design tokens

**Skopiuj 1:1 z `reference/styles.css`** (linie 1–110). Najważniejsze:

### Kolory bazowe
```css
--c-white:           #FFFFFF
--c-bg-light:        #F5F7FA      /* light bg */
--c-bg-dark:         #0F172A      /* dark bg */
--c-pastel-blue:     #DFF6FF
--c-pastel-mint:     #B8F2E6
--c-lavender:        #C7CEEA
--c-accent-blue:     #7DD3FC      /* primary accent (default) */
--c-accent-mint:     #6EE7B7
--c-accent-navy:     #5B6C8F
--c-accent-lavender: #C7CEEA
```

### Light theme
```css
--bg:            #F5F7FA
--bg-elev:       #FFFFFF
--bg-subtle:     #FAFBFD
--bg-hover:      rgba(15,23,42,0.04)
--border:        rgba(15,23,42,0.07)
--border-strong: rgba(15,23,42,0.12)
--text:          #0F172A
--text-2:        #334155
--text-3:        #64748B
--text-muted:    #94A3B8
```

### Dark theme
```css
--bg:            #0A1220
--bg-elev:       #111B2E
--bg-subtle:     #0E1828
--bg-hover:      rgba(255,255,255,0.04)
--border:        rgba(203,213,225,0.08)
--text:          #E2E8F0
--text-2:        #CBD5E1
--text-3:        #94A3B8
--text-muted:    #64748B
```

### Typografia
- **Sans:** Inter (default), Poppins, IBM Plex Sans — wszystkie wagi 400/500/600/700
- **Mono:** JetBrains Mono (do citation refs `[1]`, czasów, kbd shortcuts)
- Skala: 10px → 11px → 11.5px → 12px → 12.5px → 13px → 13.5px → 14.5px (composer) → 15px (answer body)
- Line-height: 1.4 (tytuły), 1.55 (UI), 1.65 (answer body)

### Spacing / radii / cienie
```css
--r-sm: 8px   --r-md: 12px   --r-lg: 16px   --r-xl: 22px   --r-pill: 999px

--t-fast: 140ms   --t-med: 280ms   --t-slow: 480ms
--ease:   cubic-bezier(0.2, 0.7, 0.2, 1)

--shadow-sm:   0 1px 2px rgba(15,23,42,0.04)
--shadow-md:   0 4px 12px rgba(15,23,42,0.06)
--shadow-lg:   0 16px 40px rgba(15,23,42,0.10)
--shadow-glow: 0 0 0 4px color-mix(in oklch, var(--accent) 16%, transparent)
```

## 9. Komponenty do odtworzenia (mapping prototyp → produkcja)

| Prototyp                                        | Produkcja                                              | Uwagi                                                                   |
| ----------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------- |
| `screens/chat.jsx` → `Chat`                     | `app/(app)/chat/[id]/page.tsx`                         | Główny layout + state machine                                            |
| `screens/login.jsx` → `Login`                   | `app/(auth)/login/page.tsx`                            | Bez Google/IKP                                                          |
| `components/mode-selector.jsx`                  | `components/chat/ModeSelector.tsx`                     | Segmented + Radix Popover dla hover info                                 |
| `components/thinking.jsx` → `SearchingState`    | `components/chat/SearchingState.tsx`                   | Animowany scanner dokumentów                                            |
| `components/thinking.jsx` → `ReflectPanel`      | `components/chat/ReflectPanel.tsx`                     | Timeline kroków, Collapsible z Radix                                    |
| `components/thinking.jsx` → `MultiAgentPanel`   | `components/chat/MultiAgentPanel.tsx`                  | 3 agent cards                                                            |
| `components/citations.jsx` → `CitationsCards`   | `components/chat/citations/CitationsCards.tsx`         | **Domyślny layout** (2-col grid)                                         |
| `components/citations.jsx` → `CitationsSidebar` | `components/chat/citations/CitationsSidebar.tsx`       | Opcjonalny przez Tweaks                                                  |
| `components/citations.jsx` → `CitationsInline`  | `components/chat/citations/CitationsInline.tsx`        | Accordion footnotes                                                      |
| `components/icons.jsx`                          | `lucide-react`                                          | Mapping ikon w `lib/icons.ts`                                            |
| `tweaks-panel.jsx`                              | `components/settings/SettingsSheet.tsx`                | Z `<Sheet>` shadcn/ui, persist do localStorage                          |

## 10. Plan migracji (sugerowana kolejność)

1. **Setup:** `pnpm create next-app`, dodaj Tailwind + shadcn/ui + lucide + react-query + zustand
2. **Tokens & theming:** skopiuj `styles.css` do `globals.css`, dodaj `data-theme` switcher
3. **Auth flow:** login screen + middleware redirect → mocki API póki nie podłączysz prawdziwego
4. **Sidebar shell:** `AppSidebar` + project switcher + lista rozmów (z fake danymi z `data.jsx`)
5. **Chat — statyczna wersja:** pełny layout z gotową odpowiedzią (bez stream)
6. **Citations:** wszystkie 3 warianty, sterowane Tweaks
7. **Chat — stream:** podłącz `useChatStream` do prawdziwego endpointu, state machine
8. **Tryby AI:** ModeSelector + Reflect/Multi panele
9. **History + Admin:** lista + CRUD dokumentów + upload
10. **Polish:** animacje (fade-up, stagger, scale-in), focus states, keyboard shortcuts (⌘N, ⌘K, Esc), accessibility (Radix daje większość out-of-the-box)

## 11. Pliki w tej paczce

```
design_handoff_medrag/
├── README.md                  ← ten plik
├── API_CONTRACT.md            ← kontrakt z backendem (przeczytaj!)
├── CLAUDE_CODE_PROMPT.md      ← gotowy prompt do wklejenia w Claude Code
├── SPEC_CHAT.md               ← szczegółowa specyfikacja ekranu czatu (piksele)
├── mocks/                     ← mocki API do testów lokalnych
│   ├── README.md              ← jak postawić mock-serwer (Node + Express)
│   ├── user.json
│   ├── projects.json
│   ├── documents.json
│   ├── conversations.json
│   ├── conversation-detail.json
│   ├── sse-vanilla.txt        ← strumień SSE dla mode=vanilla
│   ├── sse-reflect.txt        ← strumień SSE dla mode=reflect
│   └── sse-multi.txt          ← strumień SSE dla mode=multi
└── reference/                 ← oryginalny prototyp HTML (read-only)
    ├── medRAG.html
    ├── app.jsx / app.css
    ├── styles.css             ← TOKENS!
    ├── data.jsx               ← przykładowe dane / kształt typów
    ├── components/
    │   ├── citations.jsx
    │   ├── icons.jsx
    │   ├── mode-selector.jsx
    │   └── thinking.jsx
    └── screens/
        ├── chat.jsx + chat.css + chat-loading.css
        ├── login.jsx + login.css
        ├── history.jsx
        ├── admin.jsx
        └── history-admin.css
```

## 12. Czego NIE kopiować z prototypu
- `setTimeout`-y w `chat.jsx::runGeneration` — to symulacja, użyj prawdziwego streamu
- `data.jsx` jako źródło danych — to mocki, użyj API
- `tweaks-panel.jsx` jako host protocol — w produkcji zwykły `<Sheet>` 
- Babel in-browser + script tags — w produkcji TypeScript + bundler
- `dangerouslySetInnerHTML` (nie ma — ale na wszelki wypadek: nie wprowadzaj go gdy parsujesz markdown z LLM, użyj react-markdown z sanitizacją)

## 13. RODO / compliance (do uwzględnienia w backendzie, frontend powinien wspierać)
- Wszystkie request mają `Authorization: Bearer <jwt>` lub httpOnly cookie
- Każda odpowiedź AI musi mieć `messageId` i `usedChunks: string[]` — frontend pokazuje "5 z 8 fragmentów wykorzystano" jako audit log
- Disclaimer "nie zastępuje lekarza" jest **wymagany prawnie** — nie usuwaj go z UI
- Logout musi czyścić token i cache TanStack Query (`queryClient.clear()`)
