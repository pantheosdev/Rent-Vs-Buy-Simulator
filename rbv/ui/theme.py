# Minimal UI theme helpers (modular split)

# --- Theme constants (Azure B + warm orange; Phase 3 contrast tune) ---
BUY_COLOR = "#3D9BFF"
RENT_COLOR = "#E6B800"

BG_BLACK = "#000000"
SURFACE_CARD = "#1A1A1A"
SURFACE_INPUT = "#2A2A2A"
BORDER = "#333333"
TEXT_MUTED = "#9A9A9A"


# Consolidated stylesheet (Phase 3C): single injection point.
# NOTE: This is intentionally kept as one ordered CSS string to reduce brittle
# multiple-injection interactions with Streamlit/BaseWeb. Later rules override earlier ones.
_RBV_GLOBAL_CSS_RAW = r""":root{
  --rbv-font-sans: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  --rbv-font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --rbv-space-1: 8px;
  --rbv-space-2: 12px;
  --rbv-space-3: 16px;
  --rbv-space-4: 24px;
  --rbv-space-5: 32px;
}

/* --- Global typography (Sprint 1) --- */
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"]{
  font-family: var(--rbv-font-sans) !important;
  font-size: 13px !important;
  line-height: 1.35 !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
code, pre, kbd, samp{
  font-family: var(--rbv-font-mono) !important;
}
body, .stMarkdown, .stText, .stCaption, .stDataFrame, .stTable{
  font-variant-numeric: tabular-nums;
}

/* --- Tabs nav (radio styled as tabs; Sprint 1) --- */
.st-key-rbv_tab_nav div[role="radiogroup"]{
  display:flex !important;
  flex-wrap: nowrap !important;
  justify-content: center !important;
  overflow-x: auto !important;
  scrollbar-width: none; /* Firefox */
  gap: 10px !important;
  padding: 6px 8px !important;
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 14px !important;
}
.st-key-rbv_tab_nav div[role="radiogroup"]::-webkit-scrollbar{ display:none; height:0; }
.st-key-rbv_tab_nav div[data-baseweb="radio"]{ margin: 0 !important; }
.st-key-rbv_tab_nav input{ display:none !important; }
.st-key-rbv_tab_nav label{
  padding: 7px 10px !important;
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.00) !important;
  background: transparent !important;
  color: rgba(241,241,243,0.78) !important;
  font-weight: 600 !important;
  font-size: 0.90rem !important;
  letter-spacing: 0.01em !important;
  white-space: nowrap !important;   /* keep each tab label on one line */
  display: inline-flex !important;
  align-items: center !important;
}
.st-key-rbv_tab_nav label:has(input:checked){
  background: rgba(61,155,255,0.12) !important;
  border-color: rgba(61,155,255,0.35) !important;
  color: rgba(247,250,255,0.96) !important;
  box-shadow: 0 10px 22px rgba(0,0,0,0.35) !important;
}
@media (max-width: 900px){
  .st-key-rbv_tab_nav div[role="radiogroup"]{ flex-wrap: nowrap !important; overflow-x:auto !important; }
}

.rbv-label-row{
  display:flex; align-items:center; justify-content:space-between;
  gap:10px; margin: 10px 0 6px 0;
  min-height: 20px;
  overflow: visible;
}
.rbv-label-text{
  font-weight: 500;
  font-size: 0.95rem;
  color: rgba(241,241,243,0.92);
  line-height: 1.2;
}
.rbv-help{ position:relative; display:inline-flex; align-items:center; justify-content:center; overflow: visible; z-index: 1000000; }
.rbv-help:hover{ z-index: 1000001; }
.rbv-help-icon{
  width:18px; height:18px; border-radius:50%;
  border:1px solid rgba(255,255,255,0.18);
  color: rgba(241,241,243,0.86);
  background: rgba(255,255,255,0.06);
  font-size:12px; font-weight:700; line-height:18px; text-align:center;
  display:inline-block;
}

/* Micro-alignment pass: ensure wrapped widgets sit tight under label rows (no uneven Streamlit margins) */
.rbv-label-row + div[data-testid="stNumberInput"],
.rbv-label-row + div[data-testid="stSelectbox"],
.rbv-label-row + div[data-testid="stTextInput"],
.rbv-label-row + div[data-testid="stSlider"],
.rbv-label-row + div[data-testid="stRadio"],
.rbv-label-row + div[data-testid="stCheckbox"]{
  margin-top: 0 !important;
}
.rbv-label-row + div[data-testid="stCheckbox"]{
  padding-top: 2px !important;
}
.rbv-label-row + div[data-testid="stCheckbox"] label,
.rbv-label-row + div[data-testid="stCheckbox"] div[data-baseweb="checkbox"]{
  display:flex !important;
  align-items:center !important;
}

.rbv-help-icon.rbv-sm{
  width:16px; height:16px; line-height:16px;
  font-size:11px;
}
.rbv-help-bubble.rbv-sm-bubble{
  top: 24px;
  width: 280px;
}

.rbv-help-bubble {
  display: none;
  position: absolute;
  top: 28px;
  right: 0px;
  left: auto;
  transform: translateX(-6px);
  z-index: 999999;
  background: #141417;
  color: #E6EDF7;
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 12px;
  line-height: 1.35;
  width: 260px;
  max-height: 45vh;
  /* Allow full message visibility + scrolling on long tooltips */
  overflow: auto;
  max-width: min(280px, 86vw);
  box-shadow: 0 16px 40px rgba(0,0,0,0.65);
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  hyphens: auto;
  text-transform: none;
  letter-spacing: normal;
  font-weight: 500;
}
.rbv-help:hover .rbv-help-bubble{ display:block; }

/* Tooltip auto-flip (JS adds .rbv-tip-up on the wrapper when near viewport bottom) */
.rbv-help.rbv-tip-up .rbv-help-bubble{
  top: auto;
  bottom: 28px;
}
.rbv-help.rbv-tip-up .rbv-help-bubble.rbv-sm-bubble{
  top: auto;
  bottom: 24px;
}

/* Tooltip horizontal flip (JS adds .rbv-tip-left when bubble would overflow the left viewport edge) */
.rbv-help.rbv-tip-left .rbv-help-bubble{
  left: 0px;
  right: auto;
  transform: translateX(6px);
}

/* Prevent clipping: allow custom tooltip bubbles to overflow layout containers */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div,
div[data-testid="stMainBlockContainer"],
div[data-testid="stMainBlockContainer"] div[data-testid="stVerticalBlock"],
div[data-testid="stMainBlockContainer"] div[data-testid="stVerticalBlock"] > div{
  overflow: visible !important;
}

@media (max-width: 600px){
  .rbv-help-bubble{ max-width: min(340px, 92vw) !important; }
}

/* Tooltip final override: keep bubbles readable (no ALL CAPS) */
.rbv-help-bubble{ text-transform: none !important; letter-spacing: normal !important; font-size: 12px !important; font-weight: 500 !important; }


/* --- FINAL TOOLTIP HARDENING (v144) ---
   Goal: stop any transparent tooltip bubbles in sidebar/help icons.
   We force an opaque bubble with padding on the innermost tooltip surface. */
div[data-testid="stTooltipContent"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
body div[data-baseweb="tooltip"], body div[data-baseweb="popover"]{
  z-index: 1000000 !important;
}
body div[data-baseweb="tooltip"] div[role="tooltip"]{ z-index: 1000000 !important; }
body div[data-baseweb="popover"] div[role="tooltip"]{ z-index: 1000000 !important; }
body div[data-baseweb="tooltip"] div[role="tooltip"] > div,
body div[data-baseweb="popover"] div[role="tooltip"] > div{
  background: #141417 !important;
  opacity: 1 !important;
  color: #E6EDF7 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 12px !important;
  padding: 14px 16px !important;
  line-height: 1.35 !important;
  max-width: min(320px, 86vw) !important;
  box-shadow: 0 16px 40px rgba(0,0,0,0.70) !important;
  backdrop-filter: none !important;
  mix-blend-mode: normal !important;
}
body div[data-baseweb="tooltip"] div[role="tooltip"] > div p,
body div[data-baseweb="popover"] div[role="tooltip"] > div p{
  margin: 0 !important;
}


/* --- Sidebar: hide ALL built-in help icons (we keep detailed notes in Model Assumptions) --- */
section[data-testid="stSidebar"] [data-testid="stTooltipIcon"],
section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] *,
section[data-testid="stSidebar"] button[aria-label*="Help"],
section[data-testid="stSidebar"] button[aria-label*="help"],
section[data-testid="stSidebar"] button[aria-label*="tooltip"],
section[data-testid="stSidebar"] button[title*="Help"],
section[data-testid="stSidebar"] button[title*="help"],
section[data-testid="stSidebar"] button[title*="tooltip"],
section[data-testid="stSidebar"] [aria-label*="Help"],
section[data-testid="stSidebar"] [aria-label*="help"]{
  display: none !important;
}

/* --- Sidebar width: slightly wider to reduce wrapping (desktop only) --- */
section[data-testid="stSidebar"]{
  min-width: 340px !important;
  width: 340px !important;
  flex: 0 0 340px !important;
}
section[data-testid="stSidebar"] > div:first-child{
  width: 340px !important;
}
@media (max-width: 900px){
  section[data-testid="stSidebar"]{
    min-width: 0 !important;
    width: 100% !important;
    flex: 1 1 auto !important;
  }
  section[data-testid="stSidebar"] > div:first-child{
    width: 100% !important;
  }
}

/* Sidebar scrolling + tooltip escape (hotfix2)
   - Keep sidebar vertically scrollable (regression fix).
   - Avoid clipping our custom tooltip bubbles inside BaseWeb expander panels.
   Note: any ancestor with overflow-y:auto will clip; we therefore keep scroll on the
   outer sidebar wrapper but force expander internals to allow overflow + high z-index.
*/
section[data-testid="stSidebar"]{
  overflow: hidden !important;
}
section[data-testid="stSidebar"] > div:first-child{
  height: 100vh !important;
  overflow-y: auto !important;
  overflow-x: visible !important;
}
/* Allow bubbles to escape expander internals */
section[data-testid="stSidebar"] div[data-testid="stExpander"],
section[data-testid="stSidebar"] div[data-testid="stExpander"] * ,
section[data-testid="stSidebar"] details,
section[data-testid="stSidebar"] details *{
  overflow: visible !important;
}

/* ================= RBV CSS BLOCK ================= */

/* Streamlit wrapper: keep transparent to avoid double-box */
div[data-testid="stTooltipContent"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Bring tooltips/popovers above sidebar content */
div[data-baseweb="tooltip"], div[data-baseweb="popover"]{ z-index: 1000000 !important; }
div[data-baseweb="tooltip"] div[role="tooltip"],
div[data-baseweb="popover"] div[role="tooltip"]{
  z-index: 1000001 !important;
  opacity: 1 !important;
  backdrop-filter: none !important;
  mix-blend-mode: normal !important;
}

/* The actual bubble */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div{
  background: #141417 !important; /* fully opaque */
  color: #E6EDF7 !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 12px !important;
  padding: 12px 14px !important; /* keep text away from corners */
  max-width: 280px !important;   /* smaller than sidebar */
  line-height: 1.35 !important;
  box-shadow: 0 16px 40px rgba(0,0,0,0.65) !important;
  overflow-wrap: break-word !important;
  word-break: normal !important;
}

/* Inner nodes should not overwrite bubble background */
div[data-baseweb="tooltip"] div[role="tooltip"] > div * ,
div[data-baseweb="popover"] div[role="tooltip"] > div * {
  background: transparent !important;
  color: #E6EDF7 !important;
}

div[data-baseweb="tooltip"] div[role="tooltip"] p,
div[data-baseweb="popover"] div[role="tooltip"] p{
  margin: 0 !important;
}

/* ================= RBV CSS BLOCK ================= */

    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

    :root{ --rbv-font: 'Roboto', sans-serif; }

    /* GLOBAL RESET & BACKGROUND */
    html, body, .stApp { font-family: var(--rbv-font) !important; }

    /* Apply Roboto broadly (inheritance handles most widget text); DO NOT force spans,
       because Streamlit/BaseWeb uses span-based ligature glyphs for icons (e.g. expander arrows). */
    .stApp :is(p, label, input, textarea, button, select, option, h1,h2,h3,h4,h5,h6, th, td, li, a, small, strong, em) {
        font-family: var(--rbv-font) !important;
    }

    /* Ensure Streamlit/BaseWeb icon ligatures render as glyphs, not raw text like "arrow_drop_down" */
    .material-icons,
    .material-symbols-outlined,
    .material-symbols-rounded,
    .material-symbols-sharp,
    [data-baseweb="icon"],
    [data-testid*="Icon"],
    span[translate="no"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        font-variation-settings: 'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 20;
        letter-spacing: normal !important;
        text-transform: none !important;
    }
    code, pre, kbd, samp { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important; }
    .stApp { background-color: #000000; color: #F1F1F3; }
    

/* --- MAIN TITLE BANNER --- */
.title-banner{
    width: 100%;
    text-align: center;
    padding: 18px 16px;
    margin: 14px 0 18px 0;
    border-radius: 18px;
    font-weight: 900;
    letter-spacing: 0.03em;
    font-size: 1.55rem;
    color: #F7FAFF;
    background:
        linear-gradient(90deg, rgba(61,155,255,0.18) 0%, rgba(230,184,0,0.14) 100%),
        radial-gradient(80% 120% at 50% 0%, rgba(61,155,255,0.18) 0%, rgba(0,0,0,0.0) 70%),
        linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255,255,255,0.14);
    box-shadow: 0 18px 44px rgba(0,0,0,0.55);
}
@media (max-width: 768px){
    .title-banner{ font-size: 1.25rem; padding: 14px 12px; border-radius: 16px; }
}


/* --- DISCLAIMER BANNER (above the fold) --- */
.rbv-disclaimer{
  display:flex;
  align-items:flex-start;
  gap:12px;
  padding: 12px 14px;
  margin: 0 0 14px 0;
  border-radius: 16px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 16px 36px rgba(0,0,0,0.50);
}
.rbv-disclaimer .rbv-disclaimer-badge{
  flex: 0 0 auto;
  font-weight: 800;
  letter-spacing: 0.02em;
  font-size: 0.82rem;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(230,184,0,0.12);
  border: 1px solid rgba(230,184,0,0.35);
  color: rgba(255,244,204,0.95);
}
.rbv-disclaimer .rbv-disclaimer-text{
  color: rgba(241,241,243,0.88);
  font-size: 0.92rem;
  line-height: 1.35;
}
.rbv-disclaimer .rbv-disclaimer-text b{
  color: rgba(247,250,255,0.96);
  font-weight: 800;
}

/* TOP HEADER / TOOLBAR (keep hamburger visible, remove white strip) */
    header[data-testid="stHeader"] { background: #000000 !important; }
    header[data-testid="stHeader"] * { color: #E2E8F0 !important; }
    div[data-testid="stToolbar"] { background: transparent !important; }
    /* Toolbar (...) menu popovers */
    div[data-testid="stToolbar"] [role="menu"] {
        background: #1A1A1A !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 16px 32px rgba(0,0,0,0.55) !important;
    }
    div[data-testid="stToolbar"] [role="menuitem"] {
        color: #E2E8F0 !important;
    }
    div[data-testid="stToolbar"] [role="menuitem"]:hover,
    div[data-testid="stToolbar"] [role="menuitem"][aria-selected="true"] {
        background: rgba(255,255,255,0.08) !important;
        color: #E2E8F0 !important;
    }
    div[data-testid="stToolbar"] [role="menuitem"] * { color: inherit !important; }
    /* Reduce header padding */
    header[data-testid="stHeader"] { padding-top: 0.25rem !important; padding-bottom: 0.25rem !important; }
    
    /* SIDEBAR BACKGROUND */
    section[data-testid="stSidebar"] {
        background-color: #1A1A1A;
        border-right: 1px solid rgba(255,255,255,0.10);
    }
    
    /* REMOVE TOP WHITE GAP */
    .block-container {
        padding-top: 2.10rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px;
    }
    /* header left visible so sidebar toggle works */
    /* --- SIDEBAR HEADERS (Adjusted Spacing) --- */
    .sidebar-header-gen {
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        text-transform: none !important;
        color: #F1F1F3 !important;
        margin-top: 10px;
        margin-bottom: 12px; 
        background: transparent !important;
    }
    .sidebar-header-buy {
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        text-transform: none !important;
        color: var(--buy, #2F8BFF) !important;
        margin-top: 10px; 
        margin-bottom: 12px;
        background: transparent !important;
    }
    .sidebar-header-rent {
        font-size: 22px !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        text-transform: none !important;
        color: var(--rent, #E6B800) !important;
        margin-top: 10px;
        margin-bottom: 12px;
        background: transparent !important;
    }

    /* --- TEXT COLORS --- */
    h1, h2, h3, h4, h5, h6, 
    .stMarkdown p, .stMarkdown label, 
    div[data-testid="stInputLabel"], 
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stCaptionContainer"] p,
    div[role="radiogroup"] p,
    label, span, small {
        color: #F8FAFC !important; /* Bright White */
        opacity: 1 !important;
    }
    
    /* TITLE CENTERING */
    h1 {
        text-align: center !important;
        width: 100% !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: block !important;
        margin-bottom: 30px !important;
    }

    
    
    /* --- HELP / TOOLTIP ICONS (SIDEBAR + MAIN) --- */
    /* Goal: remove Streamlit's extra wrapper styling to avoid double-boxes, but DO NOT override BaseWeb's
       native tooltip bubble (keeps it stable across Streamlit versions). */

    div[data-testid="stTooltipContent"]{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      margin: 0 !important;
    }

    /* Keep tooltip layers above the sidebar */
    div[data-baseweb="tooltip"],
    div[data-baseweb="popover"]{
      z-index: 100000 !important;
    }

    /* Keep the help icon consistent */
    div[data-testid="stTooltipIcon"]{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      width:18px;
      height:18px;
      border-radius:999px;
      border:1px solid rgba(148,163,184,0.40);
      color: rgba(226,232,240,0.85);
      background: rgba(255,255,255,0.06);
      margin-left: 6px;
      transform: translateY(1px);
    }
    div[data-testid="stTooltipIcon"]:hover{
      border-color: rgba(255,255,255,0.34);
      color: rgba(255,255,255,0.95);
      background: rgba(255,255,255,0.08);
    }
    div[data-testid="stTooltipIcon"] svg{ width:14px !important; height:14px !important; }

/* --- SELECTBOX / DROPDOWN MENU (BaseWeb) --- */
/* Streamlit's select menus render inside a BaseWeb popover portal. We force the menu + options
   to use the app's dark theme (background + readable text + hover/selected states). */
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] div[role="listbox"],
div[data-baseweb="popover"] div[data-baseweb="menu"] {
    background: #141417 !important;
    color: #E6EDF7 !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* Fix Streamlit element "..." menus (BaseWeb): prevent inverted hover (white highlight + invisible text). */
div[data-baseweb="menu"],
div[data-baseweb="popover"] div[data-baseweb="menu"]{
  background: #141417 !important;
  color: #E6EDF7 !important;
}
div[data-baseweb="menu"] [role="menuitem"],
div[data-baseweb="menu"] li{
  color: #E6EDF7 !important;
  background: transparent !important;
}
div[data-baseweb="menu"] [role="menuitem"]:hover,
div[data-baseweb="menu"] li:hover{
  background: rgba(255,255,255,0.08) !important;
  color: #E6EDF7 !important;
}
div[data-baseweb="menu"] [role="menuitem"][aria-selected="true"],
div[data-baseweb="menu"] li[aria-selected="true"]{
  background: rgba(255,255,255,0.10) !important;
  color: #E6EDF7 !important;
}

/* Some Streamlit/BaseWeb builds wrap options in <li>. Others use nested <div role="option">. */
div[data-baseweb="popover"] li[role="option"],
div[data-baseweb="popover"] div[role="option"] {
    background: transparent !important;
    color: #E6EDF7 !important;
}
div[data-baseweb="popover"] li[role="option"] * ,
div[data-baseweb="popover"] div[role="option"] * {
    color: inherit !important;
    background: transparent !important;
}

div[data-baseweb="popover"] li[role="option"][aria-selected="true"],
div[data-baseweb="popover"] div[role="option"][aria-selected="true"] {
    background: rgba(255,255,255,0.14) !important;
    color: #E6EDF7 !important;
}
div[data-baseweb="popover"] li[role="option"]:hover,
div[data-baseweb="popover"] div[role="option"]:hover {
    background: rgba(255,255,255,0.18) !important;
    color: #E6EDF7 !important;
}

/* Popovers + dropdown menus (force dark everywhere) */
div[data-baseweb="popover"] { background: transparent !important; }

div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div,
div[data-baseweb="popover"] > div > div > div{
    background: transparent !important;   /* prevent tooltip double-boxes */
    border: none !important;
    box-shadow: none !important;
}

div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] div[role="listbox"]{
    background: rgba(16, 16, 18, 0.98) !important;
}

ul[role="listbox"],
div[role="listbox"]{
    background: rgba(16, 16, 18, 0.98) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
}

[role="listbox"] [role="option"]{
    color: #E6EDF7 !important;
    background: transparent !important;
}

[role="listbox"] [role="option"]:hover{
    background: rgba(255,255,255,0.08) !important;
}

[role="listbox"] [role="option"][aria-selected="true"]{
    background: rgba(255,255,255,0.12) !important;
}

[role="listbox"] *{ opacity: 1 !important; }

/* Some Streamlit/BaseWeb versions render the select dropdown as a "menu" or "dialog" portal */
div[data-baseweb="menu"],
div[data-baseweb="menu"] > div,
div[role="dialog"]{
    background: rgba(16, 16, 18, 0.98) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
}
div[data-baseweb="menu"] *{ color: #E6EDF7 !important; }

/* Keep scrollbars subtle but visible */
div[data-baseweb="popover"] * {
    scrollbar-color: rgba(255,255,255,0.25) transparent !important;
}

    
    /* --- EXPANDERS (Sprint 2: cleaner + consistent) --- */
    /* Default expander (main area) stays minimal */
    div[data-testid="stExpander"] details summary{
        background-color: transparent !important;
        color: rgba(241,241,243,0.94) !important;
        border: none !important;
        padding-left: 0 !important;
    }
    div[data-testid="stExpanderDetails"]{
        background-color: transparent !important;
        border: none !important;
    }

    /* Sidebar expanders get a subtle "settings console" card feel */
    section[data-testid="stSidebar"] div[data-testid="stExpander"]{
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 14px !important;
        background: rgba(255,255,255,0.02) !important;
        /* Tooltips are absolutely-positioned; overflow:hidden clips them inside the sidebar. */
        overflow: visible !important;
        margin: 10px 0 12px 0 !important;
        box-shadow: 0 10px 26px -22px rgba(0,0,0,0.85) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary{
        padding: 10px 12px !important;
        margin: 0 !important;
        border: none !important;
        background: rgba(255,255,255,0.015) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary:hover{
        background: rgba(255,255,255,0.03) !important;
        color: rgba(250,250,252,0.98) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"]{
        padding: 2px 12px 12px 12px !important;
    }

    /* Nested "advanced" expander inside sidebar: intentionally secondary */
    section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpander"]{
        border-color: rgba(255,255,255,0.06) !important;
        background: rgba(0,0,0,0.10) !important;
        margin-top: 10px !important;
        overflow: visible !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpander"] details summary{
        font-weight: 650 !important;
        font-size: 0.90rem !important;
        background: rgba(255,255,255,0.01) !important;
        opacity: 0.90 !important;
    }

    /* Sidebar hint text (replaces noisy captions) */
    .rbv-hint{
        color: rgba(148,163,184,0.78);
        font-size: 0.86rem;
        line-height: 1.35;
        margin: 6px 0 2px 0;
    }
    .rbv-pill-row{
        display:flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 8px 0 2px 0;
    }
    .rbv-pill{
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.04);
        color: rgba(241,241,243,0.90);
        font-size: 0.86rem;
        font-weight: 650;
        letter-spacing: 0.01em;
        white-space: nowrap;
    }
/* --- EXPORT (FINTECH PILL BUTTON) --- */
div[data-testid="stDownloadButton"] { width: 100% !important; }
div[data-testid="stDownloadButton"] button {
    width: 100% !important;
    background: rgba(255,255,255,0.06) !important;
    color: rgba(241,241,243,0.92) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 999px !important;
    font-weight: 700 !important;
    font-family: inherit !important;
    padding: 10px 16px !important;
    text-align: center !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transition: background 0.15s ease, transform 0.15s ease;
}
div[data-testid="stDownloadButton"] button:hover {
    background: rgba(255,255,255,0.08) !important;
    transform: translateY(-1px);
}
div[data-testid="stDownloadButton"] button:active {
    transform: translateY(0px);
}
/* --- SLIDER STYLING (MATCH CYAN FOR BUYING) --- */
    div[data-baseweb="slider"] > div > div > div > div {
        background-color: rgba(255,255,255,0.18) !important;
    }
    div[role="slider"] {
        background-color: #9CA3AF !important;
        border: 2px solid rgba(255,255,255,0.22) !important;
        box-shadow: none !important;
        opacity: 1 !important;
    }
    div[data-testid="stSliderTickBar"] { background-color: transparent !important; }
    div[data-testid="stSlider"] p { color: #FFFFFF !important; }

    /* METRIC CARDS */
    div[data-testid="stMetric"] {
        background-color: var(--rbv-card);
        border: 1px solid rgba(255,255,255,0.10);
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.38);
    }
    div[data-testid="stMetricLabel"] { color: rgba(241,241,243,0.70) !important; font-size: 0.85rem !important; font-weight: 500 !important; }
    div[data-testid="stMetricValue"] { color: rgba(241,241,243,0.92) !important; font-size: 1.8rem !important; font-weight: 700 !important; }

    /* RESULT BANNER */
    .result-banner {
        background: var(--rbv-card);
        padding: 30px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.10);
        margin-bottom: 30px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.42);
    }
    .result-title {
        font-size: 14px;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0.3px;
        color: rgba(241,241,243,0.70);
        margin-bottom: 10px;
    }
    .result-value {
        font-size: 48px;
        font-weight: 700;
        margin-bottom: 5px;
        line-height: 1.1;
        text-shadow: none;
    }
    .result-sub {
        font-size: 16px;
        font-weight: 500;
        color: rgba(241,241,243,0.86);
        margin-top: 15px;
        background: rgba(255,255,255,0.06);
        padding: 8px 16px;
        border-radius: 20px;
    }

    /* COLORS & HEADERS */
    .text-buy { color: var(--buy, #2F8BFF) !important; }
    .text-rent { color: var(--rent, #E6B800) !important; }
    
    .section-header {
        font-weight: 600;
        font-size: 14px;
        text-align: center;
        padding: 8px;
        border-radius: 6px;
        margin-bottom: 15px;
        text-transform: none;
        letter-spacing: 0.3px;
    }
    .header-buy { background: rgba(47,139,255, 0.14); color: var(--buy, #2F8BFF); border: 1px solid rgba(47,139,255, 0.30); }
    .header-rent { background: rgba(230,184,0, 0.14); color: var(--rent, #E6B800); border: 1px solid rgba(230,184,0, 0.30); }
    
    /* UNRECOVERABLE BOX */
    .unrec-box {
        background-color: #141417;
        padding: 25px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.14);
        margin: 20px 0;
        text-align: center;
    }

    
/* --- Premium grey note box (for assumptions / clarifications) --- */
.note-box{
  background: rgba(148,163,184,0.08);
  border: 1px solid rgba(148,163,184,0.18);
  color: #CBD5E1;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.35;
  box-shadow: 0 10px 25px rgba(0,0,0,0.35);
  margin: 14px 0 14px 0;
}

.note-box b{ color: #F1F5F9 !important; }
.note-box .accent-buy{ color: var(--buy, #2F8BFF) !important; font-weight:600; }
.note-box .accent-rent{ color: var(--rent, #E6B800) !important; font-weight:600; }
/* Softer accents for dark neutral theme */
.note-box .accent-buy{ color: var(--buy, #2F8BFF) !important; font-weight:600; }
.note-box .accent-rent{ color: var(--rent, #E6B800) !important; font-weight:600; }

/* Extra breathing room before tabs (prevents any overlap with KPI cards) */
div[data-testid="stTabs"]{
  margin-top: 34px !important;
}

    /* TAB STYLING */
    button[data-baseweb="tab"] { 
        color: #9A9A9A !important; 
        font-weight: 600; 
        font-size: 16px !important; 
        padding: 12px 24px !important; 
        border-radius: 8px !important; 
        margin: 0 5px !important;
        border: 1px solid transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] { 
        color: #FFFFFF !important; 
        background-color: var(--rbv-input) !important; 
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-top: 3px solid rgba(255,255,255,0.35) !important; 
    }
    /* Remove the default underline/highlight for tabs (keep only our top border) */
    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"]{
        background: transparent !important;
        height: 0px !important;
    }
    div[data-baseweb="tab-list"]{
        border-bottom: none !important;
        box-shadow: none !important;
    }


    /* TABLE STYLING */

/* -------------------- DARK TABLE SYSTEM -------------------- */
/* Streamlit renders styled dataframes either as HTML tables (Pandas Styler)
   or as a grid. We style both paths to ensure a consistent dark theme. */

/* Container */
[data-testid="stDataFrame"]{
    background-color: var(--rbv-input) !important;
    border: 1px solid #1F2937 !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    font-family: var(--rbv-font) !important;
}

/* HTML-table path (Pandas Styler) */
[data-testid="stDataFrame"] table{
    background-color: var(--rbv-input) !important;
    color: #F1F5F9 !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    width: 100% !important;
    font-family: var(--rbv-font) !important;
}
[data-testid="stDataFrame"] thead th{
    background-color: var(--rbv-input) !important;
    color: #E2E8F0 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.3px !important;
    border-bottom: 1px solid #1F2937 !important;
    border-right: 1px solid #1F2937 !important;
    padding: 10px 12px !important;
    text-align: right !important;
    white-space: nowrap !important;
}
[data-testid="stDataFrame"] thead th:first-child{
    text-align: left !important;
}
[data-testid="stDataFrame"] tbody td{
    background-color: var(--rbv-input) !important;
    color: #F1F5F9 !important;
    font-size: 13px !important;
    border-bottom: 1px solid #1F2937 !important;
    border-right: 1px solid #1F2937 !important;
    padding: 8px 12px !important;
    text-align: right !important;
    white-space: nowrap !important;
}
[data-testid="stDataFrame"] tbody td:first-child{
    text-align: left !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td{
    background-color: rgba(148,163,184,0.04) !important;
}
[data-testid="stDataFrame"] tbody tr:hover td{
    background-color: rgba(255,255,255,0.08) !important;
    transition: background-color 0.15s ease !important;
}

/* Grid path (non-Styler dataframe) - neutralize light background */
[data-testid="stDataFrame"] div[role="grid"],
[data-testid="stDataFrame"] div[role="row"],
[data-testid="stDataFrame"] div[role="columnheader"],
[data-testid="stDataFrame"] div[role="gridcell"]{
    background-color: transparent !important;
    color: #F1F5F9 !important;
    font-family: var(--rbv-font) !important;
}

/* Remove white “paper” layers inside the dataframe */
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] div{
    background-color: transparent !important;
}

/* Mobile optimization */
@media (max-width: 768px){
    [data-testid="stDataFrame"] thead th,
    [data-testid="stDataFrame"] tbody td{
        font-size: 12px !important;
        padding: 14px 18px !important;
    }
}

    /* Model Assumptions text sizing */
    .assumptions-wrap, .assumptions-wrap *{
        font-size: 0.92rem !important;
        line-height: 1.45 !important;
    }
    @media (max-width: 768px){
        .block-container{
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        button[data-baseweb="tab"]{
            font-size: 14px !important;
            padding: 10px 14px !important;
        }
    }


    /* --- Random Seed input styling (match sidebar controls) --- */
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input{
        background-color: var(--rbv-input) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 10px !important;
        text-align: center !important;
        padding: 10px 12px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder{
        color: #9A9A9A !important;
    }



    /* --- Sidebar Text Inputs (e.g., Random Seed) --- */
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input{
        background-color: var(--rbv-input) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
        text-align: center !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus{
        box-shadow: 0 0 0 2px rgba(255,255,255,0.20) !important;
        outline: none !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stTextInput"] label{
        color: #F8FAFC !important;
    }


    /* ---------------- FINTECH HTML TABLES ---------------- */
    .fin-table-wrap{
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        border: 1px solid #1F2937;
        border-radius: 14px;
        background: #141417;
        box-shadow: 0 10px 25px -20px rgba(0,0,0,0.8);
        overflow: hidden; /* clip to rounded corners */
    }
    .fin-table-scroll{
        overflow-x: auto;
        overflow-y: auto;
        max-height: 520px;
    }
    .fin-table{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-family: var(--rbv-font-sans);
        font-size: 13px;
    }
    .fin-table thead th{
        position: sticky;
        top: 0;
        z-index: 2;
        background: #141417;
        color: rgba(241,241,243,0.86);
        font-weight: 600;
        letter-spacing: 0.02em;
        text-align: left;
        padding: 11px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.10);
        border-top: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 6px 14px -14px rgba(0,0,0,0.9);
        white-space: nowrap;
    }
    .fin-table thead th.num{
        text-align: right;
    }

    .fin-table thead th:first-child{ border-top-left-radius: 14px; }
    .fin-table thead th:last-child{ border-top-right-radius: 14px; }
    .fin-table tbody tr:last-child td:first-child{ border-bottom-left-radius: 14px; }
    .fin-table tbody tr:last-child td:last-child{ border-bottom-right-radius: 14px; }

    .fin-table tbody td{
        text-align: left;
        padding: 9px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        color: rgba(241,241,243,0.88);
        background: #141417;
        white-space: nowrap;
    }
    .fin-table tbody tr:nth-child(even) td{
        background: rgba(255,255,255,0.03);
    }
    .fin-table tbody tr:hover td{
        background: rgba(255,255,255,0.06);
        transition: background-color 0.12s ease;
    }
    .fin-table td.num{
        text-align: right;
        font-variant-numeric: tabular-nums;
    }
    .fin-table td.pos{ color: var(--buy); font-weight: 650; }
    .fin-table td.neg{ color: var(--rent); font-weight: 650; }
    .fin-table td.zero{ color: #CBD5E1; }

    .fin-table td.pill{
        font-weight: 750;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.02);
    }
    .fin-table td.pill.pos{
        color: var(--buy) !important;
        background: var(--buy-bg) !important;
        border-color: var(--buy-border) !important;
    }
    .fin-table td.pill.neg{
        color: var(--rent) !important;
        background: var(--rent-bg) !important;
        border-color: var(--rent-border) !important;
    }


    .fin-table-empty{
        color: #9A9A9A;
        padding: 10px 12px;
        border: 1px dashed rgba(255,255,255,0.14);
        border-radius: 10px;
        background: rgba(255,255,255,0.03);
    }

    @media (max-width: 768px){
        .fin-table-scroll{ max-height: 420px; }
        .fin-table{ font-size: 12px; }
        .fin-table thead th, .fin-table tbody td{
        text-align: left; padding: 8px 10px; }
    }

    /* Prevent tiny columns from wrapping labels into vertical letters */
div[data-testid="stButton"] > button, div[data-testid="stButton"] button, .stButton > button {
        white-space: nowrap !important;
        background: rgba(255,255,255,0.06) !important;
        color: rgba(241,241,243,0.92) !important;
        border: 1px solid rgba(255,255,255,0.16) !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        box-shadow: none !important;
        transition: background 0.14s ease, border-color 0.14s ease, transform 0.08s ease;
    }
    div[data-testid="stButton"] > button:hover, div[data-testid="stButton"] button:hover, .stButton > button:hover {
        background: rgba(255,255,255,0.12) !important;
        border-color: rgba(255,255,255,0.38) !important;
        color: #E6EDF7 !important;
    }
    div[data-testid="stButton"] > button:focus, div[data-testid="stButton"] button:focus, .stButton > button:focus,
    div[data-testid="stButton"] > button:focus-visible, div[data-testid="stButton"] button:focus-visible, .stButton > button:focus-visible {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.25) !important;
    }
    
    /* Harden button theming across Streamlit versions (prevents white/blank buttons) */
    button[kind], button[kind="primary"], button[kind="secondary"], button[kind="tertiary"]{
        background: rgba(255,255,255,0.06) !important;
        color: rgba(241,241,243,0.92) !important;
        border: 1px solid rgba(255,255,255,0.16) !important;
    }
    button[kind]:hover, button[kind="primary"]:hover, button[kind="secondary"]:hover, button[kind="tertiary"]:hover{
        background: rgba(255,255,255,0.12) !important;
        border-color: rgba(255,255,255,0.38) !important;
        color: #E6EDF7 !important;
    }
    button[kind]:focus, button[kind]:focus-visible{
        background: rgba(255,255,255,0.06) !important;
        color: rgba(241,241,243,0.92) !important;
    }
div[data-testid="stButton"] > button:active, div[data-testid="stButton"] button:active, .stButton > button:active {
        transform: translateY(1px);
    }
    div[data-testid="stButton"] > button:disabled, div[data-testid="stButton"] button:disabled, .stButton > button:disabled {
        opacity: 0.55 !important;
        cursor: not-allowed !important;
    }
    /* If the sidebar is narrow, truncate instead of wrapping one character per line */
    section[data-testid="stSidebar"] .stButton,
    section[data-testid="stSidebar"] .stDownloadButton {
        width: 100% !important;
    }
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stDownloadButton > button {
        width: 100% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        min-width: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.5rem !important;
    }
    section[data-testid="stSidebar"] .stButton > button * ,
    section[data-testid="stSidebar"] .stDownloadButton > button * {
        white-space: nowrap !important;
    }


    /* Make the sidebar toggle always visible (so users can re-open the sidebar) */
    button[data-testid="stSidebarCollapseButton"]{
        opacity: 1 !important;
        visibility: visible !important;
        color: #E2E8F0 !important;
        background: rgba(255,255,255,0.10) !important;
        border: 1px solid rgba(148,163,184,0.25) !important;
        border-radius: 10px !important;
    }
    button[data-testid="stSidebarCollapseButton"]:hover{
        border-color: rgba(255,255,255,0.45) !important;
    }
        

/* Fintech download button styling */
[data-testid="stDownloadButton"] button {
  width: 100% !important;
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  color: rgba(241,241,243,0.92) !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
  padding: 0.55rem 0.9rem !important;
  letter-spacing: 0.2px !important;
}
[data-testid="stDownloadButton"] button:hover {
  border-color: rgba(255,255,255,0.22) !important;
  filter: brightness(1.04);
}
[data-testid="stDownloadButton"] button:active {
  transform: translateY(1px);
}


    /* --- FIX: prevent vertical/wrapped button labels (sidebar + main) --- */
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button,
    .stButton > button,
    div[data-testid="stDownloadButton"] button {
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

/* --- Number input instruction overlap fix --- */
div[data-testid="stNumberInput"] [data-testid="InputInstructions"],
div[data-testid="stNumberInput"] [data-testid="stInputInstructions"],
div[data-testid="stNumberInput"] div[aria-live="polite"],
div[data-testid="stNumberInput"] .stNumberInput-instructions{
  display: none !important;
}
div[data-testid="stNumberInput"] input{
  padding-top: 0.55rem !important;
  padding-bottom: 0.55rem !important;
  line-height: 1.2 !important;
}

/* --- Premium KPI cards (Buying vs Renting) --- */
.kpi-card{
  background: rgba(255,255,255,0.045);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 14px;
  padding: 12px 14px;
  position: relative;
  /* Tooltips must be able to escape the card bounds */
  overflow: visible;
  min-height: 78px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}
.kpi-card:before{
  content:"";
  position:absolute;
  left:0; top:0;
  height:4px; width:100%;
  background: var(--accent, rgba(255,255,255,0.25));
}
.kpi-card.kpi-neutral:before{
  display:none;
}
.kpi-title{
  color: rgba(255,255,255,0.78);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.2px;
  display:flex;
  align-items:center;
  gap:8px;
}
.kpi-value{
  color: #ffffff;
  font-size: 1.75rem;
  font-weight: 700;
  margin-top: 8px;
  letter-spacing: 0.2px;
}
@media (max-width: 768px){
  .kpi-card{ padding: 14px 14px; min-height: 86px; border-radius: 14px; }
  .kpi-value{ font-size: 1.75rem; }
}


/* --- Prevent sidebar button text from wrapping vertically --- */
.stButton > button, .stDownloadButton > button {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.stButton > button div, .stDownloadButton > button div {
  white-space: nowrap !important;
}
/* Keep help icons aligned with labels */
.stTooltipIcon {
  flex: 0 0 auto !important;
}


/* --- FINAL FIX: prevent any sidebar button text from wrapping into vertical letters --- */
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button{
  min-width: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
section[data-testid="stSidebar"] .stButton > button span,
section[data-testid="stSidebar"] .stButton > button div,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button span,
section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button div{
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}



/* KPI section badges + KPI help tooltip icon */
.kpi-section-title{
  display:block;
  width:100%;
  text-align:center;
  font-weight:700;
  letter-spacing:0.04em;
  padding:10px 12px;
  border-radius:14px;
  margin:10px 0 14px 0;
  text-transform:none;
  border:1px solid rgba(255,255,255,0.12);
  background:rgba(255,255,255,0.04);
}
.kpi-section-title.buy-title{
  color: var(--buy, #2F8BFF);
  border-color: var(--buy-border, rgba(47,139,255,0.42));
  background: rgba(47,139,255,0.10);
  box-shadow:none;
}
.kpi-section-title.rent-title{
  color: var(--rent, #E6B800);
  border-color: var(--rent-border, rgba(230,184,0,0.42));
  background: rgba(230,184,0,0.10);
  box-shadow:none;
}
.kpi-title{display:flex; align-items:center; gap:8px;}

.kpi-help{
  width:18px; height:18px;
  display:inline-flex; align-items:center; justify-content:center;
  border-radius:999px;
  border:1px solid rgba(255,255,255,0.25);
  color:rgba(255,255,255,0.85);
  font-size:12px; font-weight:800;
  background:rgba(255,255,255,0.06);
  cursor:help;
  position:relative;
  margin-left:8px;
  transform:translateY(-1px);
}
.kpi-help:hover{ border-color: rgba(255,255,255,0.26); color: rgba(241,241,243,0.92); background:rgba(255,255,255,0.08); }
.kpi-help[data-tip]:hover::after{
  content: attr(data-tip);
  position:absolute;
  left:50%;
  top:-10px;
  transform:translate(-50%,-100%);
  background:rgba(16,19,24,0.96);
  border:1px solid rgba(255,255,255,0.18);
  color:#F3F6FB;
  padding:8px 10px;
  border-radius:9px;
  white-space:pre-wrap;
  width:max-content;
  max-width:240px;
  font-size:11px;
  line-height:1.25;
  box-shadow:0 12px 28px rgba(0,0,0,0.55);
  z-index:999999;
  pointer-events:none;
}
.kpi-help[data-tip]:hover::before{
  content:"";
  position:absolute;
  left:50%;
  top:-10px;
  transform:translate(-50%,-2px);
  border:7px solid transparent;
  border-top-color: rgba(16,19,24,0.96);
  filter: drop-shadow(0 -1px 0 rgba(255,255,255,0.18));
  z-index:999998;
  pointer-events:none;
}
/* === Tooltips (single bubble, no double boxes) === */
/* Keep Streamlit's tooltip wrapper layers transparent; style the BaseWeb bubble elsewhere. */
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
/* Ensure tooltip text is readable inside the BaseWeb bubble */
div[data-baseweb="tooltip"] > div[role="tooltip"] *,
div[data-baseweb="tooltip"] > div[role="tooltip"] *{
  color: #F8FAFC !important;
}
div[data-baseweb="tooltip"] > div[role="tooltip"] a{
  color: #22D3EE !important;
}

/* Sidebar: force checkbox/toggle labels to be full-width so the ? can align right */
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label{
  width: 100% !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label > div{
  display: flex !important;
  align-items: center !important;
  width: 100% !important;
}
/* Sidebar: align Streamlit help icons to the right edge consistently */
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"]{
  display:flex !important;
  align-items:center !important;
  width:100% !important;
  gap: 8px !important;
}
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] > label{
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] [data-testid="stTooltipIcon"]{
  margin-left:auto !important;
  flex: 0 0 auto !important;
}

/* Checkbox / Toggle: keep checkbox left, push help icon to the far right when present */
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label{
  width: 100% !important;
}
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div:last-child,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label > div:last-child{
  flex: 1 1 auto !important;
  display:flex !important;
  align-items:center !important;
  gap: 8px !important;
  min-width: 0 !important;
}
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div:last-child > div:first-child,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label > div:last-child > div:first-child{
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div:last-child [data-testid="stTooltipIcon"],
div[data-testid="stSidebar"] div[data-testid="stToggle"] label > div:last-child [data-testid="stTooltipIcon"]{
  margin-left:auto !important;
}


/* Fallback selectors for older/newer Streamlit builds */
div[data-testid="stSidebar"] .stTooltipIcon{ margin-left:auto !important; }
div[data-testid="stSidebar"] .stWidgetLabel{ display:flex !important; align-items:center !important; width:100% !important; }
div[data-testid="stSidebar"] .stWidgetLabel label{ flex:1 1 auto !important; }



/* ===============================
   Sidebar: align ? icons + keep controls dark
   =============================== */

/* Make the sidebar widget label row a flex container so the help icon can align right */
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"]{
  display:flex !important;
  align-items:center !important;
  gap: 8px !important;
}
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] > label{
  flex: 1 1 auto !important;
  margin: 0 !important;
  padding-right: 6px !important;
}

/* Force the Streamlit help icon to the far-right edge of the label row */
div[data-testid="stSidebar"] div[data-testid="stTooltipIcon"]{
  margin-left: auto !important;
}

/* Fix "white" BaseWeb inputs/selects in sidebar by explicitly theming them */
div[data-testid="stSidebar"] div[data-baseweb="select"] > div,
div[data-testid="stSidebar"] div[data-baseweb="select"] > div > div,
div[data-testid="stSidebar"] div[data-baseweb="input"] > div,
div[data-testid="stSidebar"] div[data-baseweb="input"] > div > div,
div[data-testid="stSidebar"] div[data-baseweb="textarea"] > div{
  background: #141417 !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  color: #E6EDF7 !important;
  box-shadow: none !important;
}
div[data-testid="stSidebar"] div[data-baseweb="select"] span,
div[data-testid="stSidebar"] div[data-baseweb="select"] input,
div[data-testid="stSidebar"] div[data-baseweb="input"] input,
div[data-testid="stSidebar"] div[data-baseweb="textarea"] textarea{
  color: #E6EDF7 !important;
  background: transparent !important;
}
div[data-testid="stSidebar"] div[data-baseweb="select"] svg{
  fill: rgba(230,237,247,0.85) !important;
}

/* ===============================
   Sidebar tooltip: remove "double bubble" (do NOT affect widget styling)
   =============================== */
/* Some Streamlit builds render an extra stTooltipContent wrapper with its own background/border.
   Make that wrapper transparent in the sidebar only. */
div[data-testid="stSidebar"] div[data-testid="stTooltipContent"],
div[data-testid="stSidebar"] div[data-testid="stTooltipContent"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Keep the actual BaseWeb tooltip bubble styled, but make sidebar tooltips a bit more compact */
div[data-testid="stSidebar"] div[data-baseweb="tooltip"] > div[role="tooltip"]{
  overflow: visible !important;
}
div[data-testid="stSidebar"] div[data-baseweb="tooltip"] > div[role="tooltip"] > div{
  padding: 7px 10px !important;
  font-size: 11px !important;
  max-width: 280px !important;
  box-sizing: border-box !important;
}
/* Hide arrow layers that can look like a second box */
div[data-testid="stSidebar"] div[data-baseweb="tooltip"] [data-baseweb="arrow"]{
  display: none !important;
}

/* ============================================================ */
       FINAL OVERRIDES — keep ALL widgets dark + readable
       (Select menus, inputs, number inputs, tooltips, checkbox help icon alignment)
       ============================================================ */

    /* BaseWeb input/select shells (applies app-wide) */
    .stApp [data-baseweb="select"] > div,
    .stApp [data-baseweb="input"] > div,
    .stApp [data-baseweb="textarea"] > div{
        background: #141417 !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 10px !important;
        color: rgba(241,241,243,0.92) !important;
    }
    .stApp [data-baseweb="select"] input,
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea{
        background: transparent !important;
        color: rgba(241,241,243,0.92) !important;
    }

    /* Hide the blinking caret inside selectboxes (they're not true text inputs) */
    .stApp [data-baseweb="select"] input{ caret-color: transparent !important; }

    /* Keep caret visible for real text inputs */
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea{ caret-color: rgba(241,241,243,0.92) !important; }
    .stApp [data-baseweb="select"] svg,
    .stApp [data-baseweb="input"] svg{
        fill: rgba(241,241,243,0.86) !important;
    }
    .stApp [data-baseweb="select"] > div:focus-within,
    .stApp [data-baseweb="input"] > div:focus-within,
    .stApp [data-baseweb="textarea"] > div:focus-within{
        border-color: rgba(255,255,255,0.30) !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.12) !important;
    }

    /* +/- buttons in number inputs */
    .stApp [data-baseweb="input"] button{
        background: transparent !important;
        color: rgba(241,241,243,0.92) !important;
    }
    .stApp [data-baseweb="input"] button:hover{
        background: rgba(255,255,255,0.06) !important;
    }

    /* Select dropdown menu (BaseWeb menu rendered in a popover portal) */
    div[data-baseweb="menu"]{
        background: #1A1A1A !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 12px !important;
        box-shadow: 0 14px 40px rgba(0,0,0,0.55) !important;
        overflow: hidden !important;
    }
    div[data-baseweb="menu"] [role="option"]{
        color: #E6EDF7 !important;
        background: transparent !important;
        font-size: 13px !important;
        line-height: 1.25 !important;
    }
    div[data-baseweb="menu"] [role="option"]:hover{
        background: rgba(255,255,255,0.06) !important;
    }
    div[data-baseweb="menu"] [role="option"][aria-selected="true"]{
        background: rgba(255,255,255,0.14) !important;
    }

    /* Streamlit tooltip content — single dark bubble, smaller text */
    div[data-testid="stTooltipContent"]{
        background: #141417 !important;
        color: #E6EDF7 !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        box-shadow: 0 14px 40px rgba(0,0,0,0.55) !important;
        border-radius: 12px !important;
        padding: 10px 12px !important;
        font-size: 12px !important;
        line-height: 1.25 !important;
        max-width: 340px !important;
    }
    div[data-testid="stTooltipContent"] *{
        color: #E6EDF7 !important;
        font-size: 12px !important;
        line-height: 1.25 !important;
    }

    /* Sidebar help icon alignment: push help icon to the right for standard widget labels */
    div[data-testid="stSidebar"] label[data-testid="stWidgetLabel"]{
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    div[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] > div:first-child{
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }
    div[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] [data-testid="stTooltipIcon"]{
        margin-left: auto !important;
    }

    /* Sidebar checkbox help icon alignment (checkbox label isn't a WidgetLabel) */
    div[data-testid="stSidebar"] .stCheckbox{
        position: relative !important;
    }
    div[data-testid="stSidebar"] .stCheckbox [data-testid="stTooltipIcon"]{
        position: absolute !important;
        right: 6px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
    }
    div[data-testid="stSidebar"] .stCheckbox label{
        padding-right: 28px !important;
    }



/* ===== Dropdown menu (opened selectbox) — force dark background + readable text ===== */
div[data-baseweb="popover"] div[data-baseweb="menu"],
div[data-baseweb="popover"] div[data-baseweb="menu"] > div,
div[data-baseweb="popover"] div[data-baseweb="menu"] > div > div,
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul[role="listbox"],
div[data-baseweb="popover"] div[role="listbox"]{
  background: rgba(10, 14, 22, 0.98) !important;
  color: #E6EDF7 !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
}

div[data-baseweb="popover"] div[data-baseweb="menu"] [role="option"],
div[data-baseweb="popover"] ul[role="listbox"] > li,
div[data-baseweb="popover"] div[role="listbox"] > div{
  color: #E6EDF7 !important;
  background: transparent !important;
}

div[data-baseweb="popover"] div[data-baseweb="menu"] [role="option"]:hover,
div[data-baseweb="popover"] div[data-baseweb="menu"] [role="option"][aria-selected="true"],
div[data-baseweb="popover"] ul[role="listbox"] > li:hover,
div[data-baseweb="popover"] ul[role="listbox"] > li[aria-selected="true"]{
  background: rgba(255,255,255,0.12) !important;
}

div[data-baseweb="popover"] div[data-baseweb="menu"] *{
  color: inherit !important;
}

/* ===== Tooltip icons ("?") — make them visible on dark background ===== */
button[data-testid="stTooltipIcon"]{
  border: 1px solid rgba(255,255,255,0.22) !important;
  background: #141417 !important;
  border-radius: 999px !important;
  width: 22px !important;
  height: 22px !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

button[data-testid="stTooltipIcon"] svg{
  width: 15px !important;
  height: 15px !important;
  color: #AAB7C8 !important;
  fill: #AAB7C8 !important;
}

button[data-testid="stTooltipIcon"]:hover{
  background: rgba(255,255,255,0.08) !important;
  border-color: rgba(255,255,255,0.26) !important;
}

button[data-testid="stTooltipIcon"]:hover svg{
  color: rgba(241,241,243,0.92) !important;
  fill: rgba(241,241,243,0.92) !important;
}



/* ===== Global dropdown menu (portal) dark theme fix ===== */
/* BaseWeb select menu is rendered in a portal outside the sidebar, so we must style it globally. */
*[role="listbox"] {
  background: var(--rbv-panel, #1A1A1A) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  box-shadow: 0 18px 60px rgba(0,0,0,0.55) !important;
}
*[role="option"] {
  background: transparent !important;
  color: rgba(235,242,255,0.92) !important;
  font-size: 13px !important;
}
*[role="option"]:hover {
  background: rgba(255,255,255,0.12) !important;
}
*[role="option"][aria-selected="true"],
*[role="option"][aria-selected="true"]:hover {
  background: rgba(255,255,255,0.18) !important;
}

/* Some Streamlit/BaseWeb versions wrap the listbox in a popover with a default white surface */
div[data-baseweb="popover"] > div {
  background: transparent !important;
}

/* ===== Tooltip icon visibility (sidebar + main) ===== */
/* Make the "?" icon more visible against the dark sidebar */
div[data-testid="stTooltipIcon"],
span[data-testid="stTooltipIcon"] {
  color: rgba(235,242,255,0.85) !important;
}
div[data-testid="stTooltipIcon"] svg,
span[data-testid="stTooltipIcon"] svg {
  fill: rgba(235,242,255,0.85) !important;
}

div[data-testid="stTooltipIcon"] {
  border: 1px solid rgba(255,255,255,0.35) !important;
  background: rgba(255,255,255,0.06) !important;
  border-radius: 999px !important;
  width: 18px !important;
  height: 18px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* ===== Tooltip bubble sizing & theme (avoid oversized white tooltips) ===== */
/* === FINAL TOOLTIP OVERRIDE (single bubble everywhere) === */
/* Streamlit/BaseWeb sometimes renders nested tooltip wrappers. We force outer layers transparent and style only the inner bubble. */
div[data-testid="stTooltipContent"], div[data-testid="stTooltipContent"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* Make all tooltip/popover outer layers transparent */
div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
div[data-baseweb="popover"] div[role="tooltip"],
div[data-baseweb="popover"] div[role="tooltip"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Style only the inner bubble container */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div{
  background: #141417 !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  color: #E6EDF7 !important;
  padding: 16px 20px !important;
  border-radius: 12px !important;
  box-shadow: 0 16px 40px rgba(0,0,0,0.65) !important;
  font-size: 12px !important;
  line-height: 1.40 !important;
  max-width: 420px !important;
  backdrop-filter: none !important;
  word-wrap: break-word !important;
  overflow-wrap: anywhere !important;
}

/* Hide arrows (often look like a second shape) */
div[data-baseweb="tooltip"] [data-baseweb="arrow"],
div[data-baseweb="popover"] [data-baseweb="arrow"]{
  display: none !important;
}


    
    /* FINAL: Sidebar/help tooltips — single bubble, padded, no clipping */
    /* Keep Streamlit wrapper transparent (prevents "double box") */
    div[data-testid="stTooltipContent"],
    div[data-testid="stTooltipContent"] *{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
    }

    /* Hide BaseWeb arrow (it can look like a second bubble) */
    div[data-baseweb="tooltip"] [data-baseweb="arrow"],
    div[data-baseweb="popover"] [data-baseweb="arrow"]{
      display: none !important;
    }

    /* Shell (no background) */
    div[data-baseweb="tooltip"] div[role="tooltip"],
    div[data-baseweb="popover"] div[role="tooltip"]{
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      margin: 0 !important;
    }

    /* Actual visible bubble — apply padding HERE so first letter never clips */
    div[data-baseweb="tooltip"] div[role="tooltip"] > div,
    div[data-baseweb="popover"] div[role="tooltip"] > div{
      background: rgba(13, 20, 35, 0.98) !important;
      border: 1px solid rgba(255,255,255,0.14) !important;
      color: rgba(235,242,255,0.94) !important;
      border-radius: 12px !important;
padding: 14px 18px !important;
      box-shadow: 0 12px 35px rgba(0,0,0,0.55) !important;
      font-size: 12px !important;
      line-height: 1.25 !important;
      max-width: 340px !important;
      white-space: normal !important;
      box-sizing: border-box !important;
      overflow: visible !important;
      text-align: left !important;
    }

    /* Clean inner text defaults (no margins that fight the padding) */
    div[data-baseweb="tooltip"] div[role="tooltip"] > div p,
    div[data-baseweb="popover"] div[role="tooltip"] > div p{
      margin: 0 !important;
    }


/* ===== FINAL: Tooltip bubble fix (single bubble, no clipping) ===== */
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

div[data-baseweb="tooltip"] div[role="tooltip"],
div[data-baseweb="popover"] div[role="tooltip"]{
  background: rgba(13, 20, 35, 0.98) !important;
  color: #EAF2FF !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 35px rgba(0,0,0,0.55) !important;
  padding: 14px 18px !important;
  line-height: 1.25 !important;
  font-size: 0.88rem !important;
  max-width: 340px !important;
  box-sizing: border-box !important;
}

div[data-baseweb="tooltip"] div[role="tooltip"] p,
div[data-baseweb="popover"] div[role="tooltip"] p{
  margin: 0 !important;
  padding: 0 !important;
}

/* Hide arrows to avoid "double shape" */
div[data-baseweb="tooltip"] [data-baseweb="arrow"],
div[data-baseweb="popover"] [data-baseweb="arrow"]{
  display: none !important;
}



/* === FINAL TOOLTIP OVERRIDE (single bubble, no clipping) === */
div[data-testid="stTooltipContent"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
div[data-testid="stTooltipContent"] *{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* BaseWeb tooltip shells: no bubble here (prevents double box) */
div[data-baseweb="tooltip"] div[role="tooltip"],
div[data-baseweb="popover"] div[role="tooltip"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  z-index: 99999 !important;
}

/* Actual bubble is the inner container */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div,
div[role="tooltip"] > div{
  background: rgba(13, 20, 35, 0.98) !important;
  color: rgba(235,242,255,0.96) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  padding: 14px 18px !important;
  box-shadow: 0 14px 40px rgba(0,0,0,0.55) !important;
  box-sizing: border-box !important;
  line-height: 1.35 !important;
  font-size: 0.88rem !important;
  max-width: 340px !important;
}

/* Remove default paragraph margins that can push into corners */
div[role="tooltip"] > div p{ margin: 0 !important; }


    /* --- FINAL TOOLTIP OVERRIDE (authoritative) --- */
    /* Some older blocks in this file set tooltip descendants to background: transparent.
       This re-enables a single, opaque bubble with safe padding. */
    div[data-testid="stTooltipContent"]{background: transparent !important; border:none !important; box-shadow:none !important; padding:0 !important;}

    div[data-baseweb="tooltip"] div[role="tooltip"] > div,
    div[data-baseweb="popover"] div[role="tooltip"] > div{
      background: #141417 !important;
      color: #E6EDF7 !important;
      border: 1px solid rgba(255,255,255,0.12) !important;
      border-radius: 12px !important;
      padding: 16px 20px !important;
      max-width: 460px !important;
      line-height: 1.4 !important;
      box-shadow: 0 16px 40px rgba(0,0,0,0.65) !important;
      overflow-wrap: anywhere !important;
      word-break: break-word !important;
    }
    div[data-baseweb="tooltip"] div[role="tooltip"] > div * ,
    div[data-baseweb="popover"] div[role="tooltip"] > div *{
      color: #E6EDF7 !important;
      background: transparent !important;
      margin: 0 !important;
    }
    div[data-baseweb="tooltip"] div[role="tooltip"] > div p,
    div[data-baseweb="popover"] div[role="tooltip"] > div p{ margin: 0 !important; }

/* === FINAL OVERRIDE: Help tooltips (single bubble, opaque, padded) === */
/* Make all wrapper shells transparent so we don't get double boxes */
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] * {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Force the actual BaseWeb tooltip bubble to be fully opaque and padded */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div,
div[data-testid="stSidebar"] div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-testid="stSidebar"] div[data-baseweb="popover"] div[role="tooltip"] > div {
  background: #141417 !important;      /* fully opaque */
  color: #E6EDF7 !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
  padding: 18px 22px !important;       /* more breathing room to avoid corner clipping */
  max-width: 440px !important;
  line-height: 1.45 !important;
  box-shadow: 0 18px 44px rgba(0,0,0,0.70) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  opacity: 1 !important;
  filter: none !important;
  mix-blend-mode: normal !important;
  box-sizing: border-box !important;
}

/* Ensure inner text doesn't add default margins that push into corners */
div[data-baseweb="tooltip"] div[role="tooltip"] > div p,
div[data-baseweb="popover"] div[role="tooltip"] > div p {
  margin: 0 !important;
}

/* Wrap long help text cleanly */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div {
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
}

/* ================= RBV CSS BLOCK ================= */

/* 1) Force sidebar widgets to match dark theme (some Streamlit builds revert to light inputs) */
div[data-testid="stSidebar"] input,
div[data-testid="stSidebar"] textarea{
  background-color: var(--rbv-input) !important;
  color: rgba(241,241,243,0.92) !important;
  -webkit-text-fill-color: rgba(241,241,243,0.92) !important;
  caret-color: rgba(241,241,243,0.92) !important;
}
div[data-testid="stSidebar"] div[role="combobox"],
div[data-testid="stSidebar"] div[role="button"][aria-haspopup],
div[data-testid="stSidebar"] div[data-baseweb="select"] > div,
div[data-testid="stSidebar"] div[data-baseweb="select"] div[role="button"],
div[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"]{
  background-color: var(--rbv-input) !important;
  color: rgba(241,241,243,0.92) !important;
  border-color: rgba(255,255,255,0.14) !important;
}
div[data-testid="stSidebar"] div[data-baseweb="select"] *{
  color: rgba(241,241,243,0.92) !important;
}
div[data-testid="stSidebar"] div[data-testid="stNumberInput"] button{
  background-color: var(--rbv-input) !important;
  border-color: rgba(255,255,255,0.14) !important;
}
div[data-testid="stSidebar"] div[data-testid="stNumberInput"] button:hover{
  border-color: rgba(255,255,255,0.22) !important;
}

/* 2) Align help icons consistently to the far right */
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"]{
  display:flex !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap: 8px !important;
  width:100% !important;
}
div[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] label{
  flex: 1 1 auto !important;
  min-width: 0 !important;
}
div[data-testid="stSidebar"] [data-testid="stTooltipIcon"]{
  margin-left:auto !important;
  flex: 0 0 auto !important;
}

/* Checkbox/toggle labels have different markup; force a two-column layout */
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label{
  display:flex !important;
  align-items:center !important;
  width:100% !important;
}
div[data-testid="stSidebar"] div[data-testid="stCheckbox"] label > div:last-child,
div[data-testid="stSidebar"] div[data-testid="stToggle"] label > div:last-child{
  flex:1 1 auto !important;
  display:flex !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap: 8px !important;
  min-width:0 !important;
}

/* 3) Tooltip styling: single dark box, smaller font, no double border */
div[data-testid="stTooltipContent"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
div[data-testid="stTooltipContent"] div[role="tooltip"]{
  background: #141417 !important;
  color: #e7eefc !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 12px !important;
  padding: 10px 12px !important;
  box-shadow: 0 14px 34px rgba(0,0,0,0.55) !important;
  font-size: 12px !important;
  line-height: 1.25 !important;
  max-width: 340px !important;
}

/* ================= RBV CSS BLOCK ================= */

/* v2.14: Neutral dark theme + softer buy/rent accents */
.verdict-banner{
  margin-bottom: 16px !important;
  background: var(--badge-bg) !important;
  border: 1px solid var(--badge-color) !important;
  border-radius: 16px !important;
  padding: 16px 16px !important;
  text-align: center !important;
  font-weight: 700 !important;
  font-size: 32px !important;
  letter-spacing: 0.2px !important;
  line-height: 1.10 !important;
  box-shadow: 0 12px 26px rgba(0,0,0,0.42) !important;
}
.verdict-banner, .verdict-banner *{
  color: var(--badge-color) !important;
}
.verdict-banner .verdict-pv{
  font-weight: 700 !important;
  font-size: 20px !important;
  margin-left: 10px !important;
}
.verdict-banner .verdict-tag{
  font-weight: 900 !important;
  font-size: 13px !important;
  letter-spacing: 0.08em !important;
  opacity: 0.88 !important;
  margin-bottom: 6px !important;
  text-transform: uppercase !important;
}
.verdict-banner .verdict-sub{
  font-weight: 600 !important;
  font-size: 12px !important;
  opacity: 0.82 !important;
  margin-top: 6px !important;
  line-height: 1.25 !important;
}
@media (max-width: 640px){
  .verdict-banner{ font-size: 28px !important; padding: 14px 12px !important; }
  .verdict-banner .verdict-line{ display:flex; flex-direction:column; gap:6px; }
  .verdict-banner .verdict-pv{ margin-left: 0 !important; font-size: 16px !important; }
}

/* v101: Tooltip bubble — single compact premium dark box (sidebar + main) */
:root{
  --rbv-bg: #000000;
  --rbv-panel: #1A1A1A;
  --rbv-card: #1A1A1A;
  --rbv-input: #2A2A2A;
  --rbv-border: rgba(255,255,255,0.14);
  --rbv-text: rgba(241,241,243,0.92);
  --rbv-muted: rgba(241,241,243,0.70);

  /* Accents */
  --buy: #2F8BFF;
  --buy-bg: rgba(47,139,255,0.12);
  --buy-border: rgba(47,139,255,0.42);
  --rent: #E6B800;
  --rent-bg: rgba(230,184,0,0.12);
  --rent-border: rgba(230,184,0,0.42);

  /* Tooltip */
  --tt-bg: rgba(16, 16, 18, 0.98);
  --tt-border: rgba(255,255,255,0.16);
  --tt-text: rgba(241,241,243,0.92);
  --tt-shadow: 0 12px 40px rgba(0,0,0,0.60);
}


/* Neutralize wrapper so we don't get double padding/background */
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipContent"] > div{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

/* Actual tooltip bubble */
div[data-testid="stTooltipContent"] div[role="tooltip"],
div[data-baseweb="tooltip"] > div{
  background: var(--tt-bg) !important;
  border: 1px solid var(--tt-border) !important;
  color: var(--tt-text) !important;
  border-radius: 12px !important;
  padding: 12px 14px !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  box-shadow: var(--tt-shadow) !important;
  font-size: 12px !important;
  line-height: 1.25 !important;
  width: max-content !important;
  max-width: 320px !important;
  white-space: normal !important;
}

div[data-testid="stTooltipContent"] div[role="tooltip"] *,
div[data-baseweb="tooltip"] > div *{
  color: var(--tt-text) !important;
}

div[data-testid="stTooltipContent"] a,
div[data-baseweb="tooltip"] a{
  color: rgba(241,241,243,0.92) !important;
}

/* v101: Tooltip icon — consistent circle (match sidebar + KPI) */
button[data-testid="stTooltipIcon"],
div[data-testid="stTooltipIcon"],
span[data-testid="stTooltipIcon"]{
  border: 1px solid rgba(255,255,255,0.18) !important;
  background: rgba(255,255,255,0.06) !important;
  border-radius: 999px !important;
  width: 18px !important;
  height: 18px !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: rgba(235,242,255,0.88) !important;
}
button[data-testid="stTooltipIcon"] svg,
div[data-testid="stTooltipIcon"] svg,
span[data-testid="stTooltipIcon"] svg{
  width: 14px !important;
  height: 14px !important;
  fill: rgba(235,242,255,0.88) !important;
}
button[data-testid="stTooltipIcon"]:hover,
div[data-testid="stTooltipIcon"]:hover,
span[data-testid="stTooltipIcon"]:hover{
  border-color: rgba(255,255,255,0.26) !important;
  background: rgba(255,255,255,0.08) !important;
}

/* v101: KPI tooltip + icon — match Streamlit help tooltips */
.kpi-help{
  border: 1px solid rgba(255,255,255,0.18) !important;
  background: rgba(255,255,255,0.06) !important;
  color: rgba(235,242,255,0.88) !important;
}
.kpi-help:hover{
  border-color: rgba(255,255,255,0.26) !important;
  background: rgba(255,255,255,0.08) !important;
}
.kpi-help[data-tip]:hover::after{
  background: var(--tt-bg) !important;
  border: 1px solid var(--tt-border) !important;
  color: var(--tt-text) !important;
  padding: 12px 14px !important;
  border-radius: 10px !important;
  max-width: 320px !important;
  font-size: 12px !important;
  box-shadow: var(--tt-shadow) !important;
}
.kpi-help[data-tip]:hover::before{
  border-top-color: var(--tt-bg) !important;
  filter: drop-shadow(0 -1px 0 var(--tt-border)) !important;
}

/* v101: Dropdown (selectbox) popover list — force dark menu surface + readable text */
body > div[data-baseweb="portal"] div[data-baseweb="popover"] > div,
body > div[data-baseweb="portal"] div[data-baseweb="menu"],
body > div[data-baseweb="portal"] div[data-baseweb="menu"] > div,
body > div[data-baseweb="portal"] div[role="listbox"],
body > div[data-baseweb="portal"] ul[role="listbox"]{
  background: var(--rbv-panel) !important;
  color: rgba(235,242,255,0.94) !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  border-radius: 12px !important;
  box-shadow: 0 18px 60px rgba(0,0,0,0.55) !important;
}
body > div[data-baseweb="portal"] [role="option"],
body > div[data-baseweb="portal"] ul[role="listbox"] > li{
  background: transparent !important;
  color: rgba(235,242,255,0.94) !important;
}
body > div[data-baseweb="portal"] [role="option"]:hover,
body > div[data-baseweb="portal"] ul[role="listbox"] > li:hover{
  background: rgba(255,255,255,0.08) !important;
}
body > div[data-baseweb="portal"] [role="option"][aria-selected="true"],
body > div[data-baseweb="portal"] ul[role="listbox"] > li[aria-selected="true"]{
  background: rgba(255,255,255,0.12) !important;
}

/* Global neutral surfaces (last-write-wins) */
.stApp{ background: var(--rbv-bg) !important; color: var(--rbv-text) !important; }
section[data-testid="stSidebar"]{ background: var(--rbv-panel) !important; border-right: 1px solid var(--rbv-border) !important; }

/* Softer buy/rent classes */
.text-buy{ color: var(--buy) !important; }
.text-rent{ color: var(--rent) !important; }

/* ================= RBV CSS BLOCK ================= */

/* v2_73: Input Design System (single authoritative)
   Goals:
   - Remove Streamlit-native squared focus artifacts.
   - Uniform height/radius for inputs/selects (sidebar + main).
   - Premium dark fintech feel (subtle surfaces, crisp borders).
*/
:root{
  --rbv-input-radius: 14px;
  --rbv-input-h: 40px;
  --rbv-input-bg: rgba(255,255,255,0.035);
  --rbv-input-border: rgba(255,255,255,0.14);
  --rbv-input-border-hover: rgba(255,255,255,0.20);
  --rbv-input-border-focus: rgba(61,155,255,0.55);
  --rbv-input-ring: rgba(61,155,255,0.18);
  --rbv-input-text: rgba(241,241,243,0.92);
  --rbv-input-placeholder: rgba(241,241,243,0.55);
}

/* Hard kill browser/BaseWeb focus outlines (we re-add a clean inset ring on the shell) */
body .stApp input:focus,
body .stApp input:focus-visible,
body .stApp textarea:focus,
body .stApp textarea:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* Remove BaseWeb focus paint that can be squared and spill outside rounded shells */
body .stApp div[data-baseweb="base-input"]:focus-within,
body .stApp div[data-baseweb="input"]:focus-within,
body .stApp div[data-baseweb="select"]:focus-within,
body .stApp div[data-baseweb="textarea"]:focus-within{
  outline: none !important;
  box-shadow: none !important;
  border-radius: var(--rbv-input-radius) !important;
}

/* Visible shells */
body .stApp div[data-baseweb="input"] > div,
body .stApp div[data-baseweb="select"] > div,
body .stApp div[data-baseweb="textarea"] > div,
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div{
  background: var(--rbv-input-bg) !important;
  border: 1px solid var(--rbv-input-border) !important;
  border-radius: var(--rbv-input-radius) !important;
  min-height: var(--rbv-input-h) !important;
  box-shadow: none !important;
  overflow: hidden !important;
}

/* Inner wrappers (some Streamlit builds paint these light) */
body .stApp div[data-baseweb="input"] > div > div,
body .stApp div[data-baseweb="select"] > div > div,
body .stApp div[data-baseweb="textarea"] > div > div,
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div > div{
  background: transparent !important;
  box-shadow: none !important;
  color: var(--rbv-input-text) !important;
}

/* Hover + focus (keep highlight INSIDE the shell) */
body .stApp div[data-baseweb="input"] > div:hover,
body .stApp div[data-baseweb="select"] > div:hover,
body .stApp div[data-baseweb="textarea"] > div:hover,
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div:hover{
  border-color: var(--rbv-input-border-hover) !important;
}

body .stApp div[data-baseweb="input"] > div:focus-within,
body .stApp div[data-baseweb="select"] > div:focus-within,
body .stApp div[data-baseweb="textarea"] > div:focus-within,
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div:focus-within{
  border-color: var(--rbv-input-border-focus) !important;
  box-shadow: inset 0 0 0 1px var(--rbv-input-ring) !important;
}

/* Text + placeholders */
body .stApp div[data-baseweb="input"] input,
body .stApp div[data-baseweb="select"] input{
  height: var(--rbv-input-h) !important;
  min-height: var(--rbv-input-h) !important;
  background: transparent !important;
  color: var(--rbv-input-text) !important;
  -webkit-text-fill-color: var(--rbv-input-text) !important;
  font-weight: 550 !important;
  font-size: 13px !important;
  padding: 0 12px !important;
  border-radius: var(--rbv-input-radius) !important;
}

body .stApp div[data-baseweb="input"] input::placeholder,
body .stApp div[data-baseweb="select"] input::placeholder,
body .stApp div[data-baseweb="textarea"] textarea::placeholder{
  color: var(--rbv-input-placeholder) !important;
  -webkit-text-fill-color: var(--rbv-input-placeholder) !important;
}

/* Textarea */
body .stApp div[data-baseweb="textarea"] textarea{
  background: transparent !important;
  color: var(--rbv-input-text) !important;
  -webkit-text-fill-color: var(--rbv-input-text) !important;
  font-weight: 520 !important;
  font-size: 13px !important;
  padding: 10px 12px !important;
  border-radius: var(--rbv-input-radius) !important;
}

/* Icons (caret/search) */
body .stApp div[data-baseweb="select"] svg,
body .stApp div[data-baseweb="input"] svg{
  fill: rgba(241,241,243,0.80) !important;
}

/* NumberInput +/- buttons: integrated + aligned */
body .stApp div[data-testid="stNumberInput"] button{
  background: transparent !important;
  color: rgba(241,241,243,0.88) !important;
  border: none !important;
  border-left: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 0 !important;
  width: 36px !important;
  min-width: 36px !important;
  height: var(--rbv-input-h) !important;
  margin: 0 !important;
}
body .stApp div[data-testid="stNumberInput"] button:hover{
  background: rgba(255,255,255,0.06) !important;
}

/* Ensure the shell clips any remaining focus paint (prevents the square "spill") */
body .stApp div[data-baseweb="input"],
body .stApp div[data-baseweb="select"],
body .stApp div[data-baseweb="textarea"],
body .stApp div[data-testid="stNumberInput"]{
  border-radius: var(--rbv-input-radius) !important;
}

/* End v2_73 input system */


/* Style BaseWeb tooltip bubble (single bubble, no clipping)
   Streamlit renders help tooltips with an outer wrapper + an inner content div that often fills the bubble.
   If we only pad the outer wrapper, text can still clip under the radius. So we style/pad the INNER content div. */
div[data-testid="stTooltipContent"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Make outer tooltip shells transparent (prevents "double box") */
div[data-baseweb="tooltip"],
div[data-baseweb="tooltip"] > div,
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* Outer role=tooltip is just a positioning shell */
div[data-baseweb="tooltip"] div[role="tooltip"],
div[data-baseweb="popover"] div[role="tooltip"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
}

/* The actual visible bubble: pad THIS layer so first letter never clips */
div[data-baseweb="tooltip"] div[role="tooltip"] > div,
div[data-baseweb="popover"] div[role="tooltip"] > div{
  background: rgba(16, 16, 18, 0.98) !important;
  color: rgba(241,241,243,0.92) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 12px !important;
  padding: 14px 18px !important;
  box-shadow: 0 12px 35px rgba(0,0,0,0.55) !important;
  box-sizing: border-box !important;
  line-height: 1.28 !important;
  max-width: 380px !important;
  text-align: left !important;
}

/* Remove default margins inside tooltips */
div[data-baseweb="tooltip"] div[role="tooltip"] p,
div[data-baseweb="popover"] div[role="tooltip"] p{
  margin: 0 !important;
}

/* Hide arrows (often look like an extra shape) */
div[data-baseweb="tooltip"] [data-baseweb="arrow"],
div[data-baseweb="popover"] [data-baseweb="arrow"]{
  display: none !important;
}

/* ================= RBV CSS BLOCK ================= */

        .bias-pill-row{
          display:flex; flex-wrap:wrap; gap:10px;
          margin: 4px 0 10px 0;
        }
        .bias-flip-grid{
          display:grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap:10px;
          margin: 4px 0 10px 0;
        }
        @media (max-width: 1100px){
          .bias-flip-grid{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 640px){
          .bias-flip-grid{ grid-template-columns: 1fr; }
        }
        .bias-flip-grid .bias-pill{
          min-width: 0;
        }
        .bias-pill{
          flex: 1 1 170px;
          min-width: 170px;
          border: 1px solid rgba(255,255,255,0.12);
          background: rgba(255,255,255,0.03);
          border-radius: 14px;
          padding: 10px 12px;
        }
        .bias-pill .k{
          font-size: 11px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: rgba(226,232,240,0.72);
          margin-bottom: 4px;
          white-space: nowrap;
          overflow: visible;
          text-overflow: clip;
        }
        .bias-pill .v{
          font-size: 13px;
          line-height: 1.25;
          color: rgba(241,245,249,0.96);
          font-weight: 650;
          white-space: normal;
          word-break: break-word;
        }

        /* Bias pills: current value coloring + tooltip text normalization */
        .bias-pill .rbv-help-bubble{
          text-transform: none !important;
          letter-spacing: normal !important;
          font-size: 11px !important;
          font-weight: 500 !important;
          line-height: 1.35 !important;
        }
        .bias-pill .s{
          margin-top: 3px;
          font-size: 11px;
          font-weight: 700;
          line-height: 1.1;
          opacity: 0.95;
        }
        .bias-pill.bias-current.buy{
          border-color: rgba(47,139,255,0.42);
          box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset;
        }
        .bias-pill.bias-current.rent{
          border-color: rgba(230,184,0,0.42);
          box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset;
        }
        .bias-pill.bias-current.buy .s{ color:#2F8BFF; }
        .bias-pill.bias-current.rent .s{ color:#E6B800; }

        .bias-subpill{
          margin-top: -4px;
          margin-bottom: 10px;
          color: rgba(148,163,184,0.95);
          font-size: 12px;
        }
        /* Dataframes: keep dark + readable */
        div[data-testid="stDataFrame"]{
          border: 1px solid rgba(255,255,255,0.12) !important;
          border-radius: 14px !important;
          background: rgba(255,255,255,0.03) !important;
          overflow: hidden !important;
        }
        

/* ================= RBV CSS BLOCK ================= */

        /* ==== FINAL OVERRIDE: Sidebar help tooltips must be opaque and padded (no bleed-through) ==== */
        div[data-baseweb="tooltip"], div[data-baseweb="popover"]{
          z-index: 2147483647 !important;
        }

        /* Streamlit wrapper must never draw a bubble */
        div[data-testid="stTooltipContent"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          margin: 0 !important;
        }

        /* Opaque tooltip bubble: cover both BaseWeb tooltip and BaseWeb popover tooltips */
        div[data-baseweb="tooltip"] div[role="tooltip"] > div,
        div[data-baseweb="popover"] div[role="tooltip"] > div{
          background: rgba(16, 16, 18, 0.98) !important;     /* fully opaque */
          color: rgba(241,241,243,0.92) !important;
          border: 1px solid rgba(255,255,255,0.12) !important;
          border-radius: 14px !important;
          padding: 18px 22px !important;     /* extra padding fixes corner clipping */
          max-width: 440px !important;
          line-height: 1.45 !important;
          box-shadow: 0 16px 44px rgba(0,0,0,0.72) !important;
          backdrop-filter: none !important;
          opacity: 1 !important;
          mix-blend-mode: normal !important;
        }

        /* Ensure inner text doesn't introduce its own margins */
        div[data-baseweb="tooltip"] div[role="tooltip"] p,
        div[data-baseweb="popover"] div[role="tooltip"] p{
          margin: 0 !important;
        }
        
        /* ==== RBV progress bars (blue→yellow) + spacing ==== */
        div[data-testid="stProgress"]{
          margin-top: 14px !important;
          margin-bottom: 14px !important;
        }
        div[data-testid="stProgress"] div[role="progressbar"]{
          background: rgba(255,255,255,0.14) !important;
        }
        div[data-testid="stProgress"] div[role="progressbar"] > div{
          background: linear-gradient(90deg, #2F8BFF, #E6B800) !important;
        }
        .note-box{
          margin: 14px 0 14px 0 !important;
        }
        

/* ================= RBV CSS BLOCK ================= */

        :root{
          --buy: #2F8BFF;
          --buy-bg: rgba(47,139,255,0.12);
          --buy-border: rgba(47,139,255,0.42);

          --rent: #E6B800;
          --rent-bg: rgba(230,184,0,0.12);
          --rent-border: rgba(230,184,0,0.42);

          --rbv-bg: #000000;
          --rbv-panel: #1A1A1A;
          --rbv-card: #1A1A1A;
          --rbv-input: #2A2A2A;
          --rbv-border: #333333;
          --rbv-muted: #9A9A9A;
        }

        /* App + sidebar surfaces */
        .stApp { background: var(--rbv-bg) !important; }
        header[data-testid="stHeader"]{ background: var(--rbv-bg) !important; }
        section[data-testid="stSidebar"]{
          background: var(--rbv-panel) !important;
          border-right: 1px solid var(--rbv-border) !important;
        }

        /* BaseWeb input shells (app-wide) */
        div[data-baseweb="input"],
        .stApp div[data-baseweb="input"] > div,
        .stApp div[data-baseweb="input"] > div > div{
          background-color: #2A2A2A !important;
          border-color: #333333 !important;
        }
        div[data-baseweb="input"] input,
        .stApp div[data-baseweb="input"] input{
          color: #FFFFFF !important;
          -webkit-text-fill-color: #FFFFFF !important;
        }

        /* Sliders */

        /* Rail / track background (unfilled) */
        .stSlider > div > div > div > div,
        div[data-baseweb="slider"] > div > div > div > div{
          background-color: #2A2A2A !important;
        }

        /* Thumb / handle: force solid gray fill (Streamlit/BaseWeb DOM varies) */
        .stSlider div[role="slider"],
        div[data-baseweb="slider"] div[role="slider"]{
          background-color: #555555 !important;
          border: none !important;
          border-radius: 999px !important;
          box-shadow: none !important;
          opacity: 1 !important;
        }

        /* Hide the drag-value bubble/tooltip (prevents number-in-circle on handle) */
        div[data-baseweb="slider"] div[role="tooltip"],
        div[data-baseweb="slider"] div[data-baseweb="tooltip"],
        div[data-baseweb="slider"] div[data-baseweb="popover"]{
          display: none !important;
        }

        /* Layout + title spacing */
        .stApp .block-container{ padding-top: 0.70rem !important; }

        .rbv-title-wrap{
          width: 100%;
          text-align: center;
          margin: 0.12rem 0 0.95rem 0;
          padding: 0.70rem 0.95rem;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 16px;
          box-shadow: 0 10px 24px rgba(0,0,0,0.45);
        }

        .rbv-title{
          font-size: 2.65rem !important;
          font-weight: 900 !important;
          line-height: 1.03 !important;
          letter-spacing: -0.6px !important;
          margin: 0 !important;
          color: rgba(241,241,243,0.94) !important;
          text-shadow: 0 10px 30px rgba(0,0,0,0.60);
        }

        .rbv-title-underline{
          width: 160px;
          height: 4px;
          margin: 0.58rem auto 0 auto;
          border-radius: 999px;
          background: linear-gradient(90deg, var(--buy), var(--rent));
          opacity: 0.95;
        }
/* Sidebar primary headers */
        .sidebar-header-gen,
        .sidebar-header-buy,
        .sidebar-header-rent{
          font-size: 1.55rem !important;
          font-weight: 900 !important;
          letter-spacing: 0.20px !important;
          margin-top: 0.35rem !important;
          margin-bottom: 0.10rem !important;
        }
/* Typography hierarchy */
        h1 { font-size: 1.75rem !important; }
        h2 { font-size: 1.45rem !important; }
        h3 { font-size: 1.22rem !important; }
        input, select { font-size: 0.92rem !important; }

/* Cohesive number inputs (match selectbox border + radius) */
div[data-testid="stNumberInput"] > div{
  border: 1px solid var(--rbv-border) !important;
  border-radius: 10px !important;
  background: var(--rbv-input) !important;
  overflow: hidden !important;
}
div[data-testid="stNumberInput"] div[data-baseweb="input"]{
  border: none !important;
  background: transparent !important;
}
div[data-testid="stNumberInput"] input{
  background: transparent !important;
}
div[data-testid="stNumberInput"] button{
  background: var(--rbv-input) !important;
  color: #FFFFFF !important;
  border: none !important;
  box-shadow: none !important;
}
div[data-testid="stNumberInput"] button:first-of-type{
  border-left: 1px solid var(--rbv-border) !important;
}
div[data-testid="stNumberInput"] button + button{
  border-left: 1px solid var(--rbv-border) !important;
}

/* Selectbox shell rounding for consistency */
div[data-baseweb="select"] > div{
  background-color: var(--rbv-input) !important;
  border-color: var(--rbv-border) !important;
  border-radius: 10px !important;
}

/* ================= RBV CSS BLOCK ================= */

/* Progress bar spacing + gradient */
div[data-testid="stProgress"]{
  margin-top: 22px !important;
  margin-bottom: 14px !important;
}
div[data-testid="stProgress"] div[role="progressbar"]{
  background: rgba(255,255,255,0.14) !important;
}
div[data-testid="stProgress"] div[role="progressbar"] > div{
  background: linear-gradient(90deg, var(--buy, #2F8BFF), var(--rent, #E6B800)) !important;
}
.note-box{ margin-top: 22px !important; }

/* ================= RBV CSS BLOCK ================= */


/* --- Small spacers (used to control tight adjacency in results header) --- */
.rbv-space-sm{ height: 16px; }

/* --- Input panels: make dense inputs look intentional/professional --- */
.rbv-input-panel{
  background:
    radial-gradient(70% 120% at 50% 0%, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 45%, rgba(0,0,0,0.0) 100%),
    linear-gradient(180deg, rgba(255,255,255,0.028) 0%, rgba(255,255,255,0.016) 100%);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 18px;
  padding: 10px 14px 10px 14px;
  margin: 6px 0 18px 0;
  box-shadow: 0 14px 34px rgba(0,0,0,0.38);
}

/* Tighten labels a touch + improve hierarchy inside input panels */
.rbv-input-panel div[data-testid="stWidgetLabel"] > label{
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: rgba(241,241,243,0.86) !important;
  letter-spacing: 0.15px !important;
  margin-bottom: 0.25rem !important;
}

/* Slightly reduce vertical whitespace between widgets inside panels */
.rbv-input-panel div[data-testid="stNumberInput"],
.rbv-input-panel div[data-testid="stSelectbox"],
.rbv-input-panel div[data-testid="stSlider"],
.rbv-input-panel div[data-testid="stCheckbox"],
.rbv-input-panel div[data-testid="stRadio"]{
  margin-top: 0.15rem !important;
  margin-bottom: 0.15rem !important;
}


/* --- Micro group separators inside input panels (premium density without changing inputs) --- */
.rbv-input-subhead{
  margin: 4px 2px 6px 2px;
  padding: 6px 10px;
  border-radius: 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: rgba(241,241,243,0.70);
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;
}

/* Safety: if any empty subhead placeholders are ever rendered, hide them (prevents "empty banners"). */
.rbv-input-subhead:empty{
  display:none !important;
  margin:0 !important;
  padding:0 !important;
  border:none !important;
  background:transparent !important;
}

.rbv-input-panel .rbv-input-subhead:first-child{
  margin-top: 0px !important;
}
.rbv-buy-panel .rbv-input-subhead{ border-left: 3px solid var(--buy); }
.rbv-rent-panel .rbv-input-subhead{ border-left: 3px solid #E6B800; }

.rbv-input-subsep{
  height: 12px;
  margin: 0;
  background: transparent;
}





/* v2_70: Focus ring + border-radius hardening (prevents squared focus state and stray outlines) */
.stApp div[data-baseweb="input"] input:focus,
.stApp div[data-baseweb="input"] input:focus-visible,
.stApp div[data-baseweb="textarea"] textarea:focus,
.stApp div[data-baseweb="textarea"] textarea:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

.stApp div[data-baseweb="input"] > div,
.stApp div[data-baseweb="input"] > div > div,
.stApp div[data-baseweb="select"] > div,
.stApp div[data-baseweb="select"] > div > div,
.stApp div[data-baseweb="textarea"] > div,
.stApp div[data-baseweb="textarea"] > div > div,
.stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
.stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div > div{
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* Keep focus highlight inside the shell (no square outer ring) */
.stApp div[data-baseweb="input"] > div:focus-within,
.stApp div[data-baseweb="select"] > div:focus-within,
.stApp div[data-baseweb="textarea"] > div:focus-within,
.stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div:focus-within{
  border-color: rgba(255,255,255,0.28) !important;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.16) !important;
  border-radius: 12px !important;
}

/* ================= Phase 3C: Responsive columns (4→2→1) =================
   IMPORTANT: scope to .rbv-responsive-cols wrapper to avoid breaking non-input layouts.
   Streamlit columns shrink aggressively on narrower screens and can cause
   widget overflow in dense input grids. We allow wrapping and enforce min widths.
*/
.rbv-responsive-cols div[data-testid="stHorizontalBlock"]{
  flex-wrap: wrap !important;
  gap: 0.8rem !important;
}
@media (max-width: 1200px){
  .rbv-responsive-cols div[data-testid="stHorizontalBlock"] > div{
    flex: 1 1 360px !important;
    min-width: 340px !important;
  }
}
@media (max-width: 860px){
  .rbv-responsive-cols div[data-testid="stHorizontalBlock"] > div{
    flex-basis: 100% !important;
    min-width: 0 !important;
  }
}

/* ================= v2_60 UI overrides ================= */

/* Ensure current palette variables align with Azure/Orange constants */
:root{
  --buy: #3D9BFF;
  --buy-bg: rgba(61,155,255,0.10);
  --buy-border: rgba(61,155,255,0.40);
  --rent: #E6B800;
  --rent-bg: rgba(230,184,0,0.10);
  --rent-border: rgba(230,184,0,0.40);

  /* Subtle action accent */
  --action: #34C26B;
  --action-bg: rgba(52,194,107,0.08);
  --action-border: rgba(52,194,107,0.28);
}

/* Center the tab bar visually within its container */
.st-key-rbv_tab_nav div[role="radiogroup"]{
  width: fit-content !important;
  margin: 0 auto !important;
  justify-content: center !important;
}

/* Tables: deltas are text-colored only (no highlighted cell backgrounds) */
.fin-table td.delta{
  font-weight: 700 !important;
}
.fin-table td.delta.pos{
  color: var(--buy) !important;
}
.fin-table td.delta.neg{
  color: var(--rent) !important;
}
.fin-table td.delta.zero{
  color: #CBD5E1 !important;
}

/* If any legacy "pill" class remains, keep it neutral */
.fin-table td.pill,
.fin-table td.pill.pos,
.fin-table td.pill.neg{
  background: transparent !important;
  border-color: rgba(255,255,255,0.10) !important;
}

/* Subtle green action styling for buttons (download/compute/etc.) */
div[data-testid="stDownloadButton"] button,
div[data-testid="stButton"] > button,
div[data-testid="stButton"] button,
.stButton > button{
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid var(--action-border) !important;
}

div[data-testid="stDownloadButton"] button:hover,
div[data-testid="stButton"] > button:hover,
div[data-testid="stButton"] button:hover,
.stButton > button:hover{
  background: var(--action-bg) !important;
  border-color: rgba(52,194,107,0.42) !important;
}

div[data-testid="stDownloadButton"] button:focus,
div[data-testid="stButton"] > button:focus,
div[data-testid="stButton"] button:focus,
.stButton > button:focus,
div[data-testid="stDownloadButton"] button:focus-visible,
div[data-testid="stButton"] > button:focus-visible,
div[data-testid="stButton"] button:focus-visible,
.stButton > button:focus-visible{
  box-shadow: 0 0 0 2px rgba(52,194,107,0.20) !important;
}



/* =========================
   PREMIUM INPUT SYSTEM OVERRIDE v2_81
   Goal: one cohesive "hardware-like" control for inputs + steppers (Stripe/Apple vibe).
   Fixes: disjoint +/- segments, divider gaps, corner mismatch, square/leaky focus paint, stray underlines.
   Keep this block LAST. If anything conflicts, this wins.
   ========================= */
:root{
  --rbv-input-radius: 12px;
  --rbv-input-h: 40px;

  --rbv-input-bg: #1E1F23;
  --rbv-input-border: rgba(255,255,255,0.14);
  --rbv-input-border-hover: rgba(255,255,255,0.22);

  --rbv-focus: rgba(61,155,255,0.78);
  --rbv-focus-ring: rgba(61,155,255,0.22);

  --rbv-input-text: rgba(247,250,255,0.92);
  --rbv-input-placeholder: rgba(247,250,255,0.55);

  --rbv-input-divider: rgba(255,255,255,0.12);
  --rbv-stepper-icon: rgba(247,250,255,0.52);
  --rbv-stepper-icon-focus: rgba(247,250,255,0.70);
  --rbv-stepper-icon-hover: rgba(247,250,255,0.92);
  --rbv-stepper-hover-bg: rgba(255,255,255,0.05);
  --rbv-stepper-active-bg: rgba(255,255,255,0.075);
}

/* Hard reset: no default focus paint anywhere inside our widgets */
body .stApp :is(
  div[data-testid="stNumberInput"],
  div[data-testid="stTextInput"],
  div[data-testid="stSelectbox"],
  div[data-testid="stTextArea"]
) :is(*:focus, *:focus-visible){
  outline: none !important;
  box-shadow: none !important;
}

/* Kill BaseWeb pseudo-element underlines that can render as stray horizontal rules */
body .stApp :is(
  div[data-baseweb="input"],
  div[data-baseweb="base-input"],
  div[data-baseweb="textarea"],
  div[data-baseweb="select"]
)::before,
body .stApp :is(
  div[data-baseweb="input"],
  div[data-baseweb="base-input"],
  div[data-baseweb="textarea"],
  div[data-baseweb="select"]
)::after{
  content: none !important;
  display: none !important;
}

/* Remove Streamlit's outer shells (prevents double borders / clipping artifacts) */
body .stApp :is(
  div[data-testid="stNumberInput"],
  div[data-testid="stTextInput"],
  div[data-testid="stSelectbox"],
  div[data-testid="stTextArea"]
) > div{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  overflow: visible !important;
}

/* ---------- TEXT INPUT (single shell) ---------- */
body .stApp div[data-testid="stTextInput"] div[data-baseweb="input"] > div{
  background: var(--rbv-input-bg) !important;
  border: 1px solid var(--rbv-input-border) !important;
  border-radius: var(--rbv-input-radius) !important;
  height: var(--rbv-input-h) !important;
  min-height: var(--rbv-input-h) !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: center !important;
  transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
}
body .stApp div[data-testid="stTextInput"] div[data-baseweb="input"] > div:hover{
  border-color: var(--rbv-input-border-hover) !important;
}
body .stApp div[data-testid="stTextInput"] div[data-baseweb="input"] > div:focus-within{
  border-color: var(--rbv-focus) !important;
  box-shadow: inset 0 0 0 2px var(--rbv-focus-ring) !important;
}

/* ---------- SELECTBOX (single shell) ---------- */
body .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] > div{
  background: var(--rbv-input-bg) !important;
  border: 1px solid var(--rbv-input-border) !important;
  border-radius: var(--rbv-input-radius) !important;
  height: var(--rbv-input-h) !important;
  min-height: var(--rbv-input-h) !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: center !important;
  transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
}
body .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover{
  border-color: var(--rbv-input-border-hover) !important;
}
body .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within{
  border-color: var(--rbv-focus) !important;
  box-shadow: inset 0 0 0 2px var(--rbv-focus-ring) !important;
}

/* ---------- TEXTAREA (single shell; allow height growth) ---------- */
body .stApp div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div{
  background: var(--rbv-input-bg) !important;
  border: 1px solid var(--rbv-input-border) !important;
  border-radius: var(--rbv-input-radius) !important;
  min-height: calc(var(--rbv-input-h) + 8px) !important;
  overflow: hidden !important;
  transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
}
body .stApp div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div:hover{
  border-color: var(--rbv-input-border-hover) !important;
}
body .stApp div[data-testid="stTextArea"] div[data-baseweb="textarea"] > div:focus-within{
  border-color: var(--rbv-focus) !important;
  box-shadow: inset 0 0 0 2px var(--rbv-focus-ring) !important;
}

/* ---------- NUMBER INPUT (single outer wrapper: input + steppers) ---------- */
/* Streamlit's NumberInput renders: [control-row wrapper] -> BaseWeb input + stepper buttons.
   Apply the "hardware" shell to the CONTROL-ROW wrapper so buttons and input merge as one unit. */

/* Preferred selector (modern browsers): wrapper that contains BaseWeb input */
body .stApp div[data-testid="stNumberInput"] > div:has(div[data-baseweb="input"]){
  background: var(--rbv-input-bg) !important;
  border: 1px solid var(--rbv-input-border) !important;
  border-radius: var(--rbv-input-radius) !important;
  height: var(--rbv-input-h) !important;
  min-height: var(--rbv-input-h) !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: stretch !important;
  gap: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  box-shadow: none !important;
  transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
}
body .stApp div[data-testid="stNumberInput"] > div:has(div[data-baseweb="input"]):hover{
  border-color: var(--rbv-input-border-hover) !important;
}
body .stApp div[data-testid="stNumberInput"] > div:has(div[data-baseweb="input"]):focus-within{
  border-color: var(--rbv-focus) !important;
  box-shadow: inset 0 0 0 2px var(--rbv-focus-ring) !important;
}

/* Fallback for environments without :has() support */
@supports not selector(:has(*)){
  body .stApp div[data-testid="stNumberInput"] > div{
    background: var(--rbv-input-bg) !important;
    border: 1px solid var(--rbv-input-border) !important;
    border-radius: var(--rbv-input-radius) !important;
    height: var(--rbv-input-h) !important;
    min-height: var(--rbv-input-h) !important;
    overflow: hidden !important;
    display: flex !important;
    align-items: stretch !important;
    gap: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
  }
  body .stApp div[data-testid="stNumberInput"] > div:hover{
    border-color: var(--rbv-input-border-hover) !important;
  }
  body .stApp div[data-testid="stNumberInput"] > div:focus-within{
    border-color: var(--rbv-focus) !important;
    box-shadow: inset 0 0 0 2px var(--rbv-focus-ring) !important;
  }
}

/* Neutralize BaseWeb input inner shells (prevents "left-only capsule") */
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"],
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="base-input"]{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  height: 100% !important;
  min-height: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  align-items: stretch !important;
  flex: 1 1 auto !important;
}
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="base-input"] > div{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  height: 100% !important;
  min-height: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  display: flex !important;
  align-items: stretch !important;
  flex: 1 1 auto !important;
}
body .stApp div[data-testid="stNumberInput"] div[data-baseweb="input"] > div > div{
  flex: 1 1 auto !important;
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
}

/* Integrated steppers: icon buttons with 1px full-height dividers (Stripe/Apple vibe) */
body .stApp div[data-testid="stNumberInput"] button{
  width: 40px !important;
  min-width: 40px !important;
  height: 100% !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;

  margin: 0 !important;
  padding: 0 !important;

  background: transparent !important;
  border: none !important;
  border-left: 1px solid var(--rbv-input-divider) !important;

  color: var(--rbv-stepper-icon) !important;
}
body .stApp div[data-testid="stNumberInput"] button svg{
  width: 13px !important;
  height: 13px !important;
  display: block !important;
}
body .stApp div[data-testid="stNumberInput"] button:hover{
  background: var(--rbv-stepper-hover-bg) !important;
  color: var(--rbv-stepper-icon-hover) !important;
}
body .stApp div[data-testid="stNumberInput"] button:active{
  background: var(--rbv-stepper-active-bg) !important;
  color: rgba(247,250,255,0.98) !important;
}
body .stApp div[data-testid="stNumberInput"] > div:focus-within button,
body .stApp div[data-testid="stNumberInput"] > div:has(div[data-baseweb="input"]):focus-within button{
  color: var(--rbv-stepper-icon-focus) !important;
}
/* Input element typography + vertical centering */
body .stApp :is(
  div[data-testid="stNumberInput"],
  div[data-testid="stTextInput"],
  div[data-testid="stSelectbox"]
) input{
  height: var(--rbv-input-h) !important;
  min-height: var(--rbv-input-h) !important;
  line-height: var(--rbv-input-h) !important;
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  margin: 0 !important;
  padding: 0 12px !important;
  color: var(--rbv-input-text) !important;
  -webkit-text-fill-color: var(--rbv-input-text) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  border-radius: 0 !important;
}
body .stApp div[data-testid="stTextArea"] textarea{
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  color: var(--rbv-input-text) !important;
  -webkit-text-fill-color: var(--rbv-input-text) !important;
  font-weight: 560 !important;
  font-size: 13px !important;
  padding: 10px 12px !important;
}
body .stApp :is(
  div[data-testid="stNumberInput"],
  div[data-testid="stTextInput"],
  div[data-testid="stSelectbox"]
) input::placeholder,
body .stApp div[data-testid="stTextArea"] textarea::placeholder{
  color: var(--rbv-input-placeholder) !important;
  -webkit-text-fill-color: var(--rbv-input-placeholder) !important;
}

/* Selectbox typography + vertical centering */
body .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] > div{
  padding: 0 !important;
}
body .stApp div[data-testid="stSelectbox"] div[data-baseweb="select"] span{
  color: var(--rbv-input-text) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  line-height: 1.2 !important;
}
body .stApp div[data-testid="stSelectbox"] svg{
  fill: rgba(247,250,255,0.78) !important;
}

/* Label row: guarantee icon + text are perfectly centered */
.rbv-label-text{ display:flex !important; align-items:center !important; }
.rbv-help{ align-items:center !important; }
.rbv-help-icon{ display:inline-flex !important; align-items:center !important; justify-content:center !important; line-height: 1 !important; }

/* ========================= END PREMIUM INPUT OVERRIDE ========================= */



/* --- Hide default dividers (avoid empty rounded "banners") --- */
hr, div[data-testid="stDivider"]{
  display:none !important;
  height:0 !important;
  border:0 !important;
  margin:0 !important;
  padding:0 !important;
}

/* ====================================================== */
"""


