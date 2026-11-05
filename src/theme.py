"""
Dashboard design system for the Streamlit app  -  5 switchable themes.

  maroon_night      dark   brand maroon (default)
  cobalt_midnight   dark   deep navy + electric blue
  graphite_emerald  dark   charcoal + emerald
  maroon_light      light  warm white + maroon
  arctic_light      light  cool white + cobalt

How it works
  * every colour is a CSS variable (--pf-*) written to :root for the chosen theme, so a theme
    switch cross-fades (all surfaces have colour transitions)
  * the matplotlib charts (src/eda.py THEMES) use the same keys, so charts blend into the cards
  * motion = CSS (hover glow, button sheen, gauge ring, aurora background, sliding tab thumb)
    plus ONE script, assets/motion.js, driven by GSAP: staggered scroll reveals, smooth cursor ring,
    scroll-progress bar, KPI count-up, cursor spotlight, button ripple and a click-to-explain glossary.
    GSAP is read from assets/vendor/gsap.min.js when present, otherwise from cdnjs. If the script is
    blocked the page still works - panels simply appear without animating.
  * everything respects prefers-reduced-motion.

Pair this file with .streamlit/config.toml (base = "dark", primaryColor = BASE_PRIMARY): sliders
and toggles take their colour from the Streamlit theme and are hue-shifted per theme here.
"""

import colorsys
import html
import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.eda import THEMES

# primaryColor written in .streamlit/config.toml - used to hue-shift native sliders/toggles
BASE_PRIMARY = "#C65A7D"

ASSETS = Path(__file__).resolve().parent / "assets"
GSAP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"

DEFAULT_THEME = "maroon_night"

THEME_ORDER = ["maroon_night", "cobalt_midnight", "graphite_emerald", "maroon_light", "arctic_light"]

LABELS = {
    "maroon_night": "Maroon Night",
    "cobalt_midnight": "Cobalt Midnight",
    "graphite_emerald": "Graphite Emerald",
    "maroon_light": "Maroon Light",
    "arctic_light": "Arctic Light",
}

_DARK_STATUS = {
    "ok_bg": "#12382A", "ok_fg": "#76D9AA",
    "warn_bg": "#3A2E12", "warn_fg": "#F0C060",
    "bad_bg": "#3D1A1D", "bad_fg": "#F08A8A",
}
_LIGHT_STATUS = {
    "ok_bg": "#E3F4EA", "ok_fg": "#146C43",
    "warn_bg": "#FFF4DB", "warn_fg": "#8A5A00",
    "bad_bg": "#FBE6E8", "bad_fg": "#9B1C2C",
}

PALETTES = {
    "maroon_night": {
        "mode": "dark",
        "bg": "#141218", "card": "#1F1B25", "border": "#342E3C", "input": "#2A2531",
        "fg": "#ECE8F0", "muted": "#A39DAE",
        "brand": "#6B1E33", "brand_hi": "#8A2A47", "accent": "#C65A7D",
        **_DARK_STATUS,
    },
    "cobalt_midnight": {
        "mode": "dark",
        "bg": "#0B1220", "card": "#111A2C", "border": "#22304A", "input": "#172238",
        "fg": "#E6EDF7", "muted": "#8FA0BC",
        "brand": "#1D4ED8", "brand_hi": "#3B82F6", "accent": "#5BB8FF",
        "ok_bg": "#0E3327", "ok_fg": "#6EE7B7",
        "warn_bg": "#33290F", "warn_fg": "#FBBF24",
        "bad_bg": "#3A1620", "bad_fg": "#FDA4AF",
    },
    "graphite_emerald": {
        "mode": "dark",
        "bg": "#0F1412", "card": "#161D1A", "border": "#26332E", "input": "#1D2723",
        "fg": "#E6EFEA", "muted": "#8FA39A",
        "brand": "#0F7B5F", "brand_hi": "#15A07C", "accent": "#3DDC97",
        "ok_bg": "#10382B", "ok_fg": "#5EEAB4",
        "warn_bg": "#3A2F10", "warn_fg": "#F5C451",
        "bad_bg": "#3C1A1A", "bad_fg": "#FCA5A5",
    },
    "maroon_light": {
        "mode": "light",
        "bg": "#F7F4F6", "card": "#FFFFFF", "border": "#E6E8EC", "input": "#F6F1F3",
        "fg": "#1B1B22", "muted": "#5E6370",
        "brand": "#6B1E33", "brand_hi": "#8A2A47", "accent": "#A02C4D",
        **_LIGHT_STATUS,
    },
    "arctic_light": {
        "mode": "light",
        "bg": "#F3F6FB", "card": "#FFFFFF", "border": "#DDE5F0", "input": "#EEF3FA",
        "fg": "#0F1B2D", "muted": "#566783",
        "brand": "#1E4FD8", "brand_hi": "#2F6BF0", "accent": "#2563EB",
        **_LIGHT_STATUS,
    },
}

# kept so old code that imported MAROON keeps working
MAROON = PALETTES["maroon_night"]["brand"]


# ============================================================
# HELPERS
# ============================================================

def resolve(theme) -> str:
    """Accepts a theme key, or the old bool (True = dark) and returns a valid theme key."""

    if isinstance(theme, bool):
        return "maroon_night" if theme else "maroon_light"

    return theme if theme in PALETTES else DEFAULT_THEME


