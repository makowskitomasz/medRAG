# Audyt UI/UX — medRAG frontend

**Data:** 2026-08-01
**Zakres:** `frontend/` (Next.js 15) + ścieżka zapytań przez api-gateway
**Metoda:** przegląd całego kodu UI (~4350 linii TS/TSX + 1341 linii CSS) oraz ~15 realnych zapytań
wykonanych przez ten sam kanał API, z którego korzysta przeglądarka (proxy `/api/*` → api-gateway →
orchestrator, SSE). Stan systemu: 17 kontenerów `healthy`.

**Nic nie zostało zmienione ani usunięte.** Zapytania testowe utworzyły nowe konwersacje w projekcie
`Drug Interactions` (można je skasować ręcznie z historii, jeśli przeszkadzają).

---

## 1. Podsumowanie

Interfejs jest dojrzały jak na demonstrator: streaming z podziałem na fazy (search → think → stream),
panele rozumowania per tryb RAG, trzy warianty prezentacji cytowań, i18n PL/EN, tryb ciemny, panel
admina z drag&drop i pollingiem statusu indeksacji. Fundament jest dobry.

Problemy dzielą się na trzy grupy:

1. **Defekt, który uderza w główną tezę pracy** — cytowania gubią się w ~1 na 5 odpowiedzi (§2.1).
   Praca deklaruje traceability jako kluczową własność RARE-RAG; UI tego nie dowozi konsekwentnie.
2. **Funkcje napisane, ale nieosiągalne z UI** — panel ustawień, dwa z trzech układów cytowań,
   sugerowane pytania, zamykanie disclaimera, ⌘K (§3).
3. **Braki w obsłudze czekania i błędów** — 10–35 s bez sensownego feedbacku, brak retry,
   brak akcji na odpowiedzi (§4, §5).

Priorytet dla obrony pracy: **§2.1, §2.2, §4.1, §3.1** — reszta to szlif.

---

## 2. Błędy krytyczne

### 2.1. Utrata wszystkich cytowań, gdy model użyje wariantu markera

**Objaw:** odpowiedź powołuje się na źródła w treści, ale UI pokazuje „0 fragmentów", brak kart
cytowań, a surowy marker wycieka do tekstu odpowiedzi.

**Przyczyna:** `services/generation/app/services/citation_extractor.py:9`

```python
re.finditer(r"[\[【]\s*SOURCE_(\d+)\s*[\]】]", answer)
```

Model (gpt-oss-120b) emituje też formy, których ten regex nie łapie:

| forma w odpowiedzi | złapane? |
|---|---|
| `[SOURCE_2]` | tak |
| `【SOURCE_2】` | tak |
| `[**SOURCE_2**]` (bold w środku nawiasu) | **nie** |
| `[​SOURCE_3]` (zero-width space; `\s` w Pythonie go nie obejmuje) | **nie** |
| ` [...]` (narrow no-break space przed nawiasem) | nie dotyczy, ale psuje odstępy |

**Pomiar:** na 10 zapytaniach do projektu `Drug Interactions` (tryb vanilla) 2 odpowiedzi straciły
**komplet** cytowań mimo 2–5 markerów w treści. Przykłady:

```
"Ibuprofen plus lisinopril risks?"   → cits=0, markery: [​SOURCE_3], [​SOURCE_5]
"And what about ... ibuprofen?"      → cits=0, markery: [**SOURCE_2**] ×2
"Explain amiodarone digoxin ..."     → cits=3, markery: 【SOURCE_1】【SOURCE_4】   (OK)
```

**Skutek uboczny w UI:** `MessageAnswer.normalizeText()`
(`frontend/components/chat/MessageAnswer.tsx:14`) ma dokładnie ten sam brak, więc gdy backend
przepuści taką formę, użytkownik widzi w tekście dosłowne `[​SOURCE_3]` zamiast klikalnego numerka.

**Naprawa (backend, jedna linia):**

```python
CITE_RX = re.compile(r"[\[【][\s​‌⁠*_]*SOURCE[_ ]?(\d+)[\s​‌⁠*_]*[\]】]", re.I)
```
plus lustrzana poprawka w `normalizeText()`. Warto też dodać przypadki `[**SOURCE_1**]`
i `[​SOURCE_1]` do `services/generation/tests/test_citation_extractor.py`.