# Action button emphasis (v2.85)
# - Primary buttons (compute/download/enable) should be visually obvious (green).
# - Secondary buttons are reserved for destructive actions (stop/disable) (red).
_RBV_ACTION_BUTTONS_CSS = r"""
/* ================= RBV ACTION BUTTON EMPHASIS (v2.88) =================
   Goal: premium fintech look on dark theme:
   - Tinted glassy gradients (not flat neon)
   - Light text (white/soft gray) consistent with rest of UI
   - Clear primary vs destructive affordance
====================================================================== */
:root{
  /* Muted, premium accents (avoid neon) */
  --rbv-action: rgba(52,194,107,0.32);
  --rbv-action-2: rgba(52,194,107,0.14);
  --rbv-action-border: rgba(52,194,107,0.45);

  --rbv-danger: rgba(224,82,82,0.30);
  --rbv-danger-2: rgba(224,82,82,0.12);
  --rbv-danger-border: rgba(224,82,82,0.46);

  --rbv-btn-base: rgba(18,22,30,0.92);
  --rbv-btn-text: rgba(243,245,248,0.92);   /* soft white */
  --rbv-btn-text-2: rgba(243,245,248,0.86);
}

/* Shared button polish */
div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button,
button[data-testid^="baseButton-"]{
  border-radius: 14px !important;
  letter-spacing: 0.01em !important;
  transition: transform 120ms ease, box-shadow 140ms ease, filter 140ms ease, border-color 140ms ease !important;
}

/* Primary (green) */
button[kind="primary"],
button[data-testid="baseButton-primary"],
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stDownloadButton"] button[kind="primary"]{
  background:
    linear-gradient(180deg, var(--rbv-action) 0%, var(--rbv-action-2) 100%),
    var(--rbv-btn-base) !important;
  border: 1px solid var(--rbv-action-border) !important;
  color: var(--rbv-btn-text) !important;
  font-weight: 780 !important;
  box-shadow:
    0 12px 28px rgba(0,0,0,0.40),
    0 10px 26px rgba(52,194,107,0.14),
    0 0 0 1px rgba(255,255,255,0.04) inset,
    0 1px 0 rgba(255,255,255,0.05) inset !important;
}
button[kind="primary"] * ,
button[data-testid="baseButton-primary"] *{
  color: var(--rbv-btn-text) !important;
}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover,
div[data-testid="stButton"] button[kind="primary"]:hover,
div[data-testid="stDownloadButton"] button[kind="primary"]:hover{
  border-color: rgba(52,194,107,0.62) !important;
  filter: saturate(1.06) brightness(1.02) !important;
  box-shadow:
    0 14px 32px rgba(0,0,0,0.44),
    0 12px 30px rgba(52,194,107,0.20),
    0 0 0 1px rgba(255,255,255,0.05) inset,
    0 1px 0 rgba(255,255,255,0.07) inset !important;
  transform: translateY(-1px) !important;
}
button[kind="primary"]:active,
button[data-testid="baseButton-primary"]:active{
  transform: translateY(0px) !important;
}

/* Destructive (red) — use ONLY for destructive actions */
button[kind="secondary"],
button[data-testid="baseButton-secondary"],
div[data-testid="stButton"] button[kind="secondary"]{
  background:
    linear-gradient(180deg, var(--rbv-danger) 0%, var(--rbv-danger-2) 100%),
    var(--rbv-btn-base) !important;
  border: 1px solid var(--rbv-danger-border) !important;
  color: var(--rbv-btn-text) !important;
  font-weight: 790 !important;
  box-shadow:
    0 12px 28px rgba(0,0,0,0.40),
    0 10px 26px rgba(224,82,82,0.12),
    0 0 0 1px rgba(255,255,255,0.04) inset,
    0 1px 0 rgba(255,255,255,0.05) inset !important;
}
button[kind="secondary"] * ,
button[data-testid="baseButton-secondary"] *{
  color: var(--rbv-btn-text) !important;
}

button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
div[data-testid="stButton"] button[kind="secondary"]:hover{
  border-color: rgba(224,82,82,0.66) !important;
  filter: saturate(1.06) brightness(1.02) !important;
  box-shadow:
    0 14px 32px rgba(0,0,0,0.44),
    0 12px 30px rgba(224,82,82,0.18),
    0 0 0 1px rgba(255,255,255,0.05) inset,
    0 1px 0 rgba(255,255,255,0.07) inset !important;
  transform: translateY(-1px) !important;
}

/* Keyboard focus (accessibility): strong but on-brand */
button[kind="primary"]:focus-visible,
button[data-testid="baseButton-primary"]:focus-visible{
  outline: 2px solid rgba(52,194,107,0.70) !important;
  outline-offset: 2px !important;
}
button[kind="secondary"]:focus-visible,
button[data-testid="baseButton-secondary"]:focus-visible{
  outline: 2px solid rgba(224,82,82,0.72) !important;
  outline-offset: 2px !important;
}
/* ================= END ACTION BUTTON EMPHASIS ================= */
"""