def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def _hue(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def _root_vars(name: str) -> str:
    p = PALETTES[name]

    hue_shift = (_hue(p["accent"]) - _hue(BASE_PRIMARY) + 540) % 360 - 180

    dark = p["mode"] == "dark"

    shadow = "0 22px 44px -30px rgba(0,0,0,.85)" if dark else "0 18px 40px -30px rgba(40,24,60,.32)"

    # dataframes are canvas-drawn in the Streamlit base theme (dark): invert them on light themes
    grid_filter = "none" if dark else "invert(1) hue-rotate(180deg) brightness(1.03)"

    return (
        ":root{"
        f"--pf-bg:{p['bg']};--pf-card:{p['card']};--pf-border:{p['border']};--pf-input:{p['input']};"
        f"--pf-fg:{p['fg']};--pf-muted:{p['muted']};"
        f"--pf-brand:{p['brand']};--pf-brand-hi:{p['brand_hi']};--pf-accent:{p['accent']};"
        f"--pf-acc-rgb:{_rgb(p['accent'])};--pf-brand-rgb:{_rgb(p['brand_hi'])};--pf-fg-rgb:{_rgb(p['fg'])};"
        f"--pf-ok-bg:{p['ok_bg']};--pf-ok-fg:{p['ok_fg']};"
        f"--pf-warn-bg:{p['warn_bg']};--pf-warn-fg:{p['warn_fg']};"
        f"--pf-bad-bg:{p['bad_bg']};--pf-bad-fg:{p['bad_fg']};"
        f"--pf-shadow:{shadow};--pf-hue:{hue_shift:.0f}deg;--pf-grid-filter:{grid_filter};"
        "--pf-ease:cubic-bezier(.16,1,.3,1);--pf-io:cubic-bezier(.65,0,.35,1);"
        f"color-scheme:{p['mode']};"
        "}"
    )


# ============================================================
# STYLESHEET
# ============================================================

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@500;600;700&display=swap');
@property --glow { syntax: '<number>'; inherits: false; initial-value: 0; }

@keyframes pfRise   { from { opacity: 0; transform: translateY(16px) scale(.99); } to { opacity: 1; transform: none; } }
@keyframes pfFade   { from { opacity: 0; } to { opacity: 1; } }
@keyframes pfImg    { from { opacity: 0; transform: scale(.99); } to { opacity: 1; transform: none; } }
@keyframes pfFill   { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pfGrow   { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes pfSheen  { from { transform: translateX(-120%); } to { transform: translateX(120%); } }
@keyframes pfPulse  { 0% { box-shadow: 0 0 0 0 rgba(var(--pf-acc-rgb), .55); } 70%, 100% { box-shadow: 0 0 0 9px rgba(var(--pf-acc-rgb), 0); } }
@keyframes pfFlow   { from { background-position: 0% 0; } to { background-position: 200% 0; } }
@keyframes pfAurora { from { transform: translate3d(0, 0, 0) scale(1); } to { transform: translate3d(3vmax, 2vmax, 0) scale(1.1); } }
@keyframes pfRing   { from { stroke-dashoffset: 100; } }
@keyframes pfSpin   { to { transform: rotate(360deg); } }
@keyframes pfShimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
@keyframes pfBreath { 0%, 100% { box-shadow: 0 0 0 0 rgba(var(--pf-acc-rgb), 0), 0 0 0 1px currentColor inset; } 50% { box-shadow: 0 0 34px -6px currentColor, 0 0 0 1px currentColor inset; } }
@keyframes pfRipple { from { transform: scale(0); opacity: .45; } to { transform: scale(1); opacity: 0; } }
@keyframes pfReveal { to { opacity: 1; } }
@keyframes pfToast  { from { opacity: 0; transform: translateY(14px) scale(.96); } to { opacity: 1; transform: none; } }

/* ============ page ============ */
html, [data-testid="stMain"] { scroll-behavior: smooth; }
.stApp { isolation: isolate; background: var(--pf-bg); color: var(--pf-fg); transition: background-color .6s ease, color .4s ease; }
html, body, .stApp, [data-testid="stMarkdownContainer"], label, button, input, textarea, select, [data-baseweb] {
    font-family: 'Manrope', 'Segoe UI', system-ui, -apple-system, sans-serif;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { font-family: 'Sora', 'Manrope', system-ui, sans-serif; letter-spacing: -.01em; }
.stApp::before {
    content: ""; position: fixed; inset: -20vmax; z-index: -2; pointer-events: none; will-change: transform;
    background:
        radial-gradient(38vmax 38vmax at 12% 8%,  rgba(var(--pf-acc-rgb), .17), transparent 62%),
        radial-gradient(34vmax 34vmax at 92% 18%, rgba(var(--pf-brand-rgb), .20), transparent 62%),
        radial-gradient(44vmax 44vmax at 62% 105%, rgba(var(--pf-acc-rgb), .09), transparent 62%);
    animation: pfAurora 26s ease-in-out infinite alternate;
}
.stApp::after {
    content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background-image:
        linear-gradient(rgba(var(--pf-fg-rgb), .045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(var(--pf-fg-rgb), .045) 1px, transparent 1px);
    background-size: 46px 46px;
    -webkit-mask-image: radial-gradient(120% 70% at 50% 0%, #000 0%, transparent 72%);
            mask-image: radial-gradient(120% 70% at 50% 0%, #000 0%, transparent 72%);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] {
    height: 3px; background: linear-gradient(90deg, var(--pf-brand), var(--pf-accent), var(--pf-brand-hi), var(--pf-brand));
    background-size: 200% 100%; animation: pfFlow 8s linear infinite; opacity: .4;
}
.block-container { padding-top: 2.4rem; max-width: 1400px; }
footer { visibility: hidden; }
hr { border-color: var(--pf-border) !important; }
::selection { background: rgba(var(--pf-acc-rgb), .35); }
* { scrollbar-width: thin; scrollbar-color: rgba(var(--pf-acc-rgb), .35) transparent; }
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: rgba(var(--pf-acc-rgb), .35); border-radius: 9px; }
::-webkit-scrollbar-thumb:hover { background: rgba(var(--pf-acc-rgb), .6); }
:focus-visible { outline: 2px solid var(--pf-accent) !important; outline-offset: 2px; }

/* the script that powers count-up / spotlight lives in an iframe: keep it out of the layout */
.st-key-pf_enh { position: absolute; width: 0; height: 0; overflow: hidden; margin: 0; padding: 0; }

/* ============ text colours (Streamlit base theme is not ours, so force them) ============ */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp li, .stApp span:not([data-testid="stIconMaterial"]),
.stApp label, .stApp label *,
[data-testid="stWidgetLabel"] *, [data-testid="stMarkdownContainer"] *,
[data-testid="stExpander"] summary *, [data-testid="stSidebar"] *,
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"],
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] { color: var(--pf-fg); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: var(--pf-muted) !important; }
code { color: var(--pf-ok-fg) !important; background: rgba(var(--pf-acc-rgb), .12) !important; border-radius: 5px; }

/* ============ sidebar ============ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--pf-card), var(--pf-bg)); border-right: 1px solid var(--pf-border);
    transition: background .5s ease;
}
.pf-brand { display: flex; align-items: center; gap: .85rem; margin: .9rem 0 1.1rem; animation: pfRise .8s cubic-bezier(.16,1,.3,1) backwards; }
.pf-mark {
    flex: none; width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; color: #fff;
    background: linear-gradient(140deg, var(--pf-brand), var(--pf-accent)); box-shadow: 0 10px 22px -10px rgba(var(--pf-acc-rgb), .9);
}
.pf-mark svg { width: 28px; height: 28px; color: #fff !important; animation: pfSpin 24s linear infinite; }
.pf-brand-t { font-family: 'Sora', sans-serif; font-size: 1.02rem; font-weight: 600; line-height: 1.25; color: var(--pf-fg) !important; }
.pf-brand-s { display: flex; align-items: center; gap: .45rem; margin-top: .3rem; font-size: .74rem; color: var(--pf-muted) !important; }
.pf-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pf-ok-fg); animation: pfPulse 2.2s ease-out infinite; }
.pf-side-h { font-family: 'Sora', sans-serif; font-size: .98rem; font-weight: 600; margin: .3rem 0 .6rem; color: var(--pf-fg) !important; }
.pf-side-p { font-size: .85rem; color: var(--pf-muted) !important; line-height: 1.7; }
.pf-swatches { display: flex; gap: .4rem; margin: .5rem 0 .2rem; }
.pf-swatches i { flex: 1; height: 22px; border-radius: 7px; border: 1px solid rgba(var(--pf-fg-rgb), .18); transition: transform .3s cubic-bezier(.2,.8,.2,1); animation: pfRise .6s cubic-bezier(.16,1,.3,1) backwards; }
.pf-swatches i:hover { transform: translateY(-4px) scale(1.08); }

/* ============ inputs ============ */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"],
[data-testid="stNumberInput"] input, [data-testid="stNumberInput"] button {
    background: var(--pf-input) !important; color: var(--pf-fg) !important; border-color: var(--pf-border) !important;
    transition: border-color .25s ease, box-shadow .25s ease, background-color .5s ease;
}
[data-baseweb="select"] > div:hover, [data-baseweb="input"]:hover { border-color: rgba(var(--pf-acc-rgb), .6) !important; }
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within { border-color: var(--pf-accent) !important; box-shadow: 0 0 0 3px rgba(var(--pf-acc-rgb), .22); }
[data-baseweb="select"] *, [data-baseweb="input"] input { color: var(--pf-fg) !important; }
/* newer Streamlit (react-aria): selectbox = .react-aria-ComboBox > div */
.react-aria-ComboBox > div {
    background: var(--pf-input) !important; border-color: var(--pf-border) !important;
    transition: border-color .25s ease, box-shadow .25s ease, background-color .5s ease;
}
.react-aria-ComboBox > div:hover { border-color: rgba(var(--pf-acc-rgb), .6) !important; }
.react-aria-ComboBox > div:focus-within { border-color: var(--pf-accent) !important; box-shadow: 0 0 0 3px rgba(var(--pf-acc-rgb), .22); }
.react-aria-ComboBox input, .react-aria-ComboBox button svg { color: var(--pf-fg) !important; }
[role="listbox"] { background: var(--pf-input) !important; border-radius: 10px; }
[role="listbox"] * { color: var(--pf-fg) !important; }
[role="option"] { transition: background .15s ease; }
[role="option"]:hover, [role="option"][data-focused="true"], [role="option"][aria-selected="true"] { background: rgba(var(--pf-acc-rgb), .18) !important; }
/* toggle: keep the OFF state visible on light themes */
[data-testid="stCheckbox"] label:has(input:not(:checked)) > span + div { background: rgba(var(--pf-fg-rgb), .25) !important; }
[data-testid="stCheckbox"] label:has(input:not(:checked)) > span + div > div { background: #FFFFFF !important; box-shadow: 0 1px 3px rgba(0,0,0,.45); }
/* newer Streamlit nests the bordered element deeper: recolour any bordered child of a select / number / text input */
[data-baseweb="select"] div { border-color: var(--pf-border) !important; }
[data-baseweb="select"]:focus-within div, [data-baseweb="select"] div:hover,
[data-testid="stNumberInputContainer"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within { border-color: var(--pf-accent) !important; }
[data-testid="stNumberInputContainer"], [data-testid="stTextInputRootElement"] { border-color: var(--pf-border) !important; background: var(--pf-input) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: var(--pf-input) !important; }
[data-baseweb="popover"] > div { border-radius: 10px; border: 1px solid var(--pf-border); animation: pfRise .25s cubic-bezier(.16,1,.3,1) both; }
[data-baseweb="popover"] li * { color: var(--pf-fg) !important; }
[data-baseweb="popover"] li { transition: background .15s ease; }
[data-baseweb="popover"] li:hover { background: rgba(var(--pf-acc-rgb), .16) !important; }
[data-baseweb="tag"] { background: rgba(var(--pf-acc-rgb), .2) !important; border-radius: 6px; }

/* native sliders + toggles take Streamlit's primary colour: shift its hue to the theme */
[data-testid="stSlider"] [role="slider"], [data-testid="stSlider"] [data-rac][style*="position: absolute"] > div ~ div { transition: box-shadow .25s ease; }
[data-testid="stSlider"] [role="slider"] { background: var(--pf-accent) !important; box-shadow: 0 0 0 4px rgba(var(--pf-acc-rgb), .22); }
[data-testid="stSlider"] [data-rac][style*="position: absolute"] { background: var(--pf-accent) !important; box-shadow: 0 0 0 4px rgba(var(--pf-acc-rgb), .22); transition: box-shadow .25s ease; }
[data-testid="stSlider"] [data-rac][style*="position: absolute"]:hover { box-shadow: 0 0 0 9px rgba(var(--pf-acc-rgb), .2); }
[data-testid="stSlider"] [data-baseweb="slider"] div[style*="linear-gradient"],
[data-testid="stSlider"] [data-orientation="horizontal"] > div:first-child:not([data-rac]) { filter: hue-rotate(var(--pf-hue)); }
[data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child,
[data-testid="stCheckbox"] label[data-rac] > span + div { filter: hue-rotate(var(--pf-hue)); transition: background .3s ease; }

/* ============ buttons ============ */
.stButton > button, .stDownloadButton > button {
    position: relative; overflow: hidden; border-radius: 10px; font-weight: 600; letter-spacing: .01em;
    background: linear-gradient(135deg, var(--pf-brand), var(--pf-brand-hi)) !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    box-shadow: 0 10px 22px -14px rgba(var(--pf-acc-rgb), .9), inset 0 1px 0 rgba(255,255,255,.16);
    transition: transform .25s cubic-bezier(.2,.8,.2,1), box-shadow .3s ease, filter .3s ease;
}
.stButton > button *, .stDownloadButton > button * { color: #FFFFFF !important; position: relative; z-index: 1; }
.stButton > button::after, .stDownloadButton > button::after {
    content: ""; position: absolute; inset: 0; transform: translateX(-120%);
    background: linear-gradient(105deg, transparent 30%, rgba(255,255,255,.28) 50%, transparent 70%);
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px); box-shadow: 0 18px 28px -14px rgba(var(--pf-acc-rgb), 1), inset 0 1px 0 rgba(255,255,255,.2); filter: brightness(1.08); }
.stButton > button:hover::after, .stDownloadButton > button:hover::after { animation: pfSheen .8s cubic-bezier(.2,.7,.2,1); }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0) scale(.97); }
.pf-ripple { position: absolute; border-radius: 50%; pointer-events: none; background: rgba(255,255,255,.6); animation: pfRipple .65s ease-out forwards; }

/* ============ navigation + radios (segmented control) ============ */
[data-testid="stRadio"] [role="radiogroup"] {
    display: inline-flex; flex-wrap: wrap; gap: .25rem; padding: .3rem; border-radius: 999px;
    background: var(--pf-card); border: 1px solid var(--pf-border); box-shadow: var(--pf-shadow);
    transition: background-color .5s ease, border-color .5s ease;
}
[data-testid="stRadio"] label[data-baseweb="radio"], [data-testid="stRadioOption"] {
    background: transparent; border: 1px solid transparent; border-radius: 999px; padding: .42rem 1.15rem; margin: 0; cursor: pointer;
    transition: background .35s cubic-bezier(.2,.8,.2,1), transform .25s ease, box-shadow .35s ease;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:hover, [data-testid="stRadioOption"]:hover { background: rgba(var(--pf-acc-rgb), .14); transform: translateY(-1px); }
/* hide the round radio dot (old DOM: first child; new DOM: the div that is not the text) */
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child:not(:has(p)),
[data-testid="stRadio"] label[data-baseweb="radio"] > span:not(:has(p)),
[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) { display: none !important; }
[data-testid="stRadio"] label p { font-size: .86rem; font-weight: 600; transition: color .25s ease; }
[data-testid="stRadio"] label:has(input:checked):not([data-testid="stWidgetLabel"]) {
    background: linear-gradient(135deg, var(--pf-brand), var(--pf-brand-hi)); box-shadow: 0 8px 18px -10px rgba(var(--pf-acc-rgb), 1);
}
[data-testid="stRadio"] [role="radiogroup"] { position: relative; isolation: isolate; }
[data-testid="stRadio"] [role="radiogroup"]::before {
    content: ""; position: absolute; left: 0; top: 0; z-index: 0; pointer-events: none; opacity: 0; border-radius: 999px;
    width: var(--tw, 0px); height: var(--th, 0px); transform: translate3d(var(--tx, 0px), var(--ty, 0px), 0);
    background: linear-gradient(135deg, var(--pf-brand), var(--pf-brand-hi)); box-shadow: 0 8px 18px -10px rgba(var(--pf-acc-rgb), 1), inset 0 1px 0 rgba(255,255,255,.16);
}
[data-testid="stRadio"] [role="radiogroup"][data-thumb]::before { opacity: 1; }
[data-testid="stRadio"] [role="radiogroup"][data-thumb="live"]::before {
    transition: transform .55s var(--pf-io), width .55s var(--pf-io), height .55s var(--pf-io);
}
[data-testid="stRadio"] [role="radiogroup"][data-thumb] label:has(input:checked):not([data-testid="stWidgetLabel"]) { background: transparent; box-shadow: none; }
[data-testid="stRadio"] [role="radiogroup"] label { position: relative; z-index: 1; }
[data-testid="stRadio"] label:has(input:checked) p { color: #FFFFFF !important; }

/* ============ banner ============ */
.pf-banner {
    position: relative; overflow: hidden; display: flex; justify-content: space-between; align-items: center; gap: 1.2rem;
    border-radius: 18px; padding: 1.4rem 1.8rem; margin-bottom: 1.3rem;
    background:
        repeating-radial-gradient(circle at 94% 50%, rgba(255,255,255,.075) 0 1px, transparent 1px 26px),
        linear-gradient(118deg, var(--pf-brand) 0%, var(--pf-brand-hi) 100%);
    box-shadow: 0 26px 48px -30px rgba(var(--pf-acc-rgb), .95), inset 0 1px 0 rgba(255,255,255,.18);
    animation: pfRise .9s cubic-bezier(.16,1,.3,1) backwards;
}
.pf-banner::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(105deg, transparent 38%, rgba(255,255,255,.2) 50%, transparent 62%); animation: pfSheen 1.8s .5s cubic-bezier(.2,.7,.2,1) both; }
.pf-banner .l { display: flex; align-items: center; gap: 1rem; }
.pf-banner .mark { width: 50px; height: 50px; border-radius: 14px; display: grid; place-items: center; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.24); backdrop-filter: blur(6px); }
.pf-banner .mark svg { width: 30px; height: 30px; color: #fff !important; animation: pfSpin 24s linear infinite; }
.pf-banner .t { font-family: 'Sora', sans-serif; font-size: 1.6rem; font-weight: 700; color: #FFFFFF !important; letter-spacing: -.02em; line-height: 1.15; }
.pf-banner .sub { margin-top: .3rem; font-size: .84rem; color: rgba(255,255,255,.82) !important; }
.pf-banner .r { display: flex; gap: .6rem; flex-wrap: wrap; justify-content: flex-end; }
.pf-chip { display: inline-flex; align-items: center; gap: .5rem; padding: .38rem .85rem; border-radius: 999px; font-size: .8rem; font-weight: 600; color: #FFFFFF !important; background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.24); backdrop-filter: blur(6px); }
.pf-chip .pf-dot { background: #7CF0B8; box-shadow: 0 0 0 0 rgba(124,240,184,.6); }

/* ============ KPI cards ============ */
.pf-kpi {
    position: relative; overflow: hidden; --glow: 0;
    background: radial-gradient(260px circle at var(--mx, 50%) var(--my, 0%), rgba(var(--pf-acc-rgb), calc(var(--glow) * .18)), transparent 70%), var(--pf-card);
    border: 1px solid var(--pf-border); border-radius: 14px; padding: 1.1rem 1.3rem 1.15rem; margin: .8rem 0 .9rem; box-shadow: var(--pf-shadow); min-height: 8.9rem;
    transition: --glow .4s ease, transform .4s cubic-bezier(.2,.8,.2,1), border-color .3s ease, box-shadow .4s ease, background-color .5s ease;
}
.pf-kpi::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; transform-origin: left; background: linear-gradient(90deg, var(--pf-brand-hi), var(--pf-accent)); animation: pfGrow 1s .25s cubic-bezier(.16,1,.3,1) backwards; }
.pf-kpi:hover { --glow: 1; transform: translateY(-5px); border-color: rgba(var(--pf-acc-rgb), .55); box-shadow: 0 26px 40px -28px rgba(var(--pf-acc-rgb), 1); }
.pf-kpi .l { font-size: .86rem; font-weight: 600; color: var(--pf-muted) !important; }
.pf-kpi .v { font-family: 'Sora', sans-serif; font-size: 2.05rem; font-weight: 600; color: var(--pf-fg) !important; line-height: 1.35; letter-spacing: -.025em; font-variant-numeric: tabular-nums; }
.pf-kpi .s { font-size: .76rem; color: var(--pf-muted) !important; }

/* ============ panels (st.container(key="panel_...")) ============ */
[class*="st-key-panel"] {
    position: relative; --glow: 0; --d: 0s;
    background: radial-gradient(560px circle at var(--mx, 50%) var(--my, 0%), rgba(var(--pf-acc-rgb), calc(var(--glow) * .09)), transparent 65%), var(--pf-card);
    border: 1px solid var(--pf-border); border-radius: 18px; padding: 1.3rem 1.5rem 1.5rem; margin-bottom: 1.1rem; box-shadow: var(--pf-shadow);
    transition: --glow .5s ease, border-color .35s ease, background-color .5s ease;
}
[class*="st-key-panel"]:hover { --glow: 1; border-color: rgba(var(--pf-acc-rgb), .35); }
.st-key-panel_telemetry, .st-key-panel_ba, .st-key-panel_risk, .st-key-panel_report { --d: .08s; }
.st-key-panel_breakdown { --d: .16s; }
.st-key-panel_signal, .st-key-panel_data { --d: .24s; }
.st-key-panel_corr, .st-key-panel_rejected { --d: .32s; }
[class*="st-key-inner"] { border: 1px solid var(--pf-border); border-radius: 12px; padding: 1rem 1.1rem; background: rgba(var(--pf-fg-rgb), .02); }
.pf-title { display: flex; align-items: center; gap: .65rem; font-family: 'Sora', sans-serif; font-size: 1.08rem; font-weight: 600; margin: 0 0 .8rem; color: var(--pf-fg) !important; }
.pf-title::before { content: ""; width: 4px; height: 1.15em; border-radius: 4px; background: linear-gradient(180deg, var(--pf-accent), var(--pf-brand-hi)); transform-origin: top; animation: pfGrow .8s .3s cubic-bezier(.16,1,.3,1) backwards; }

/* ============ images, tables, expanders, alerts ============ */
[data-testid="stImage"] img { border-radius: 10px; animation: pfImg .9s cubic-bezier(.16,1,.3,1) backwards; }
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid var(--pf-border); }
[data-testid="stDataFrame"] canvas, [data-testid="stDataFrame"] iframe { filter: var(--pf-grid-filter); }
[data-testid="stExpander"] details { background: var(--pf-card); border: 1px solid var(--pf-border); border-radius: 14px; transition: border-color .3s ease, background-color .5s ease; }
[data-testid="stExpander"] details:hover { border-color: rgba(var(--pf-acc-rgb), .4); }
[data-testid="stExpander"] summary { background: var(--pf-input); border-radius: 14px; transition: background .25s ease; }
[data-testid="stExpander"] details[open] > div { animation: pfFade .5s ease both; }
[data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--pf-border); animation: pfRise .5s cubic-bezier(.16,1,.3,1) backwards; }
[data-testid="stToast"] { border-radius: 14px !important; border: 1px solid var(--pf-border); background: var(--pf-card) !important; box-shadow: var(--pf-shadow); animation: pfToast .45s cubic-bezier(.16,1,.3,1) both; }

/* loading + rerun feedback */
[data-testid="stSpinner"] p, [data-testid="stSpinner"] { font-weight: 600; }
[data-testid="stSpinner"] p {
    background: linear-gradient(90deg, var(--pf-muted) 0%, var(--pf-accent) 25%, var(--pf-muted) 50%);
    background-size: 200% 100%; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    color: transparent !important; animation: pfShimmer 2.2s linear infinite;
}
[data-stale="true"] { opacity: .6 !important; transition: opacity .3s ease .12s !important; }

/* numbers stay hidden until the script has counted them up; if it never runs they fade in anyway */
.pf-kpi .v:not([data-pf-done]), .pf-gauge .num:not([data-pf-done]) { opacity: 0; animation: pfReveal .3s 1.5s forwards; }

/* ============ risk result: gauge + message ============ */
.pf-result {
    display: grid; grid-template-columns: 112px 1fr; align-items: center; gap: 1.3rem;
    border-radius: 16px; padding: 1.1rem 1.5rem; margin: 1.2rem 0 .6rem;
    animation: pfRise .7s cubic-bezier(.16,1,.3,1) backwards;
}
.pf-result.nogauge { grid-template-columns: 1fr; }
.pf-result .h { font-family: 'Sora', sans-serif; font-size: 1.18rem; font-weight: 600; line-height: 1.3; }
.pf-result .d { font-size: .86rem; margin-top: .35rem; opacity: .92; line-height: 1.6; }
.pf-result.ok   { background: linear-gradient(120deg, var(--pf-ok-bg), var(--pf-card));   color: var(--pf-ok-fg); }
.pf-result.warn { background: linear-gradient(120deg, var(--pf-warn-bg), var(--pf-card)); color: var(--pf-warn-fg); }
.pf-result.bad  { background: linear-gradient(120deg, var(--pf-bad-bg), var(--pf-card));  color: var(--pf-bad-fg); animation: pfRise .7s cubic-bezier(.16,1,.3,1) backwards, pfBreath 2.6s 1s ease-in-out infinite; }
.pf-result.ok *   { color: var(--pf-ok-fg) !important; }
.pf-result.warn * { color: var(--pf-warn-fg) !important; }
.pf-result.bad *  { color: var(--pf-bad-fg) !important; }
.pf-gauge { position: relative; width: 112px; height: 112px; }
.pf-gauge svg { width: 100%; height: 100%; transform: rotate(-90deg); overflow: visible; }
.pf-gauge .trk { fill: none; stroke: currentColor; stroke-opacity: .16; stroke-width: 9; }
.pf-gauge .val { fill: none; stroke: currentColor; stroke-width: 9; stroke-linecap: round; filter: drop-shadow(0 0 6px currentColor); animation: pfRing 1.5s .15s cubic-bezier(.22,1,.36,1) backwards; }
.pf-gauge .num { position: absolute; inset: 0; display: grid; place-items: center; font-family: 'Sora', sans-serif; font-size: 1.45rem; font-weight: 700; font-variant-numeric: tabular-nums; }

/* ============ motion layer: progress bar, cursor ring, glossary, page rail ============ */
#pf-bar { position: fixed; left: 0; top: 0; height: 3px; width: 100%; z-index: 1000000; pointer-events: none; transform: scaleX(0); transform-origin: left;
    background: linear-gradient(90deg, var(--pf-brand-hi), var(--pf-accent)); box-shadow: 0 0 12px rgba(var(--pf-acc-rgb), .7); will-change: transform; }
#pf-ring, #pf-dot { position: fixed; left: 0; top: 0; pointer-events: none; z-index: 1000000; opacity: 0; transition: opacity .35s ease; }
#pf-ring { width: 34px; height: 34px; margin: -17px 0 0 -17px; border-radius: 50%; border: 1.5px solid rgba(var(--pf-acc-rgb), .7); will-change: transform;
    scale: 1; transition: opacity .35s ease, scale .4s var(--pf-ease), background-color .3s ease, border-color .3s ease; }
#pf-ring.hot { scale: 1.65; background: rgba(var(--pf-acc-rgb), .12); border-color: rgba(var(--pf-acc-rgb), .9); }
#pf-ring.down { scale: .8; }
#pf-dot { width: 5px; height: 5px; margin: -2.5px 0 0 -2.5px; border-radius: 50%; background: var(--pf-accent); will-change: transform; }

.term { border-bottom: 1px dotted var(--pf-accent); cursor: help; transition: color .2s ease, border-color .2s ease; }
.term:hover, .term:focus-visible { color: var(--pf-accent) !important; border-bottom-style: solid; }
.pf-banner .term { border-bottom-color: rgba(255,255,255,.7); }
.pf-banner .term:hover { color: #FFFFFF !important; }
#term-pop {
    position: fixed; left: 50%; bottom: 28px; width: min(560px, calc(100vw - 28px)); max-height: calc(100vh - 90px); overflow-y: auto;
    transform: translateX(-50%); z-index: 1000001; display: none; padding: 1.4rem 1.5rem;
    background: var(--pf-card); border: 1px solid var(--pf-accent); border-radius: 20px;
    box-shadow: 0 30px 80px rgba(0,0,0,.6), 0 0 0 1px rgba(var(--pf-acc-rgb), .15); color: var(--pf-muted); font-family: 'Manrope', system-ui, sans-serif;
}
#term-pop h3 { margin: 0 2rem .7rem 0; font-family: 'Sora', sans-serif; font-size: 1.35rem; font-weight: 600; color: var(--pf-fg); letter-spacing: -.02em; }
#term-pop h5 { margin: .8rem 0 .15rem; font-family: 'Sora', sans-serif; font-size: .68rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--pf-accent); }
#term-pop p { margin: 0; font-size: .95rem; line-height: 1.6; color: var(--pf-fg); opacity: .9; }
#term-pop button { position: absolute; top: 14px; right: 14px; width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--pf-border); background: none; color: var(--pf-fg); font-size: 18px; line-height: 1; cursor: pointer; transition: border-color .2s ease, color .2s ease; }
#term-pop button:hover { border-color: var(--pf-accent); color: var(--pf-accent); }

.pf-flow { margin: .9rem 0 .3rem; animation: pfFade .6s ease backwards; }
.pf-flow-t { display: flex; align-items: baseline; gap: .6rem; font-family: 'Sora', sans-serif; font-size: .72rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--pf-muted); margin-bottom: .55rem; }
.pf-flow-t b { color: var(--pf-accent); font-weight: 600; }
.pf-flow-b { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 6px; }
.pf-flow-b i { position: relative; display: block; height: 4px; border-radius: 4px; overflow: hidden; background: rgba(var(--pf-fg-rgb), .12); }
.pf-flow-b i::after { content: ""; position: absolute; inset: 0; transform-origin: left; transform: scaleX(0); border-radius: inherit; background: linear-gradient(90deg, var(--pf-brand-hi), var(--pf-accent)); }
.pf-flow-b i.on::after { animation: pfFill .7s calc(var(--i) * .09s) var(--pf-ease) forwards; }
.pf-flow-b i.cur::after { box-shadow: 0 0 10px rgba(var(--pf-acc-rgb), .8); }

@media (max-width: 900px) {
    .pf-banner { flex-direction: column; align-items: flex-start; padding: 1.1rem 1.2rem; }
    .pf-banner .t { font-size: 1.25rem; }
    .pf-result { grid-template-columns: 1fr; justify-items: start; }
    [class*="st-key-panel"] { padding: 1rem 1rem 1.2rem; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; } .pf-kpi .v, .pf-gauge .num { opacity: 1 !important; } }
"""


# ============================================================
# GLOSSARY  (dotted words that explain themselves on click)
# ============================================================
# key -> words that trigger it, plus the five text fields shown in the pop-up.

GLOSSARY = {
    "roc_auc": {
        "words": ["ROC-AUC"], "title": "ROC-AUC",
        "what": "A single score for how well the model ranks risky readings above healthy ones.",
        "does": "Tells you whether the model separates the failure window from normal operation at all.",
        "how": "Take one reading from the failure window and one healthy reading: ROC-AUC is the chance the model gives the failure reading the higher risk.",
        "example": "0.50 is a coin flip, 1.00 is perfect. A score of 0.90 means 9 times out of 10 the risky reading ranks higher.",
    },
    "pr_auc": {
        "words": ["PR-AUC"], "title": "PR-AUC",
        "what": "Area under the precision-recall curve: how clean the alerts are when failures are rare.",
        "does": "Punishes false alarms. It is more honest than ROC-AUC when only a small share of rows are failures.",
        "how": "Sweeps the alert threshold from strict to loose and measures precision against recall at every step.",
        "example": "If 2% of test rows are failure-window rows, a model that guesses scores about 0.02. Anything far above that is real signal.",
    },
    "iqr": {
        "words": ["IQR"], "title": "IQR fence",
        "what": "The interquartile range: the spread of the middle half of a sensor's readings.",
        "does": "Flags glitches. Values far outside the fence are treated as spikes and replaced.",
        "how": "Fence = Q3 + k x IQR, computed on NORMAL rows only. BROKEN and RECOVERING rows are never touched, because their extremes are the failure signal.",
        "example": "A reading 40x above the usual spread on a NORMAL row is removed as a spike; the same reading during a breakdown is kept.",
    },
    "outlier": {
        "words": ["outliers", "outlier", "spikes"], "title": "Outliers",
        "what": "Readings that sit unusually far from a sensor's normal range.",
        "does": "Distort averages and charts, so glitches are cleaned before modelling.",
        "how": "Detected with the IQR fence and the -999 sentinel check, then filled by interpolation.",
        "example": "A pressure sensor jumping to 10,000 for one minute and back is a glitch, not a real event.",
    },
    "sentinel": {
        "words": ["sentinels", "sentinel"], "title": "Sentinel value",
        "what": "A 'no data' code that a sensor writes instead of a real number. Here it is -999.",
        "does": "Must be removed, otherwise it looks like an extreme reading.",
        "how": "Sentinels are turned into missing values first, then filled like any other gap.",
        "example": "-999.0 in sensor_07 is not a temperature; it means the sensor sent nothing.",
    },
    "imputation": {
        "words": ["imputation", "imputed"], "title": "Imputation",
        "what": "Filling missing sensor values with sensible estimates.",
        "does": "Keeps every minute usable without inventing dramatic values.",
        "how": "Short gaps are interpolated in time, longer gaps use the median of the same machine status, and anything left uses the global median.",
        "example": "A 5-minute dropout is bridged by a straight line between the readings on either side.",
    },
    "quarantine": {
        "words": ["quarantined", "quarantine"], "title": "Quarantine",
        "what": "Rows that fail the Pydantic schema check are set aside instead of crashing the run.",
        "does": "Protects the model from invalid records while keeping the evidence for inspection.",
        "how": "Each row is validated against MachineRecord; failures are listed with the reason on the Data & Report page.",
        "example": "A row with an unknown machine status is quarantined with the message explaining which field failed.",
    },
    "early_warning": {
        "words": ["early-warning", "early warning"], "title": "Early-warning target",
        "what": "The label the model learns: will this pump break within the next 24 hours?",
        "does": "Turns a handful of breakdowns into enough positive examples to train on.",
        "how": "Every row up to 24 h before a BROKEN row is flagged 1; everything else is 0. RECOVERING rows are left out of training.",
        "example": "A reading taken 6 hours before a breakdown is labelled 1 even though the pump still looked fine.",
    },
    "failure_window": {
        "words": ["failure-window", "failure window"], "title": "Failure window",
        "what": "The stretch of time (24 h by default) leading up to a breakdown.",
        "does": "Defines which records count as 'about to fail' for the model and for the rate shown here.",
        "how": "Set by HORIZON_MIN in config.py.",
        "example": "A failure-window rate of 3% means 3 in every 100 records fall inside a warning period.",
    },
    "hgb": {
        "words": ["HistGradientBoosting"], "title": "HistGradientBoosting",
        "what": "A fast tree-based scikit-learn classifier that builds many small decision trees one after another.",
        "does": "Learns non-linear combinations of sensors that a simple threshold would miss.",
        "how": "Each new tree corrects the mistakes of the previous ones; features are bucketed into histograms for speed.",
        "example": "It can learn that sensor_11 being low is only alarming when sensor_04 is also high.",
    },
}

_WORD_TO_KEY = {w.lower(): k for k, g in GLOSSARY.items() for w in g["words"]}
_TERM_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(_WORD_TO_KEY, key=len, reverse=True)) + r")(?![\w-])", re.I
)
_SKIP_TAGS = ("code", "a", "button", "h1", "h2", "h3", "h4", "svg", "style", "script")


def _glossary_payload() -> dict:
    # same shape the original reveal.js expects: [unused, title, what, does, how, example]
    return {k: ["", g["title"], g["what"], g["does"], g["how"], g["example"]] for k, g in GLOSSARY.items()}


def glossify(markup: str) -> str:
    """Wrap the first occurrence of every glossary word in clickable markup (skips code, links, headings)."""

    seen, depth, out = set(), 0, []

    for part in re.split(r"(<[^>]+>)", markup):
        if part.startswith("<"):
            m = re.match(r"</?\s*([a-zA-Z0-9]+)", part)

            if m and m.group(1).lower() in _SKIP_TAGS and not part.endswith("/>"):
                depth += -1 if part.startswith("</") else 1

            out.append(part)

        elif depth > 0:
            out.append(part)

        else:
            def wrap(m):
                key = _WORD_TO_KEY[m.group(1).lower()]

                if key in seen:
                    return m.group(1)

                seen.add(key)
                return f'<span class="term" data-term="{key}" tabindex="0" role="button">{m.group(1)}</span>'

            out.append(_TERM_RE.sub(wrap, part))

    return "".join(out)


def term(key: str, text: str = "") -> str:
    """Inline clickable term for use inside your own HTML: theme.term('roc_auc')."""

    g = GLOSSARY[key]

    return f'<span class="term" data-term="{key}" tabindex="0" role="button">{html.escape(text or g["words"][0])}</span>'


def md(text: str):
    """st.markdown with glossary terms made clickable (plain text/markdown in, safe to mix with HTML)."""

    st.markdown(glossify(text), unsafe_allow_html=True)


# ============================================================
# MOTION SCRIPT LOADER
# ============================================================
# Streamlit's markdown cannot run scripts, so the motion engine runs in a zero-size component iframe
# and reaches the page through window.parent (see assets/motion.js).

def _gsap_tag() -> str:
    local = ASSETS / "vendor" / "gsap.min.js"

    if local.exists():
        return f"<script>{local.read_text(encoding='utf-8')}</script>"

    return f'<script src="{GSAP_CDN}"></script>'


def _motion_html() -> str:
    glossary = json.dumps(_glossary_payload(), ensure_ascii=True).replace("</", "<\\/")
    js = (ASSETS / "motion.js").read_text(encoding="utf-8")

    return f"{_gsap_tag()}<script>const GLOSSARY = {glossary};</script><script>{js}</script>"


def inject(theme=DEFAULT_THEME) -> dict:
    """Write the CSS for the chosen theme + start the motion engine; returns the matplotlib palette."""

    name = resolve(theme)

    css = _root_vars(name) + _CSS

    # markdown stops an HTML block at a blank line, so drop them
    css = "\n".join(line for line in css.splitlines() if line.strip())

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    try:
        with st.container(key="pf_enh"):
            if hasattr(st, "iframe"):  # Streamlit >= 1.5x: components.v1.html is deprecated
                st.iframe(_motion_html(), height=1)
            else:
                components.html(_motion_html(), height=0)
    except Exception:
        pass  # motion is decoration: never block the dashboard

    return THEMES[name]


# ============================================================
# SMALL HTML COMPONENTS
# ============================================================

_GEAR = (
    '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true">'
    '<circle cx="24" cy="24" r="16" stroke="currentColor" stroke-width="6" stroke-dasharray="5.03 5.03"/>'
    '<circle cx="24" cy="24" r="12" stroke="currentColor" stroke-width="3.5"/>'
    '<circle cx="24" cy="24" r="4.5" fill="currentColor"/></svg>'
)


def banner(title: str, right: str = "", subtitle: str = ""):
    chips = '<span class="pf-chip"><i class="pf-dot"></i>Live model</span>'

    if right:
        chips += f'<span class="pf-chip">{html.escape(right)}</span>'

    sub = f'<div class="sub">{glossify(html.escape(subtitle))}</div>' if subtitle else ""

    st.markdown(
        f'<div class="pf-banner"><div class="l"><div class="mark">{_GEAR}</div>'
        f'<div><div class="t">{html.escape(title)}</div>{sub}</div></div>'
        f'<div class="r">{chips}</div></div>',
        unsafe_allow_html=True,
    )


def sidebar_brand(title: str, status: str = "System online"):
    st.markdown(
        f'<div class="pf-brand"><div class="pf-mark">{_GEAR}</div>'
        f'<div><div class="pf-brand-t">{html.escape(title)}</div>'
        f'<div class="pf-brand-s"><i class="pf-dot"></i>{html.escape(status)}</div></div></div>',
        unsafe_allow_html=True,
    )


def swatches(theme):
    """Small colour strip that previews the active theme in the sidebar."""

    p = PALETTES[resolve(theme)]

    chips = "".join(
        f'<i title="{k}" style="background:{p[k]};animation-delay:{i * 0.05:.2f}s"></i>'
        for i, k in enumerate(["bg", "card", "brand", "brand_hi", "accent", "ok_fg"])
    )

    st.markdown(f'<div class="pf-swatches">{chips}</div>', unsafe_allow_html=True)


def title(text: str):
    st.markdown(f'<div class="pf-title">{glossify(html.escape(text))}</div>', unsafe_allow_html=True)


def kpi_row(items):
    """items = [(label, value, sub), ...] -> one card per column."""

    cols = st.columns(len(items))

    for col, item in zip(cols, items):
        label, value, *rest = item
        sub = rest[0] if rest else ""

        col.markdown(
            f'<div class="pf-kpi">'
            f'<div class="l">{glossify(html.escape(str(label)))}</div>'
            f'<div class="v">{html.escape(str(value))}</div>'
            f'<div class="s">{glossify(html.escape(str(sub)))}</div></div>',
            unsafe_allow_html=True,
        )


def flow_bar(step: int, labels):
    """Segmented progress rail for the page tabs. step is 0-based; labels = list of page names."""

    total = len(labels)

    bars = "".join(
        f'<i class="{"on" if i <= step else ""}{" cur" if i == step else ""}" style="--i:{i}"></i>' for i in range(total)
    )

    st.markdown(
        f'<div class="pf-flow"><div class="pf-flow-t"><b>Step {step + 1} of {total}</b>'
        f'<span>{html.escape(str(labels[step]))}</span></div><div class="pf-flow-b">{bars}</div></div>',
        unsafe_allow_html=True,
    )


def result_box(level: str, heading: str, detail: str, probability=None, label=None):
    """
    level: ok | warn | bad
    probability: optional 0..1 -> shows an animated gauge ring next to the message
    label: text inside the ring (defaults to the probability as a percentage)
    """

    gauge = ""

    if probability is not None:
        p = min(max(float(probability), 0.0), 1.0)

        text = label or (f"{p * 100:.0f}%" if p >= 0.01 else f"{p * 100:.1f}%")

        gauge = (
            '<div class="pf-gauge"><svg viewBox="0 0 120 120">'
            '<circle class="trk" cx="60" cy="60" r="50"/>'
            f'<circle class="val" cx="60" cy="60" r="50" pathLength="100" '
            f'stroke-dasharray="100" stroke-dashoffset="{100 - p * 100:.2f}"/></svg>'
            f'<div class="num">{html.escape(text)}</div></div>'
        )

    st.markdown(
        f'<div class="pf-result {level}{"" if gauge else " nogauge"}">{gauge}'
        f'<div><div class="h">{html.escape(heading)}</div>'
        f'<div class="d">{html.escape(detail)}</div></div></div>',
        unsafe_allow_html=True,
    )