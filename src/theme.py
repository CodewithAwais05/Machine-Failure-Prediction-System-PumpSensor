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
  * motion is CSS only (entrance rise, hover glow, button sheen, gauge ring, aurora background)
    plus one tiny script (_ENHANCER) for the things CSS cannot do: KPI count-up, cursor spotlight
    on cards and button ripple. If the script is blocked the page still works - numbers just
    appear without counting.
  * everything respects prefers-reduced-motion.

Pair this file with .streamlit/config.toml (base = "dark", primaryColor = BASE_PRIMARY): sliders
and toggles take their colour from the Streamlit theme and are hue-shifted per theme here.
"""

import colorsys
import html

import streamlit as st
import streamlit.components.v1 as components

from src.eda import THEMES

# primaryColor written in .streamlit/config.toml - used to hue-shift native sliders/toggles
BASE_PRIMARY = "#C65A7D"

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
        f"color-scheme:{p['mode']};"
        "}"
    )


# ============================================================
# STYLESHEET
# ============================================================

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Sora:wght@500;600;700&display=swap');
@property --glow { syntax: '<number>'; inherits: false; initial-value: 0; }

@keyframes pfRise   { from { opacity: 0; transform: translateY(18px) scale(.985); filter: blur(6px); } to { opacity: 1; transform: none; filter: none; } }
@keyframes pfFade   { from { opacity: 0; } to { opacity: 1; } }
@keyframes pfImg    { from { opacity: 0; transform: scale(.985); filter: blur(8px); } to { opacity: 1; transform: none; filter: none; } }
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
html { scroll-behavior: smooth; }
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
    background-size: 200% 100%; animation: pfFlow 6s linear infinite;
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
    animation: pfRise .8s cubic-bezier(.16,1,.3,1) backwards;
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
    animation: pfRise .85s var(--d) cubic-bezier(.16,1,.3,1) backwards;
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
[data-testid="stExpander"] details { background: var(--pf-card); border: 1px solid var(--pf-border); border-radius: 14px; transition: border-color .3s ease, background-color .5s ease; animation: pfRise .8s .1s cubic-bezier(.16,1,.3,1) backwards; }
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
[data-stale="true"] { opacity: .55 !important; transition: opacity .25s ease !important; }

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

@media (max-width: 900px) {
    .pf-banner { flex-direction: column; align-items: flex-start; padding: 1.1rem 1.2rem; }
    .pf-banner .t { font-size: 1.25rem; }
    .pf-result { grid-template-columns: 1fr; justify-items: start; }
    [class*="st-key-panel"] { padding: 1rem 1rem 1.2rem; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; } .pf-kpi .v, .pf-gauge .num { opacity: 1 !important; } }
"""


# ============================================================
# SMALL SCRIPT: count-up numbers, cursor spotlight, button ripple
# ============================================================
# Streamlit's markdown cannot run scripts, so this runs in a zero-size component iframe and
# reaches the page through window.parent. It is optional: if it fails nothing breaks.

_ENHANCER = """
<script>
(function () {
  var P, D;
  try { P = window.parent; D = P.document; } catch (e) { return; }
  try { if (P.__pfCleanup) P.__pfCleanup(); } catch (e) {}

  var reduce = P.matchMedia && P.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ease = function (t) { return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t); };

  function countUp(el) {
    if (el.dataset.pfDone) return;
    el.dataset.pfDone = '1';
    var txt = el.textContent.trim();
    var m = /^(-?)([\\d,]*\\.?\\d+)(%?)$/.exec(txt);
    if (!m || reduce) return;
    var raw = m[2], grouped = raw.indexOf(',') > -1, dec = (raw.split('.')[1] || '').length;
    var to = parseFloat(raw.replace(/,/g, '')) * (m[1] ? -1 : 1);
    var dur = Math.min(1500, 750 + Math.log10(Math.abs(to) + 1) * 150), t0 = null;
    var fmt = function (v) {
      return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: grouped }) + m[3];
    };
    el.textContent = fmt(0);
    (function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur);
      if (k < 1) { el.textContent = fmt(to * ease(k)); P.requestAnimationFrame(step); }
      else { el.textContent = txt; }
    })(P.performance.now());
  }

  var queued = false;
  function scan() {
    queued = false;
    var nodes = D.querySelectorAll('.pf-kpi .v:not([data-pf-done]), .pf-gauge .num:not([data-pf-done])');
    for (var i = 0; i < nodes.length; i++) countUp(nodes[i]);
  }
  var mo = new P.MutationObserver(function () {
    if (!queued) { queued = true; P.requestAnimationFrame(scan); }
  });
  mo.observe(D.body, { childList: true, subtree: true });
  scan();

  var SPOT = '.pf-kpi, [class*="st-key-panel"]';
  function onMove(e) {
    var t = e.target && e.target.closest ? e.target.closest(SPOT) : null;
    if (!t) return;
    var r = t.getBoundingClientRect();
    t.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    t.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }
  function onDown(e) {
    var b = e.target && e.target.closest ? e.target.closest('.stButton > button, .stDownloadButton > button') : null;
    if (!b || reduce) return;
    var r = b.getBoundingClientRect(), s = Math.max(r.width, r.height) * 2;
    var d = D.createElement('span');
    d.className = 'pf-ripple';
    d.style.cssText = 'width:' + s + 'px;height:' + s + 'px;left:' + (e.clientX - r.left - s / 2) + 'px;top:' + (e.clientY - r.top - s / 2) + 'px';
    b.appendChild(d);
    setTimeout(function () { d.remove(); }, 700);
  }
  D.addEventListener('pointermove', onMove, { passive: true });
  D.addEventListener('pointerdown', onDown, { passive: true });

  P.__pfCleanup = function () {
    mo.disconnect();
    D.removeEventListener('pointermove', onMove);
    D.removeEventListener('pointerdown', onDown);
  };
})();
</script>
"""


def inject(theme=DEFAULT_THEME) -> dict:
    """Write the CSS for the chosen theme; returns the matplotlib palette of that theme."""

    name = resolve(theme)

    css = _root_vars(name) + _CSS

    # markdown stops an HTML block at a blank line, so drop them
    css = "\n".join(line for line in css.splitlines() if line.strip())

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    with st.container(key="pf_enh"):
        components.html(_ENHANCER, height=0)

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

    sub = f'<div class="sub">{html.escape(subtitle)}</div>' if subtitle else ""

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
    st.markdown(f'<div class="pf-title">{html.escape(text)}</div>', unsafe_allow_html=True)


def kpi_row(items):
    """items = [(label, value, sub), ...] -> one card per column."""

    cols = st.columns(len(items))

    for i, (col, item) in enumerate(zip(cols, items)):
        label, value, *rest = item
        sub = rest[0] if rest else ""

        col.markdown(
            f'<div class="pf-kpi" style="animation-delay:{i * 0.07:.2f}s">'
            f'<div class="l">{html.escape(str(label))}</div>'
            f'<div class="v">{html.escape(str(value))}</div>'
            f'<div class="s">{html.escape(str(sub))}</div></div>',
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