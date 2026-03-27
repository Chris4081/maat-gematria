# Maat Gematria

> A symbolic analysis plugin for [text-generation-webui](https://github.com/oobabooga/text-generation-webui) — gematria calculation, pattern comparison, memory integration, and AI context injection across multiple alphabetic traditions.

**Author:** Christof Krieg — Independent Researcher  
www.maat-research.com

---

## What It Does

Maat Gematria transforms letter-number correspondences into an interactive symbolic-analysis layer for AI systems. It is not a proof engine — it is a reflective tool for detecting resonance patterns across names, words, and concepts.

Key principle:
> *Gematria functions as a mirror: it reveals how a person, a symbol, and a history can become linked through repeated numerical structures.*

---

## Supported Gematria Systems

| Key | System | Description |
|-----|--------|-------------|
| `EN_ORD` | English Ordinal | A=1, B=2, … Z=26 |
| `PYTH` | Pythagorean Reduction | Letters reduced to 1–9 |
| `EN_GEM` | English Gematria | Ordinal values × 6 |
| `HEB_STD` | Hebrew Mispar Hechrechi | Standard Hebrew letter values |
| `HEB_GADOL` | Hebrew Mispar Gadol | Final letters receive extended values |
| `HEB_KATAN` | Hebrew Mispar Katan | Reduced Hebrew values (1–9) |
| `HEB_ATBASH` | Hebrew Atbash | Mirror substitution before value assignment |
| `GR_ISO` | Greek Isopsephy | Full classical Greek letter values |
| `GR_SIMPLE` | Greek Simple | Simplified Greek letter values |

All systems can be applied simultaneously to a single input. English, Hebrew, and Greek inputs are normalised automatically.

---

## Features

### 1. Gematria Calculation
For each selected system, the plugin computes:
- per-letter numerical breakdown
- total sum
- digital root (recursive sum to single digit)


---

### 2. Multi-System Comparison
Apply multiple gematria systems to the same input simultaneously. Enables cross-tradition symbolic analysis — the same name or concept may reveal different structures depending on the alphabetic system.

---

### 3. Auto-Trigger Mode
The plugin detects trigger phrases automatically in chat input and computes results without manual UI interaction.

Configurable via regex (default):
```
^\s*(?:gematria\s*:\s*|!gematria\s+)(?P<text>.+)$
```

The trigger prefix can optionally be stripped from the user message before it reaches the model.

---

### 4. Context Injection
Computed gematria results can be injected directly into the AI's reasoning context. This allows the model to reference symbolic correspondences in follow-up responses — transforming the plugin from a static calculator into a contextual reasoning aid.

Configurable:
- `inject_on_trigger`: enable/disable injection
- `inject_cap`: character limit for injected block

---

### 5. Memory Integration
Results can be saved to a persistent Maat Memory extension (`maat_memory`). This makes symbolic anchors available across sessions — useful for long-term symbolic projects, autobiographical reflection, and recurring thematic research.

---

### 6. History Tracking
A persistent log of all analysed inputs and results. Enables review of recurring patterns over time and makes symbolic exploration reproducible rather than purely momentary.

---

### 7. CSV Export
Full calculation history can be exported as a CSV file for external documentation and analysis. Useful for:
- building personal symbolic archives
- comparing recurring numbers
- analysing resonance clusters
- integrating gematria data into broader research workflows

---

### 8. Sum Comparison
Groups multiple inputs by shared gematric value within a selected system. Reveals *resonance clusters* — sets of different terms that converge numerically.

Sources:
- automatically from history
- or a custom list (one entry per line)

---

## Installation

Place the `maat_gematria` folder into your text-generation-webui extensions directory:

```
text-generation-webui/
└── user_data/
   └── extensions/
      └── maat_gematria/
         └── script.py
```

Enable in the webui under **Extensions** → `maat_gematria`.

**Dependencies:**
```bash
pip install gradio pyyaml
```

---

## Configuration

All settings are configurable from the UI under **Settings** and persisted in `user_data/extensions/maat_gematria/gematria.yaml`.

| Setting | Default | Description |
|---------|---------|-------------|
| `default_systems` | `["EN_ORD", "PYTH"]` | Systems active by default |
| `auto_trigger` | `true` | Enable chat trigger detection |
| `inject_on_trigger` | `false` | Inject result into AI context |
| `inject_cap` | `1200` | Max characters injected |
| `strip_trigger_prefix` | `true` | Remove trigger phrase from user input |
| `persist_history` | `true` | Save history to disk |
| `history_limit` | `50` | Max entries in history |
| `save_to_memory` | `false` | Save results to Maat Memory extension |
| `max_chars_memory` | `800` | Character cap for memory entries |
| `trigger_regex` | see above | Regex for auto-trigger detection |
| `debug` | `false` | Enable debug logging |

---

## Technical Architecture

The plugin is structured in five modular layers:

```
Input normalisation
    └── cleaning English / Hebrew / Greek input

Value mapping
    └── assignment of numerical values by system

Computation
    └── total sums · digital roots · per-letter breakdown

Interaction layer
    └── Gradio UI · auto-trigger · comparison tools

Persistence layer
    └── memory integration · history · CSV export
```

This layered structure allows additional alphabets, scoring systems, or symbolic transformations to be integrated in future versions without modifying the core architecture.

---

## text-generation-webui Hooks

The plugin implements the standard extension hooks:

| Hook | Purpose |
|------|---------|
| `input_modifier` | Detects trigger, optionally strips prefix |
| `custom_generate_chat_prompt` | Injects gematria block into context |
| `bot_prefix_modifier` | Prepends result block to AI response prefix |
| `ui()` | Renders the Gradio tab |

---

## Interpretive Note

The plugin does not prove metaphysical claims. Its outputs are numerical transformations of text under specific symbolic systems. Their significance emerges only through interpretation.

The plugin should be understood as:
- a symbolic-analysis tool
- a reflective support module
- a resonance-mapping instrument

— not as an oracle or proof engine.

---

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

This project is free software. If you modify or publicly deploy Maat Gematria, you must also release the source code of your modifications.

> *Maat Gematria is a research and art project. Its goal is awareness, not exploitation.*
