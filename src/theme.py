"""CSS for the SensorGuard dashboard (maroon brand, light + dark)."""

PALETTES = {
    "light": {
        "bg": "#F4F5F7",
        "card": "#FFFFFF",
        "card2": "#F8F9FB",
        "text": "#1B1B22",
        "muted": "#5E6370",
        "border": "#E3E5EA",
        "maroon": "#6B1E33",
        "maroon_dark": "#561523",
        "maroon_hover": "#7D2540",
        "accent": "#6B1E33",
        "ok_bg": "#DCF5E8",
        "ok_fg": "#0A5C3A",
        "warn_bg": "#FFF1D6",
        "warn_fg": "#7A4A00",
        "bad_bg": "#FBE0E5",
        "bad_fg": "#8A1230",
        "shadow": "0 1px 3px rgba(20,20,40,.08)",
        "df_filter": "none",
    },
    "dark": {
        "bg": "#141218",
        "card": "#1F1B25",
        "card2": "#2A2531",
        "text": "#ECE8F0",
        "muted": "#A39DAE",
        "border": "#342E3C",
        "maroon": "#6B1E33",
        "maroon_dark": "#7A2440",
        "maroon_hover": "#8E2C4D",
        "accent": "#C65A7D",
        "ok_bg": "#12382A",
        "ok_fg": "#7BE0B0",
        "warn_bg": "#3D2E10",
        "warn_fg": "#F3C26B",
        "bad_bg": "#43161F",
        "bad_fg": "#FF9DB1",
        "shadow": "0 1px 3px rgba(0,0,0,.5)",
        "df_filter": "invert(0.9) hue-rotate(180deg)",
    },
}

_STATIC = """
.stApp { background: var(--bg); color: var(--text); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; max-width: 1400px; }

[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--border); }

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp p, .stApp li,
.stApp label, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stMarkdownContainer"] {
    color: var(--text);
}
.stApp [data-testid="stCaptionContainer"], .stApp small { color: var(--muted); }

/* ---------- header banner ---------- */
.sg-header {
    background: var(--maroon); color: #fff !important;
    padding: 1.15rem 1.6rem; border-radius: 6px; margin-bottom: 1.1rem;
    font-weight: 700; font-size: 1.55rem; letter-spacing: .1px;
    display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
}
.sg-header span.sg-sub { font-size: .85rem; font-weight: 500; opacity: .85; }
.sg-chip {
    display: inline-block; padding: .15rem .65rem; border-radius: 999px; font-size: .75rem; font-weight: 600;
    background: rgba(255,255,255,.18); color: #fff !important; margin-left: .4rem;
}

/* ---------- KPI cards ---------- */
.kpi {
    background: var(--card); border: 1px solid var(--border); border-top: 3px solid var(--accent);
    border-radius: 8px; padding: 1.05rem 1.3rem; box-shadow: var(--shadow); height: 100%;
}
.kpi .kpi-label { color: var(--muted); font-size: .92rem; }
.kpi .kpi-value { color: var(--text); font-size: 2.1rem; font-weight: 700; line-height: 1.25; }
.kpi .kpi-sub { color: var(--muted); font-size: .78rem; margin-top: .1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ---------- panels (st.container(key="panel_...")) ---------- */
[class*="st-key-panel"] {
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    padding: 1.2rem 1.4rem; margin-bottom: 1rem; box-shadow: var(--shadow);
}
.panel-title { font-size: 1.15rem; font-weight: 700; color: var(--text); margin: 0 0 .7rem 0; }

/* ---------- buttons ---------- */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseButton-primaryFormSubmit"] {
    background: var(--maroon_dark); color: #fff; border: 0; border-radius: 6px; font-weight: 600;
}
[data-testid="stBaseButton-secondary"] p, [data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-secondaryFormSubmit"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: #fff !important; }
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-secondaryFormSubmit"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: var(--maroon_hover); color: #fff; border: 0;
}
[data-testid="stFormSubmitButton"] button { width: 100%; padding: .7rem 1rem; }

/* ---------- inputs (old baseweb markup + newer react-aria markup) ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"],
[data-testid="stNumberInputContainer"], [data-testid="stTextInputRootElement"],
[data-testid="stSelectbox"] [role="group"], [data-testid="stMultiSelect"] [role="group"] {
    background: var(--card2) !important; border-color: var(--border) !important;
}
.stApp input, .stApp textarea { color: var(--text) !important; -webkit-text-fill-color: var(--text) !important; background: transparent !important; }
[data-baseweb="select"] *, [data-testid="stSelectbox"] button, [data-testid="stMultiSelect"] button { color: var(--text); }
[data-baseweb="popover"] ul, [data-baseweb="menu"], [data-baseweb="popover"] > div,
[role="listbox"], [data-testid="stSelectboxVirtualDropdown"] { background: var(--card) !important; color: var(--text) !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li *, [role="option"], [role="option"] * { color: var(--text) !important; }
[data-baseweb="popover"] li:hover, [role="option"]:hover, [role="option"][data-focused="true"] { background: var(--card2) !important; }
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {
    background: var(--card2) !important; color: var(--text) !important; border-color: var(--border) !important;
}
[data-testid="stFileUploaderDropzone"] { background: var(--card2); border-color: var(--border); }
[data-testid="stFileUploaderDropzone"] * { color: var(--muted); }

/* ---------- pill navigation (st.radio horizontal) ---------- */
div[role="radiogroup"] { gap: .5rem; flex-wrap: wrap; }
[data-testid="stRadioOption"], div[role="radiogroup"] > label {
    background: var(--card); border: 1px solid var(--border); border-radius: 999px;
    padding: .3rem 1.05rem; cursor: pointer; margin: 0;
}
[data-testid="stRadioOption"] > div > div:first-child, div[role="radiogroup"] > label > div:first-child { display: none; }
[data-testid="stRadioOption"][data-selected="true"], div[role="radiogroup"] > label:has(input:checked) {
    background: var(--maroon); border-color: var(--maroon);
}
[data-testid="stRadioOption"][data-selected="true"] *, div[role="radiogroup"] > label:has(input:checked) * { color: #fff !important; }
[data-testid="stRadioOption"]:hover { border-color: var(--accent); }

/* ---------- misc ---------- */
[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--border); border-radius: 8px; }
[data-testid="stExpander"] summary * { color: var(--text); }
[data-testid="stDataFrame"] { filter: var(--df_filter); }
[data-testid="stImage"] img { border-radius: 6px; }
hr { border-color: var(--border) !important; }

/* ---------- risk result box ---------- */
.result { border-radius: 8px; padding: 1rem 1.3rem; margin-top: 1rem; }
.result .result-title { font-size: 1.25rem; font-weight: 700; }
.result .result-sub { font-size: .98rem; margin-top: .15rem; }
.result.ok   { background: var(--ok_bg);   color: var(--ok_fg); }
.result.warn { background: var(--warn_bg); color: var(--warn_fg); }
.result.bad  { background: var(--bad_bg);  color: var(--bad_fg); }
.result * { color: inherit !important; }
"""


def get_css(mode: str = "light") -> str:
    p = PALETTES["dark" if mode == "dark" else "light"]

    variables = ";".join(f"--{k}:{v}" for k, v in p.items())

    # CSS custom properties cannot contain "-"-less keys with underscores in var() names
    # used above, so both spellings are declared.
    variables += ";" + ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in p.items())

    css = _STATIC.replace("var(--maroon_dark)", "var(--maroon-dark)") \
                 .replace("var(--maroon_hover)", "var(--maroon-hover)")

    return f"<style>:root{{{variables}}}{css}</style>"