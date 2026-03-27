import os
import io
import re
import csv
import time
import yaml
import threading
import unicodedata as ud
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import gradio as gr

# ============================================================
# Paths / Defaults
# ============================================================
EXT_DIR = os.path.join("user_data", "extensions", "maat_gematria")
STATE_FILE = os.path.join(EXT_DIR, "gematria.yaml")
HISTORY_FILE = os.path.join(EXT_DIR, "history.yaml")
CSV_FILE = os.path.join(EXT_DIR, "history.csv")

MEM_EXT_DIR = os.path.join("user_data", "extensions", "maat_memory")
MEM_FILE = os.path.join(MEM_EXT_DIR, "memory.yaml")

SCHEMA_VERSION = 3

DEFAULTS = {
    "version": SCHEMA_VERSION,
    "debug": False,
    "save_to_memory": False,
    "default_systems": ["EN_ORD", "PYTH"],
    "max_chars_memory": 800,
    "history_limit": 50,
    "persist_history": True,
    "auto_trigger": True,
    "trigger_regex": r"^\s*(?:gematria\s*:\s*|!gematria\s+)(?P<text>.+)$",
    "inject_on_trigger": False,
    "inject_cap": 1200,
    "strip_trigger_prefix": True,
    "store_trigger_result_in_history": True,
}

config = dict(DEFAULTS)
history: List[Tuple[float, str, Dict[str, dict]]] = []
_IO_LOCK = threading.Lock()
_last_hit = {"term": None, "block": None}


# ============================================================
# File helpers
# ============================================================
def _ensure_dirs() -> None:
    os.makedirs(EXT_DIR, exist_ok=True)
    os.makedirs(MEM_EXT_DIR, exist_ok=True)


def _debug(*parts) -> None:
    if config.get("debug"):
        print("[maat-gematria]", *parts, flush=True)


def _atomic_write_yaml(path: str, data) -> None:
    tmp = path + ".tmp"
    with _IO_LOCK:
        with io.open(tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, path)


def _load_yaml(path: str):
    if not os.path.exists(path):
        return {}
    with _IO_LOCK:
        with io.open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


def _save_state() -> None:
    _ensure_dirs()
    _atomic_write_yaml(STATE_FILE, config)


def _load_state() -> None:
    _ensure_dirs()
    raw = _load_yaml(STATE_FILE)
    config.clear()
    config.update(DEFAULTS)
    if isinstance(raw, dict):
        config.update(raw)


def _save_history() -> None:
    if not config.get("persist_history", True):
        return
    payload = {
        "version": SCHEMA_VERSION,
        "items": [
            {
                "ts": ts,
                "text": text,
                "results": results,
            }
            for ts, text, results in history
        ],
    }
    _atomic_write_yaml(HISTORY_FILE, payload)


def _load_history() -> None:
    history.clear()
    raw = _load_yaml(HISTORY_FILE)
    items = raw.get("items", []) if isinstance(raw, dict) else []
    for item in items:
        try:
            history.append((float(item["ts"]), str(item["text"]), dict(item["results"])))
        except Exception:
            continue


# ============================================================
# Utility helpers
# ============================================================
def _cap(s: str, n: int) -> str:
    if n <= 0 or len(s) <= n:
        return s
    return s[: max(0, n - 60)].rstrip() + "\n… [truncated]"


def digital_root(n: int) -> int:
    n = abs(int(n))
    if n == 0:
        return 0
    return 1 + (n - 1) % 9


def reduce_1_9(v: int) -> int:
    return ((v - 1) % 9) + 1 if v > 0 else 0


# ============================================================
# Mappings
# ============================================================
EN_ORD = {chr(i + 64): i for i in range(1, 27)}
EN_GEM = {k: v * 6 for k, v in EN_ORD.items()}