**Dlaczego to ważne dla pracy:** to jest dokładnie ten mechanizm, o którym ch7 pisze
*„the citation mechanism that makes every claim traceable to a passage"*. Jeśli recenzent kliknie
i trafi na odpowiedź bez cytowań, argument się sypie.

### 2.2. Zwijanie sidebara nie przesuwa layoutu

`app/(app)/chat/[id]/page.tsx:156`:

```tsx
<div className={`chat-root${useUIStore.getState().sidebarCollapsed ? " sidebar-collapsed" : ""}`}>
```

`getState()` czyta store **nieraktywnie**. Po kliknięciu zwijania re-renderuje się tylko `Sidebar`
(subskrybowany hookiem), a `ChatPage` nie — więc klasa `.sidebar-collapsed` nie trafia na
`.chat-root` i siatka zostaje `280px 1fr` (`globals.css:451,459`). Efekt: zwinięty sidebar
zostawia 216 px pustki, dopóki cokolwiek innego nie wymusi re-renderu.

**Naprawa:** `const sidebarCollapsed = useUIStore((s) => s.sidebarCollapsed);`

### 2.3. Znacznik czasu wiadomości użytkownika liczony przy renderze

`page.tsx:204` — `new Date().toLocaleTimeString(...)` bez zapamiętanej wartości. Każda wiadomość
użytkownika pokazuje „teraz", a godzina przeskakuje przy każdym re-renderze (czyli przy każdym
tokenie streamu). Trzeba zapisać `createdAt` w `ChatMessage`.

---

## 3. Funkcje napisane, ale nieosiągalne z interfejsu

### 3.1. Panel ustawień nie istnieje — 5 preferencji jest martwych

Store (`store/index.ts`) trzyma `accent`, `density`, `font`, `anim`, `citationLayout`.
`layout.tsx` sumiennie wystawia je jako `data-accent`, `data-density`, `data-font`, `data-anim`
na `<html>`, a `globals.css` ma pod nie style. Ale:

```
setAccent:          0 wywołań
setDensity:         0 wywołań
setFont:            0 wywołań
setAnim:            0 wywołań
setCitationLayout:  0 wywołań
```

`TopBar` ma przycisk ustawień, ale renderuje go tylko gdy dostanie `onSettingsOpen` — a **żaden
rodzic go nie przekazuje**. Czyli: cała warstwa personalizacji + dwa z trzech układów cytowań
(`sidebar`, `inline` — razem ~150 linii dopracowanego kodu w `Citations.tsx`) są dla użytkownika
niewidoczne. `citationLayout` jest na stałe `"cards"`.

**To najtańszy duży zysk w całym audycie:** panel/drawer ustawień odblokowuje gotowy kod.
Dla pracy magisterskiej układ `sidebar` (cytowania w prawej kolumnie, na żywo w trakcie streamu)
jest zdecydowanie najbardziej efektowny na demo.

### 3.2. Sugerowane pytania — zdefiniowane, nierenderowane

`page.tsx:49` — `const FOLLOW_UPS = [...]` (3 pytania po polsku) nie jest użyte nigdzie. Pusty
ekran startowy pokazuje tylko ikonę i zdanie opisu. Chipy z przykładowymi pytaniami to standard
w tego typu UI i realnie skracają czas do pierwszego zapytania.

### 3.3. Disclaimera nie da się zamknąć

`useDisclaimer()` zwraca `{ visible, hide }`, z 30-dniową pamięcią w localStorage — ale `hide`
nie jest destrukturyzowane (`page.tsx:81` bierze tylko `visible`) i nie ma przycisku ✕.
Baner medyczny wisi w każdej konwersacji na zawsze.

### 3.4. ⌘K reklamowane, niezaimplementowane

`Sidebar.tsx:163` renderuje `<kbd>⌘K</kbd>` przy polu wyszukiwania. Jedyny globalny handler
klawiszy (`page.tsx:143`) obsługuje wyłącznie ⌘N. Naciśnięcie ⌘K nie robi nic (w Chrome przejmie
je pasek adresu). Albo dopiąć fokus na input, albo zdjąć `<kbd>`.

### 3.5. Martwe przyciski

- `Citations.tsx:202-203` — „Open document" i „Copy snippet" bez `onClick`. Widoczne tylko w układzie
  `inline`, więc na razie zasłonięte przez §3.1, ale po jego naprawie staną się widoczne.
