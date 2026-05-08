# Diagramy PlantUML — pakiet na spotkanie z promotorem

## Pliki

1. `01_context.puml` — C4 Context (system w otoczeniu)
2. `02_container.puml` — C4 Container (wszystkie mikroserwisy)
3. `03_seq_query.puml` — sekwencja zapytania (sync + SSE + async event)
4. `04_seq_ingestion.puml` — sekwencja ingestion (event-driven przez RabbitMQ)
5. `05_state_document.puml` — lifecycle dokumentu

## Renderowanie — 3 sposoby

### Sposób 1: PlantUML online (najszybszy)
- Wejdź na https://www.plantuml.com/plantuml/uml/
- Wklej zawartość pliku `.puml`
- Wyrenderowuje się automatycznie, możesz pobrać PNG/SVG

### Sposób 2: VS Code
```bash
# Zainstaluj rozszerzenie: jebbs.plantuml
# Otwórz plik .puml
# Alt+D = preview, Ctrl+Shift+P → "PlantUML: Export Current Diagram"
```

### Sposób 3: CLI (najlepszy do pracy magisterskiej, batch render)
```bash
# Zainstaluj
sudo apt install plantuml          # Linux
brew install plantuml              # macOS

# Render wszystkich do PNG (do druku/pracy)
plantuml -tpng *.puml

# Render do SVG (do edycji w Inkscape, lepsze dla LaTeX)
plantuml -tsvg *.puml

# Render do PDF (gotowe do wstawienia do pracy)
plantuml -tpdf *.puml
```

## Struktura repo (sugerowana)

```
my-rag-thesis/
├── docs/
│   ├── diagrams/         # te pliki
│   ├── adr/              # Architecture Decision Records
│   └── api/              # OpenAPI specs
├── services/
│   ├── auth/
│   ├── gateway/
│   ├── ingestion-api/
│   └── ...
├── frontend/             # Next.js
├── shared/               # wspólna lib (logger, AMQP client)
├── docker/
│   └── docker-compose.yml
└── thesis/               # tex / docx pracy
```

Wersjonujesz `.puml` w git razem z kodem — diagramy zawsze
zsynchronizowane z architekturą.
