"""TagForge visual theme: color tokens and the shared stylesheet.

Every page calls apply_theme() (via layout.frame) so colors live in one place.
Change a token here and every screen follows.
"""
from nicegui import ui

COLORS = {
    'bg':         '#0b0f10',   # page background
    'surface':    '#111718',   # panels and tiles
    'surface_2':  '#162022',   # inputs, hover rows
    'border':     '#243033',
    'text':       '#e6edee',
    'muted':      '#8a9a9d',
    'accent':     '#19c39a',   # primary action / active nav
    'accent_dim': '#0f3b33',
    'warn':       '#e0a43a',
    'fail':       '#e5534b',
}

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600'
    '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
)

C = COLORS
CSS = f"""
:root {{
  --tf-bg: {C['bg']}; --tf-surface: {C['surface']}; --tf-surface-2: {C['surface_2']};
  --tf-border: {C['border']}; --tf-text: {C['text']}; --tf-muted: {C['muted']};
  --tf-accent: {C['accent']}; --tf-accent-dim: {C['accent_dim']};
  --tf-warn: {C['warn']}; --tf-fail: {C['fail']};
}}
body, .q-page, .nicegui-content {{
  background: var(--tf-bg); color: var(--tf-text);
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}}
.nicegui-content {{ padding: 0; }}
.tf-mono {{ font-family: 'IBM Plex Mono', ui-monospace, monospace; }}

/* ---- header ---- */
.tf-header {{ background: var(--tf-bg) !important; border-bottom: 1px solid var(--tf-border);
  padding: 10px 24px; align-items: center; gap: 24px; }}
.tf-logo {{ background: var(--tf-accent); color: #04120e; border-radius: 8px;
  font-size: 22px; padding: 6px; }}
.tf-brand {{ font-size: 20px; font-weight: 700; color: var(--tf-text); }}
.tf-version {{ font-size: 12px; color: var(--tf-muted); letter-spacing: .08em; margin-top: 4px; }}
.tf-nav {{ gap: 4px; }}
.tf-nav-link {{ color: var(--tf-muted); text-decoration: none; padding: 8px 14px;
  border-radius: 6px; font-weight: 500; }}
.tf-nav-link:hover {{ color: var(--tf-text); background: var(--tf-surface-2); }}
.tf-nav-link.active {{ color: var(--tf-accent); background: var(--tf-accent-dim); font-weight: 600; }}
.tf-db-pill {{ border: 1px solid var(--tf-border); border-radius: 999px; padding: 6px 14px;
  gap: 10px; align-items: center; font-size: 13px; }}
.tf-db-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--tf-muted); }}
.tf-db-dot.ok {{ background: var(--tf-accent); }}

/* ---- page grid: side column | main column ---- */
.tf-page {{ padding: 20px 24px; width: 100%; }}
.tf-workspace {{ display: grid; grid-template-columns: 400px 1fr; gap: 20px;
  width: 100%; align-items: start; }}
.tf-side, .tf-main {{ gap: 20px; width: 100%; min-width: 0; }}
@media (max-width: 1100px) {{ .tf-workspace {{ grid-template-columns: 1fr; }} }}

/* ---- panels ---- */
.tf-panel {{ background: var(--tf-surface); border: 1px solid var(--tf-border);
  border-radius: 10px; width: 100%; }}
.tf-panel-head {{ padding: 16px 20px; align-items: center; gap: 12px; width: 100%; }}
.tf-panel-title {{ font-size: 17px; font-weight: 600; }}
.tf-panel-body {{ padding: 0 20px 20px; gap: 12px; width: 100%; }}
.tf-badge {{ background: var(--tf-surface-2); color: var(--tf-muted); border-radius: 4px;
  padding: 2px 8px; font-size: 11px; letter-spacing: .1em; font-weight: 600;
  font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; }}

/* ---- status tiles ---- */
.tf-tiles {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 100%; }}
.tf-tile {{ background: var(--tf-surface); border: 1px solid var(--tf-border);
  border-radius: 10px; padding: 18px 20px; gap: 6px; min-height: 130px; }}
.tf-tile-value {{ font-size: 28px; font-weight: 700; font-family: 'IBM Plex Mono', monospace; }}
.tf-tile-value.ok {{ color: var(--tf-accent); }}
.tf-tile-value.warn {{ color: var(--tf-warn); }}
.tf-tile-value.fail {{ color: var(--tf-fail); }}
.tf-caption {{ color: var(--tf-muted); font-size: 13px; }}

/* ---- small caps field label ---- */
.tf-label {{ color: var(--tf-muted); font-size: 11px; font-weight: 600;
  letter-spacing: .12em; text-transform: uppercase; }}

/* ---- tables (Quasar q-table) ---- */
.tf-panel .q-table__container, .tf-panel .q-table {{ background: transparent; }}
.tf-panel .q-table th {{ color: var(--tf-muted); font-size: 11px; font-weight: 600;
  letter-spacing: .12em; text-transform: uppercase; }}
.tf-panel .q-table tbody tr:hover {{ background: var(--tf-surface-2); }}

/* ---- empty states ---- */
.tf-empty {{ width: 100%; padding: 40px 20px; align-items: center; gap: 6px; text-align: center; }}
.tf-empty-title {{ color: var(--tf-muted); font-size: 16px; }}
"""


def apply_theme() -> None:
    """Load fonts, Quasar brand colors, and the shared stylesheet into the current page."""
    ui.add_head_html(FONTS)
    ui.colors(primary=C['accent'], positive=C['accent'],
              warning=C['warn'], negative=C['fail'], dark=C['bg'])
    ui.add_css(CSS)