- `login/page.tsx:151` — „Forgot password" jako `href="#"`.
- `login/page.tsx:22,147` — checkbox „Remember me" nigdzie nie wpływa na zapis tokenu.
- `TopBar.tsx:49` — przycisk „pin" renderuje się tylko dla `pinned`, którego nikt nie przekazuje.
- `Sidebar.tsx:170` — pozycja „bieżąca konwersacja" to `<button>` bez akcji.

---

## 4. Obsługa czekania i błędów

### 4.1. Długie ciche okna w trakcie zapytania

Zmierzone czasy do pierwszego widocznego sygnału (SSE, projekt DDI, 54 629 chunków):

| tryb | search start | search done | pierwszy `think` | pierwszy token | koniec |
|---|---|---|---|---|---|
| vanilla | 0,1 s | ~11,9 s | 12,1 s | 17,9 s | 25,1 s |
| rare_rag (hotpot) | *brak eventu* | *brak* | ~30 s | 32,7 s | 32,7 s |

Dwa problemy:

- **Vanilla:** ~12 s ze spinnerem „Searching your documents" i **pustą listą** — `SearchingState`
  dostaje `docs=[]`, bo backend wysyła nazwy plików dopiero w evencie `done`. Podlicznik
  `{doneCount} / {docs.length}` nie renderuje się wcale. To najdłuższy pojedynczy moment niepewności
  w całej aplikacji. Retrieval mógłby streamować nazwy plików przyrostowo — komponent jest już na to
  gotowy (obsługuje `progress` i `doc.done` per dokument, ścieżka używana przez mock SSE).
- **rare_rag i pokrewne:** pipeline **w ogóle nie emituje eventu `search`**. Użytkownik widzi ~30 s
  bez żadnej informacji zwrotnej, a potem od razu odpowiedź. Etapy „Triage / Grounding check /
  Answer accepted" przychodzą dopiero na końcu, jednym rzutem — więc `ThinkPanel`, który miał
  pokazywać rozumowanie na żywo, pokazuje je *po fakcie*. To akurat szkoda, bo w kontekście pracy
  właśnie widoczność tych kroków jest tym, co RARE-RAG „kupuje" zamiast dokładności.

**Sugestia:** skeleton/pasek postępu z etykietami etapów i licznikiem sekund od startu, plus
emisja `search start` we wszystkich pipeline'ach.

### 4.2. Błąd bez możliwości ponowienia

`page.tsx:363` renderuje błąd jako czerwony tekst wpisany inline stylami — bez ikony, bez przycisku
„Spróbuj ponownie", bez zachowania treści pytania (input jest czyszczony w `handleSend` *przed*
`send()`, więc po błędzie użytkownik musi przepisać pytanie od zera). Przy 25-sekundowych
zapytaniach to bolesne.

**Minimum:** przycisk retry przy błędzie + przywrócenie tekstu do inputu, gdy `send` rzuci.

### 4.3. `alert()` jako komunikat walidacji

`page.tsx:128` — `alert("Please select a project in the sidebar.")`. Natywny alert, po angielsku,
mimo pełnego i18n (237 kluczy w obu językach). Powinien być toast albo inline hint.

### 4.4. Twardy 502 dla klientów bez `Accept: text/event-stream`

Odtwarzalne 4/4:

```
Accept: text/event-stream  → 200, ~17 kB SSE
Accept: */*                → 502 {"detail":"Gateway unreachable: fetch failed"}
```

Przeglądarka zawsze wysyła właściwy nagłówek (`lib/api.ts:357`), więc **UI działa** — ale każdy inny
klient (curl, skrypt ewaluacyjny, przyszła integracja) dostaje mylący błąd „gateway unreachable",
podczas gdy gateway odpowiedział 200 i pipeline wykonał się do końca. Wart naprawy dla
reprodukowalności eksperymentów opisywanych w pracy.

### 4.5. Brak sygnału „projekt jest pusty"

Dwa z czterech projektów mają 0 dokumentów:

```
test20260602      0 dokumentów   ← domyślnie wybrany w sidebarze
Wikipedia         0 dokumentów
hotpot_qa      1 988 dokumentów
Drug Interactions 16 776 dokumentów
```

`Sidebar.tsx:43` ustawia `activeProjectId = projectList[0]`, czyli **pusty `test20260602`**. Pierwsze
pytanie nowego użytkownika trafia w próżnię i dostaje:

> „I'm sorry, but the provided context does not contain enough information to answer your question…"

— nieodróżnialne od „nie ma tego w bazie". Front zna `documents/stats`; wystarczy przy 0 dokumentach
pokazać w pustym stanie i przy composerze: „Ten projekt nie ma zaindeksowanych dokumentów"
(+ link do panelu admina). Alternatywnie: domyślnie wybierać projekt z największą liczbą dokumentów.

---

## 5. Braki funkcjonalne w czacie

Rzeczy, których użytkownik oczekuje, a których nie ma:

- **Kopiowanie odpowiedzi.** `msg-actions` (`page.tsx:428`) zawiera wyłącznie „N fragmentów".
  Brak kopiuj / regeneruj / kciuk w górę-dół. Kciuki byłyby dodatkowo źródłem danych do rozdziału
  ewaluacyjnego.
- **Eksport konwersacji** (MD/PDF) — naturalne dla narzędzia doradczego i łatwe do pokazania na obronie.
- **Zarządzanie konwersacjami.** Nie da się zmienić nazwy ani usunąć rozmowy — ani w sidebarze,
  ani w `/history` (menu „⋯" ma tylko Open i Copy link). Historia będzie tylko rosnąć.
- **Tytuły konwersacji** to pierwsze pytanie ucięte CSS-em. Krótkie podsumowanie z LLM byłoby czytelniejsze.
- **Wyszukiwarka szuka tylko po pierwszym pytaniu.** `Sidebar.tsx:60` i `history/page.tsx:103`
  filtrują po `first_user_message`; treść odpowiedzi i dalsze pytania są nieprzeszukiwalne.
- **Filtr trybów w historii jest niekompletny** — `history/page.tsx:167-172` wymienia 4 tryby,
  podczas gdy `MODE_LABELS` w tym samym pliku zna 9. Rozmów w trybie CRAG/MADAM/RARE nie da się
  odfiltrować, choć badanie dotyczy właśnie ich.
- **Brak porównania trybów side-by-side.** Skoro to jest demonstrator do pracy porównującej
  architektury RAG, możliwość zadania jednego pytania dwóm trybom i zestawienia odpowiedzi obok siebie
  (czas, liczba cytowań, treść) byłaby najmocniejszym elementem obrony. Cała infrastruktura już jest —
  `rag_mode_override` działa per zapytanie.
- **Brak widoku metryk RAGAS.** Serwis `eval` liczy metryki na `query.completed`, ale UI ich nie
  pokazuje. Nawet mały odznaczek „faithfulness 0,94" pod odpowiedzią spinałby pracę z demonstratorem.

---

## 6. Dostępność i responsywność

Tu jest największa systemowa luka — mierzalna i łatwa do wytknięcia na obronie.

| sprawdzenie | wynik |
|---|---|
| `aria-*` w całym `app/` + `components/` | **2 wystąpienia** (oba to `aria-hidden` na dekoracyjnym SVG) |
| `:focus-visible` w `globals.css` | **0** |
| `prefers-reduced-motion` | **0** (mimo ustawienia `anim` w store!) |
| breakpointy mobilne | **1**, i tylko dla ekranu logowania |

Konkretnie:

- **Nawigacja klawiaturą jest praktycznie niemożliwa** — zero stylów fokusa na 1341 linii CSS.
  Nie da się zobaczyć, gdzie się jest. To jedna reguła `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`.
- **Brak `aria-live`** na wątku czatu — czytnik ekranu nie ogłosi napływającej odpowiedzi.
  Streaming jest kompletnie niedostępny dla użytkownika niewidomego.
- **Rozwijane panele** (`SearchingState`, `ThinkPanel`, `CitationsCards`, menu projektu, menu użytkownika)
  nie mają `aria-expanded` ani `aria-controls`.
- **Menu bez semantyki** — menu projektu i użytkownika to `<div>` z `<button>`, bez `role="menu"`,
  bez pułapki fokusa, bez zamykania na Escape (jest tylko zamykanie na klik poza — `Sidebar.tsx:31`).
- **Aplikacja jest bezużyteczna na telefonie.** `.chat-root` to sztywne `grid-template-columns: 280px 1fr`
  bez żadnego media query. Na 375 px sidebar zjada 75% ekranu, a composer zostaje na ~95 px.
  Ekran logowania jest responsywny (jedyny `@media (max-width: 700px)`) — więc użytkownik zaloguje się
  na telefonie i wpadnie w nieużywalny czat. Potrzebny sidebar jako off-canvas drawer poniżej ~900 px.
- **Kontrast:** `--text-muted` używany na 10,5–11 px tekście (podpisy w `ModeSelector`,
  `cite-card-sub`) — warto zweryfikować pod WCAG AA, prawdopodobnie nie przechodzi.
- **`<html lang>`** jest ustawiane po hydratacji (`layout.tsx`, `ThemeSync`); pierwszy render zawsze
  ma `lang="en"`, nawet gdy użytkownik ma wybrane PL.

---

## 7. Drobniejsze uwagi

- **Login ma zaszyte dane admina** (`login/page.tsx:19-20`: `admin@mail.com` / `admin`). Wygodne na demo,
  ale jeśli cokolwiek z tego trafi poza laptopa — do usunięcia. Minimum: pod flagą env.
- **Formaty dat są mieszane i niezależne od locale** — `en-GB` w `page.tsx:204` i `history/page.tsx:116`,
  `en` w `Sidebar.tsx:189`, przy pełnym i18n PL/EN. Powinno iść z `locale` ze store'u.
- **Sidebar pokazuje maksymalnie 10 konwersacji** (`Sidebar.tsx:178`) bez informacji, ile jest ukrytych.
- **`/history` pobiera wszystkie rozmowy ze wszystkich projektów naraz** (`Promise.all`, po 100 na projekt)
  i filtruje po stronie klienta. Przy 4 projektach jeszcze uchodzi; przy większej liczbie trzeba
  filtrowania serwerowego.
- **Upload przyjmuje tylko jeden plik naraz** (`admin/page.tsx:582,588` — `files[0]`), choć drag&drop
  wizualnie sugeruje wielo-plikowość. Przy korpusie 16 776 dokumentów to realne ograniczenie.
- **Brak `<title>`/metadanych** — `layout.tsx` nie eksportuje `metadata`, karta przeglądarki pokaże
  domyślny tytuł Next.js.
- **Renderer Markdown jest ręczny** (`MessageAnswer.tsx`) i obsługuje tylko `**bold**`, listy `-`/`•`
  i cytat `>`. Brak tabel, kodu, nagłówków, kursywy, list numerowanych. Model potrafi zwrócić tabelę
  interakcji — użytkownik zobaczy wtedy surowe pipe'y. Warto rozważyć `react-markdown` z własnym
  rendererem dla markerów cytowań.

---

## 8. Rekomendowana kolejność prac

**Etap 1 — wiarygodność demonstratora (0,5–1 dnia)**

1. Naprawa regexa cytowań w `citation_extractor.py` + `normalizeText()` + testy (§2.1)
2. Reaktywne `sidebarCollapsed` (§2.2)
3. Baner „projekt nie ma dokumentów" + domyślny wybór niepustego projektu (§4.5)
4. Retry przy błędzie + zachowanie treści pytania (§4.2)
5. `:focus-visible` — jedna reguła CSS (§6)

**Etap 2 — odblokowanie napisanego kodu (1–2 dni)**

6. Drawer ustawień: motyw, akcent, gęstość, font, animacje, układ cytowań (§3.1)
7. Chipy z sugerowanymi pytaniami w pustym stanie (§3.2)
8. Zamykanie disclaimera + ⌘K + usunięcie martwych przycisków (§3.3, §3.4, §3.5)
9. Akcje przy odpowiedzi: kopiuj / regeneruj / ocena (§5)

**Etap 3 — wartość dla obrony (2–3 dni)**

10. Przyrostowy feedback wyszukiwania + `search` we wszystkich pipeline'ach (§4.1)
11. Tryb porównania dwóch architektur side-by-side (§5)
12. Metryki RAGAS przy odpowiedzi (§5)
13. Responsywność: off-canvas sidebar poniżej 900 px (§6)

**Etap 4 — dostępność (1–2 dni)**

14. `aria-live` na wątku, `aria-expanded` na panelach, role menu, Escape, `prefers-reduced-motion`

Punkty 1, 10, 11 i 12 mają bezpośrednie przełożenie na tekst pracy: pierwszy naprawia mechanizm,
na którym opiera się argument o traceability, a pozostałe trzy czynią z demonstratora narzędzie,
które ilustruje tezę zamiast tylko jej towarzyszyć.