def _apply_palette(css: str, buy_color: str, rent_color: str) -> str:
    """Replace legacy hard-coded palette values with the current theme palette."""
    css = css.replace("#2F8BFF", buy_color).replace("#E6B800", rent_color)

    # Also replace common rgba() occurrences for the legacy colors used across charts/borders.
    def _hex_to_rgb(h: str):
        h = (h or "").lstrip("#")
        if len(h) != 6:
            return (0, 0, 0)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    br, bg, bb = _hex_to_rgb(buy_color)
    rr, rg, rb = _hex_to_rgb(rent_color)

    css = css.replace("rgba(47,139,255", f"rgba({br},{bg},{bb}".format(br=br, bg=bg, bb=bb))
    css = css.replace("rgba(230,184,0", f"rgba({rr},{rg},{rb}".format(rr=rr, rg=rg, rb=rb))
    return css


def inject_global_css(st, *, buy_color: str = BUY_COLOR, rent_color: str = RENT_COLOR) -> None:
    """Inject the RBV global stylesheet.

    NOTE:
    Streamlit reruns can recreate the page DOM and drop previously injected <style> tags.
    If we inject CSS only "once" using a session_state flag, the app can enter a
    "missing CSS" state after reruns (e.g., toggling Fast↔Quality), which makes
    tooltip bubbles render inline and layouts appear broken.

    Therefore we intentionally inject on *every* run. Duplicate CSS blocks are
    harmless and are preferable to intermittent styling loss.
    """

    css = _apply_palette(_RBV_GLOBAL_CSS_RAW + "\n" + _RBV_ACTION_BUTTONS_CSS, buy_color, rent_color)

    st.markdown(
        "<style>\n" + css + "\n</style>",
        unsafe_allow_html=True,
    )

    # Intentionally do not gate on a session_state "injected" flag.


# Backwards-compatible alias (older app.py variants called this)
def inject_progress_css(st) -> None:
    inject_global_css(st)