HEB_STD = {
    "א": 1,
    "ב": 2,
    "ג": 3,
    "ד": 4,
    "ה": 5,
    "ו": 6,
    "ז": 7,
    "ח": 8,
    "ט": 9,
    "י": 10,
    "כ": 20,
    "ך": 20,
    "ל": 30,
    "מ": 40,
    "ם": 40,
    "נ": 50,
    "ן": 50,
    "ס": 60,
    "ע": 70,
    "פ": 80,
    "ף": 80,
    "צ": 90,
    "ץ": 90,
    "ק": 100,
    "ר": 200,
    "ש": 300,
    "ת": 400,
}
HEB_GADOL = HEB_STD | {"ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900}
_HEB_ATBASH_MAP = {
    "א": "ת", "ב": "ש", "ג": "ר", "ד": "ק", "ה": "צ", "ו": "פ", "ז": "ע", "ח": "ס", "ט": "נ",
    "י": "מ", "כ": "ל", "ך": "ל", "ל": "כ", "מ": "י", "ם": "י", "נ": "ט", "ן": "ט", "ס": "ח",
    "ע": "ז", "פ": "ו", "ף": "ו", "צ": "ה", "ץ": "ה", "ק": "ד", "ר": "ג", "ש": "ב", "ת": "א",
}

GR_ISO = {
    "Α": 1, "Β": 2, "Γ": 3, "Δ": 4, "Ε": 5, "Ϛ": 6, "Ζ": 7, "Η": 8, "Θ": 9,
    "Ι": 10, "Κ": 20, "Λ": 30, "Μ": 40, "Ν": 50, "Ξ": 60, "Ο": 70, "Π": 80,
    "Ϟ": 90, "Ρ": 100, "Σ": 200, "Τ": 300, "Υ": 400, "Φ": 500, "Χ": 600, "Ψ": 700, "Ω": 800, "Ϡ": 900,
}
GR_SIMPLE = {
    "Α": 1, "Β": 2, "Γ": 3, "Δ": 4, "Ε": 5, "Ζ": 7, "Η": 8, "Θ": 9,
    "Ι": 10, "Κ": 20, "Λ": 30, "Μ": 40, "Ν": 50, "Ξ": 60, "Ο": 70, "Π": 80,
    "Ρ": 100, "Σ": 200, "Τ": 300, "Υ": 400, "Φ": 500, "Χ": 600, "Ψ": 700, "Ω": 800,
}


# ============================================================
# Normalisation
# ============================================================
def strip_non_english(s: str) -> str:
    s = ud.normalize("NFKD", s)
    s = "".join(ch for ch in s if "A" <= ch.upper() <= "Z")
    return s.upper()


def strip_hebrew(s: str) -> str:
    return "".join(ch for ch in s if ch in HEB_STD)


def norm_greek(s: str) -> str:
    s = ud.normalize("NFKC", s).upper().replace("Ϲ", "Σ").replace("ς", "Σ")
    return "".join(ch for ch in s if ch in GR_SIMPLE or ch in GR_ISO)


# ============================================================
# Calculation
# ============================================================
@dataclass
class GematriaResult:
    total: int
    digital_root: int
    breakdown: List[Tuple[str, int]]


def calc_en_ordinal(text: str) -> GematriaResult:
    t = strip_non_english(text)
    vals = [(ch, EN_ORD.get(ch, 0)) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_en_pyth(text: str) -> GematriaResult:
    t = strip_non_english(text)
    vals = [(ch, reduce_1_9(EN_ORD.get(ch, 0))) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_en_gem(text: str) -> GematriaResult:
    t = strip_non_english(text)
    vals = [(ch, EN_GEM.get(ch, 0)) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_hebrew_hechrechi(text: str) -> GematriaResult:
    t = strip_hebrew(text)
    vals = [(ch, HEB_STD.get(ch, 0)) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_hebrew_gadol(text: str) -> GematriaResult:
    t = strip_hebrew(text)
    vals = [(ch, HEB_GADOL.get(ch, 0)) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_hebrew_katan(text: str) -> GematriaResult:
    t = strip_hebrew(text)
    vals = [(ch, reduce_1_9(HEB_STD.get(ch, 0))) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_hebrew_atbash(text: str) -> GematriaResult:
    t = strip_hebrew(text)
    mapped = [_HEB_ATBASH_MAP.get(ch, ch) for ch in t]
    vals = [(ch, HEB_STD.get(ch, 0)) for ch in mapped]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


def calc_greek_isopsephy(text: str) -> GematriaResult:
    t = norm_greek(text)
    vals = [(ch, GR_ISO.get(ch, GR_SIMPLE.get(ch, 0))) for ch in t]
    total = sum(v for _, v in vals)
    return GematriaResult(total, digital_root(total), vals)


SYSTEMS = {
    "EN_ORD": ("English Ordinal (A=1..Z=26)", calc_en_ordinal),
    "PYTH": ("Pythagorean (Reduction 1–9)", calc_en_pyth),
    "EN_GEM": ("English Gematria (×6)", calc_en_gem),
    "HE_HE": ("Hebräisch – Mispar Hechrechi", calc_hebrew_hechrechi),
    "HE_GD": ("Hebräisch – Mispar Gadol", calc_hebrew_gadol),
    "HE_KT": ("Hebräisch – Mispar Katan", calc_hebrew_katan),
    "HE_AT": ("Hebräisch – Atbash (Hechrechi)", calc_hebrew_atbash),
    "GR_ISO": ("Griechisch – Isopsephie", calc_greek_isopsephy),
}


def compute_all(text: str, sys_ids: List[str]) -> Dict[str, dict]:
    out = {}
    for sid in sys_ids:
        if sid not in SYSTEMS:
            continue
        title, fn = SYSTEMS[sid]
        res = fn(text)
        out[sid] = {
            "title": title,
            "total": res.total,
            "digital_root": res.digital_root,
            "breakdown": res.breakdown,
        }
    return out


def render_results(text: str, results: Dict[str, dict]) -> str:
    if not results:
        return "ℹ️ Keine Ergebnisse."
    lines = [f"### Ergebnis für: **{text}**"]
    for sid, r in results.items():
        lines.append(
            f"**{r['title']}** — Summe: **{r['total']}** · Digital Root: **{r['digital_root']}**"
        )
        if r["breakdown"]:
            letters = " ".join(f"{ch}({v})" for ch, v in r["breakdown"])
            lines.append(f"`{letters}`")
        else:
            lines.append("`(no characters recognised for this system)`")
        lines.append("")
    return "\n".join(lines).strip()


def render_results_compact(text: str, results: Dict[str, dict]) -> str:
    lines = [f"[GEMATRIA] term='{text}'"]
    for _, r in results.items():
        lines.append(f"- {r['title']}: total={r['total']}, dr={r['digital_root']}")
    return "\n".join(lines)


# ============================================================
# Memory integration
# ============================================================
def _sanitize_memory(raw):
    if not isinstance(raw, dict):
        return {"version": 1, "memory": []}
    out = {"version": raw.get("version", 1)}
    pairs = raw.get("memory") or raw.get("pairs") or []
    out["memory"] = []
    if isinstance(pairs, list):
        for p in pairs:
            if isinstance(p, dict):
                out["memory"].append(
                    {
                        "keywords": str(p.get("keywords", "")),
                        "memory": str(p.get("memory", "")),
                        "always": bool(p.get("always", False)),
                    }
                )
    for k in ("timecontext", "datecontext", "debug", "max_context_chars"):
        if k in raw:
            out[k] = raw[k]
    return out


def _exists_entry(mem: dict, text: str) -> bool:
    target = (text or "").strip()
    return any((p.get("memory", "").strip() == target) for p in mem.get("memory", []))


def save_result_to_memory(original_text: str, results: Dict[str, dict]) -> bool:
    if not config.get("save_to_memory", False):
        return False
    mem_raw = _load_yaml(MEM_FILE)
    mem = _sanitize_memory(mem_raw)
    block = _cap(render_results_compact(original_text, results), int(config.get("max_chars_memory", 800)))
    if _exists_entry(mem, block):
        return False
    mem.setdefault("memory", []).append({
        "keywords": original_text,
        "memory": block,
        "always": False,
    })
    _atomic_write_yaml(MEM_FILE, mem)
    return True


# ============================================================
# History / CSV / Compare
# ============================================================
def _push_history(text: str, results: Dict[str, dict]) -> None:
    ts = time.time()
    history.append((ts, text, results))
    limit = int(config.get("history_limit", 50))
    if len(history) > limit:
        del history[:-limit]
    _save_history()


def _render_history_md() -> str:
    if not history:
        return "(empty)"
    parts: List[str] = []
    for ts, text, results in history[::-1]:
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        parts.append(f"#### {dt} — **{text}**")
        parts.append(render_results(text, results))
        parts.append("---")
    return "\n".join(parts[:-1])


def export_history_csv() -> str:
    _ensure_dirs()
    with io.open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "datetime", "input", "system_id", "title", "total", "digital_root", "breakdown"
        ])
        for ts, text, results in history:
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            for sid, r in results.items():
                br = " ".join(f"{ch}({v})" for ch, v in r.get("breakdown", []))
                writer.writerow([ts, dt, text, sid, r.get("title", ""), r.get("total", 0), r.get("digital_root", 0), br])
    return CSV_FILE


def compare_same_sums(inputs: List[str], systems: List[str], min_group: int = 2) -> str:
    inputs = [x.strip() for x in inputs if x and x.strip()]
    if not inputs:
        return "⚠️ Keine gültigen Einträge."
    systems = systems or config.get("default_systems", ["EN_ORD", "PYTH"])

    report = []
    for sid in systems:
        if sid not in SYSTEMS:
            continue
        title, _ = SYSTEMS[sid]
        buckets: Dict[int, List[str]] = {}
        for word in inputs:
            res = compute_all(word, [sid])[sid]
            buckets.setdefault(int(res["total"]), []).append(word)
        groups = [(s, sorted(set(words))) for s, words in buckets.items() if len(set(words)) >= int(min_group)]
        if not groups:
            report.append(f"### {title}\n(no groups ≥ {min_group})\n")
            continue
        report.append(f"### {title}")
        for total, words in sorted(groups, key=lambda x: (-len(x[1]), x[0])):
            report.append(f"- **Sum {total}**: {', '.join(words)}")
        report.append("")
    return "\n".join(report).strip() or "ℹ️ No groups found."


# ============================================================
# Shared execution path
# ============================================================
def run_gematria(text: str, systems: Optional[List[str]] = None, save_history: bool = True) -> Dict[str, dict]:
    text = (text or "").strip()
    systems = systems or config.get("default_systems", ["EN_ORD", "PYTH"])
    results = compute_all(text, systems)
    if config.get("save_to_memory", False):
        try:
            save_result_to_memory(text, results)
        except Exception as exc:
            _debug("save_result_to_memory failed:", exc)
    if save_history:
        _push_history(text, results)
    return results


# ============================================================
# Trigger helpers
# ============================================================
def _extract_trigger_term(user_input: str) -> Optional[str]:
    if not config.get("auto_trigger", True):
        return None
    pattern = config.get("trigger_regex") or DEFAULTS["trigger_regex"]
    try:
        m = re.search(pattern, user_input or "", flags=re.IGNORECASE)
    except re.error:
        m = re.search(DEFAULTS["trigger_regex"], user_input or "", flags=re.IGNORECASE)
    if not m:
        return None
    term = (m.groupdict().get("text") or "").strip()
    return term or None


def _build_trigger_block(term: str) -> str:
    results = run_gematria(term, config.get("default_systems", ["EN_ORD", "PYTH"]), save_history=config.get("store_trigger_result_in_history", True))
    block = render_results(term, results)
    _last_hit["term"] = term
    _last_hit["block"] = block
    return block


# ============================================================
# text-generation-webui hooks
# ============================================================
def input_modifier(string, state=None, is_chat=False):
    """
    Robust signature for different text-generation-webui versions.
    Keeps visible prompt intact by default, but can strip the trigger prefix if desired.
    """
    term = _extract_trigger_term(string or "")
    if not term:
        return string
    _build_trigger_block(term)
    if config.get("strip_trigger_prefix", True):
        return term
    return string


def custom_generate_chat_prompt(user_input, state_dict, **kwargs):
    term = _extract_trigger_term(user_input or "")
    if not term:
        return None
    block = _last_hit.get("block") or _build_trigger_block(term)
    if config.get("inject_on_trigger", False) and isinstance(state_dict, dict):
        capped = _cap(block, int(config.get("inject_cap", 1200)))
        current = state_dict.get("context", "") or ""
        state_dict["context"] = (capped + "\n\n" + current).strip()
        _debug("context injected for term:", term)
    return None


def bot_prefix_modifier(prefix, state=None):
    if not config.get("inject_on_trigger", False):
        return prefix
    block = _last_hit.get("block")
    if not block:
        return prefix
    _last_hit["term"] = None
    _last_hit["block"] = None
    capped = _cap(block, int(config.get("inject_cap", 1200)))
    return (capped + "\n\n" + (prefix or "")).strip()


# ============================================================
# UI
# ============================================================
def ui():
    _load_state()
    _load_history()

    system_choices = [(SYSTEMS[k][0], k) for k in SYSTEMS.keys()]

    with gr.Tab("🔢 Maat Gematria"):
        with gr.Row():
            tb_text = gr.Textbox(label="Word / phrase", placeholder="Example: Maat, אמת, ΑΓΑΠΗ …")
        with gr.Row():
            dd_sys = gr.CheckboxGroup(
                choices=system_choices,
                label="Systems",
                value=config.get("default_systems", ["EN_ORD", "PYTH"]),
                info="Multiple selection supported. English/Greek/Hebrew are normalised automatically.",
            )
        with gr.Row():
            btn_calc = gr.Button("Calculate", variant="primary")
            btn_clear = gr.Button("Clear history")
            btn_export = gr.Button("Export CSV")
        out_md = gr.Markdown(value="")
        out_file = gr.File(label="CSV download", visible=False)

        with gr.Accordion("History", open=False):
            out_hist = gr.Markdown(value=_render_history_md())

        with gr.Accordion("Compare (find matching sums)", open=False):
            with gr.Row():
                cb_use_hist = gr.Checkbox(value=True, label="Use inputs from history")
            tb_list = gr.Textbox(label="Custom list (one entry per line)", lines=6, visible=False)
            with gr.Row():
                dd_cmp_sys = gr.CheckboxGroup(
                    choices=system_choices,
                    label="Systems for comparison",
                    value=config.get("default_systems", ["EN_ORD", "PYTH"]),
                )
                nb_min = gr.Number(value=2, precision=0, label="Min. group size (≥)")
            btn_cmp = gr.Button("Compare")
            out_cmp = gr.Markdown(value="")

        with gr.Accordion("⚙️ Settings", open=False):
            with gr.Row():
                cb_debug = gr.Checkbox(value=config.get("debug", False), label="Debug logs")
                cb_mem = gr.Checkbox(value=config.get("save_to_memory", False), label="Save results to Maat memory")
                cb_persist = gr.Checkbox(value=config.get("persist_history", True), label="Persist history")
            with gr.Row():
                dd_default = gr.CheckboxGroup(
                    choices=system_choices,
                    label="Default systems",
                    value=config.get("default_systems", ["EN_ORD", "PYTH"]),
                )
            with gr.Row():
                nb_hist = gr.Number(value=config.get("history_limit", 50), precision=0, label="History limit")
                nb_cap = gr.Number(value=config.get("max_chars_memory", 800), precision=0, label="Memory cap (characters)")
            gr.Markdown("**Auto-trigger** (e.g. `gematria: MAAT` or `!gematria MAAT`):")
            with gr.Row():
                cb_auto = gr.Checkbox(value=config.get("auto_trigger", True), label="Auto-trigger active")
                cb_inj = gr.Checkbox(value=config.get("inject_on_trigger", False), label="Inject result into context")
                cb_strip = gr.Checkbox(value=config.get("strip_trigger_prefix", True), label="Strip trigger prefix from user text")
            with gr.Row():
                tb_re = gr.Textbox(value=config.get("trigger_regex", DEFAULTS["trigger_regex"]), label="Trigger regex (group 'text' required)")
                nb_inj = gr.Number(value=config.get("inject_cap", 1200), precision=0, label="Cap on injection")

        def _calc(text, systems):
            text = (text or "").strip()
            if not text:
                return "⚠️ Please enter some text.", _render_history_md(), gr.update(visible=False)
            results = run_gematria(text, systems or None, save_history=True)
            return render_results(text, results), _render_history_md(), gr.update(visible=False)

        def _clear_hist():
            history.clear()
            _save_history()
            return gr.update(value="(empty)"), gr.update(value="ℹ️ History cleared."), gr.update(visible=False)

        def _export():
            path = export_history_csv()
            return gr.update(value=f"✅ CSV exported: `{path}`"), gr.update(value=path, visible=True)

        def _toggle_hist_src(use_hist):
            return gr.update(visible=not bool(use_hist))

        def _do_compare(use_hist, list_block, systems, min_group):
            if use_hist:
                inputs = [text for _, text, _ in history]
            else:
                inputs = [ln.strip() for ln in (list_block or "").splitlines() if ln.strip()]
            return compare_same_sums(inputs, systems or None, int(min_group or 2))

        def _upd_settings(dbg, mem, persist, dfl, hlim, cap, auto, inj, strip_prefix, rgx, injcap):
            config["debug"] = bool(dbg)
            config["save_to_memory"] = bool(mem)
            config["persist_history"] = bool(persist)
            config["default_systems"] = list(dfl or DEFAULTS["default_systems"])
            config["history_limit"] = max(1, int(hlim or 50))
            config["max_chars_memory"] = max(200, int(cap or 800))
            config["auto_trigger"] = bool(auto)
            config["inject_on_trigger"] = bool(inj)
            config["strip_trigger_prefix"] = bool(strip_prefix)
            config["trigger_regex"] = rgx or DEFAULTS["trigger_regex"]
            config["inject_cap"] = max(200, int(injcap or 1200))
            _save_state()
            _save_history()

        btn_calc.click(_calc, [tb_text, dd_sys], [out_md, out_hist, out_file])
        btn_clear.click(_clear_hist, [], [out_hist, out_md, out_file])
        btn_export.click(_export, [], [out_md, out_file])

        cb_use_hist.change(_toggle_hist_src, [cb_use_hist], [tb_list])
        btn_cmp.click(_do_compare, [cb_use_hist, tb_list, dd_cmp_sys, nb_min], [out_cmp])

        settings_inputs = [cb_debug, cb_mem, cb_persist, dd_default, nb_hist, nb_cap, cb_auto, cb_inj, cb_strip, tb_re, nb_inj]
        cb_debug.change(_upd_settings, settings_inputs, [])
        cb_mem.change(_upd_settings, settings_inputs, [])
        cb_persist.change(_upd_settings, settings_inputs, [])
        dd_default.change(_upd_settings, settings_inputs, [])
        nb_hist.change(_upd_settings, settings_inputs, [])
        nb_cap.change(_upd_settings, settings_inputs, [])
        cb_auto.change(_upd_settings, settings_inputs, [])
        cb_inj.change(_upd_settings, settings_inputs, [])
        cb_strip.change(_upd_settings, settings_inputs, [])
        tb_re.change(_upd_settings, settings_inputs, [])
        nb_inj.change(_upd_settings, settings_inputs, [])


# ============================================================
# Import initialisation
# ============================================================
def _on_import():
    _load_state()
    _load_history()
    print(
        "[maat-gematria] ready:",
        "default_systems=", config.get("default_systems"),
        "save_to_memory=", config.get("save_to_memory"),
        "auto_trigger=", config.get("auto_trigger"),
        "inject_on_trigger=", config.get("inject_on_trigger"),
        flush=True,
    )


_on_import()
