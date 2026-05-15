import streamlit as st
import subprocess
import sys
import re
import base64
import time
import signal
import io
from pathlib import Path
import os
import json
import yaml
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit.components.v1 import html as st_html
from datetime import datetime

# ── Optional: fpdf2 for PDF export ──────────────────────────────────────────
# Install with:  pip install fpdf2
try:
    from fpdf import FPDF
    _FPDF_OK = True
except ImportError:
    _FPDF_OK = False

# ==============================================================================
# 1. Page Configuration
# ==============================================================================

st.set_page_config(
    page_title="ProcSentinel | Memory Forensics",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR             = Path(__file__).resolve().parent
CLI_SCRIPT_PATH      = BASE_DIR / "runner.py"
MEMORY_FOLDER        = BASE_DIR / "memory"
OUTPUT_FOLDER        = BASE_DIR / "out"
BASELINE_FILE_PATH   = BASE_DIR / "baseline.yaml"
DETECTIONS_FILE_PATH = BASE_DIR / "detections.yaml"

try:
    MEMORY_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# ==============================================================================
# 2. Design System CSS
#    Palette:
#      bg_deep    #080c14   deepest background
#      bg_surface #0f1623   page background
#      bg_card    #141e2e   card fill
#      bg_raised  #1a2540   elevated element
#      border     #1e2d45   default border
#      accent     #3b82f6   blue primary
#      teal       #0ea5e9   secondary highlight
#      green      #10b981   success / positive
#      red        #ef4444   critical
#      orange     #f97316   high
#      yellow     #eab308   medium
#      text_hi    #e2e8f0   primary text
#      text_mid   #94a3b8   secondary text
#      text_lo    #475569   muted text
# ==============================================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Syne:wght@700;800&display=swap');

/* ── Reset ── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

/* ── Page background ── */
.stApp,[data-testid="stAppViewContainer"],.main{background:#060b14!important}
.block-container{padding:0!important;max-width:100%!important}
header[data-testid="stHeader"],div[data-testid="stDecoration"],div[data-testid="stToolbar"],section[data-testid="stSidebar"]{display:none!important}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:#060b14}
::-webkit-scrollbar-thumb{background:#1e3a5f;border-radius:4px}

/* ── Typography ── */
/* NOTE: div and span are intentionally EXCLUDED from the global rule.
   Streamlit's expander internals use div/span for SVG icon labels like
   _arrow_right. Making those visible causes text to stack on expander headers.
   Scope font/color to .block-container content only instead. */
body,p,li,td,th{font-family:'Inter',sans-serif!important;color:#cbd5e1}
h1,h2,h3,h4{font-family:'Inter',sans-serif!important;color:#e2e8f0}
.block-container p,
.block-container li,
.block-container td,
.block-container th{font-family:'Inter',sans-serif!important;color:#cbd5e1}

/* ── Inputs ── */
.stTextInput>div>div>input,.stPasswordInput>div>div>input{
  background:#0d1b2e!important;border:1px solid #1e3a5f!important;
  color:#e2e8f0!important;font-family:'Inter',sans-serif!important;
  font-size:14px!important;border-radius:8px!important;padding:10px 14px!important}
.stTextInput>div>div>input:focus,.stPasswordInput>div>div>input:focus{
  border-color:#3b82f6!important;box-shadow:0 0 0 3px rgba(59,130,246,.15)!important}
.stTextInput label,.stPasswordInput label,.stSelectbox label{
  color:#64748b!important;font-size:11px!important;font-weight:600!important;
  letter-spacing:.6px!important;text-transform:uppercase!important}

/* ── Selectbox ── */
.stSelectbox>div>div>div{background:#0d1b2e!important;border:1px solid #1e3a5f!important;
  color:#e2e8f0!important;border-radius:8px!important}
.stSelectbox [data-baseweb="popover"],.stSelectbox [data-baseweb="menu"],
.stSelectbox ul,.stSelectbox li{background:#0d1b2e!important;color:#e2e8f0!important;
  border:1px solid #1e3a5f!important}

/* ── Buttons ── */
.stButton>button{background:transparent!important;border:1px solid #1e3a5f!important;
  color:#64748b!important;font-family:'Inter',sans-serif!important;
  font-weight:500!important;font-size:13px!important;border-radius:8px!important;
  padding:8px 18px!important;transition:all .2s!important;letter-spacing:.2px}
.stButton>button:hover{border-color:#3b82f6!important;color:#60a5fa!important;
  background:rgba(59,130,246,.06)!important}
.stFormSubmitButton>button,.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#1d4ed8,#3b82f6)!important;
  border-color:#3b82f6!important;color:#fff!important;
  font-weight:600!important;letter-spacing:.3px}
.stFormSubmitButton>button:hover{background:linear-gradient(135deg,#1e40af,#2563eb)!important}

/* ── Progress ── */
.stProgress>div>div>div>div{background:linear-gradient(90deg,#1d4ed8,#3b82f6)!important;border-radius:6px!important}
.stProgress>div>div{background:#0d1b2e!important;border:1px solid #1e3a5f!important;border-radius:6px!important;height:8px!important}
.stProgress p,.stProgress span{color:#64748b!important;font-size:12px!important}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #1e3a5f!important;gap:2px!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#64748b!important;
  border:none!important;padding:10px 20px!important;font-size:13px!important;
  font-weight:500!important;border-bottom:2px solid transparent!important;transition:.2s}
.stTabs [aria-selected="true"]{color:#60a5fa!important;border-bottom:2px solid #3b82f6!important;background:transparent!important}

/* ── Expanders ── */
.streamlit-expanderHeader{background:#0d1b2e!important;border:1px solid #1e3a5f!important;
  border-radius:10px!important;padding:14px 18px!important;transition:.2s;margin-bottom:6px!important}
.streamlit-expanderHeader:hover{border-color:#3b82f6!important;background:#0f2040!important}
.streamlit-expanderContent{background:#0a1628!important;border:1px solid #1e3a5f!important;
  border-top:none!important;border-radius:0 0 10px 10px!important;padding:20px!important}

/* ── Dataframe ── */
.stDataFrame{border-radius:10px!important;overflow:hidden!important;border:1px solid #1e3a5f!important}
.stDataFrame [data-testid="stDataFrameResizable"]{background:#060e1d!important}

/* ── Alerts ── */
.stInfo{background:rgba(59,130,246,.08)!important;border:1px solid rgba(59,130,246,.25)!important;
  border-radius:10px!important;color:#93c5fd!important}
.stWarning{background:rgba(234,179,8,.08)!important;border:1px solid rgba(234,179,8,.25)!important;
  border-radius:10px!important;color:#fde68a!important}

/* ── Attack path ── */
.attack-path-container{display:flex;flex-wrap:wrap;align-items:flex-start;gap:0;margin:16px 0}
.attack-step{background:#0d1b2e;border:1px solid #1e3a5f;border-radius:10px;
  padding:14px 18px;flex:1;min-width:160px;max-width:280px;transition:.2s}
.attack-step:hover{border-color:#3b82f6}
.attack-step b{color:#60a5fa;font-size:12px;font-weight:600;display:block;margin-bottom:6px}
.attack-step hr{border:none;border-top:1px solid #1e3a5f;margin:6px 0}
.attack-step p{font-size:12px;color:#94a3b8;line-height:1.5}
.attack-arrow{display:flex;align-items:center;padding:0 8px;color:#3b82f6;font-size:20px;
  font-weight:700;align-self:center}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 3. Topbar & UI helpers
# ==============================================================================

def topbar(active):
    steps = ["Login", "New Analysis", "Progress", "Results"]
    pills = ""
    for i, s in enumerate(steps):
        if s == active:
            pills += (
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'background:#1a2540;border:1px solid #3b82f6;border-radius:20px;'
                f'padding:5px 14px 5px 8px;">'
                f'<div style="width:20px;height:20px;border-radius:50%;background:#3b82f6;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:10px;font-weight:700;color:#fff;flex-shrink:0;">{i+1}</div>'
                f'<span style="font-size:12px;font-weight:600;color:#60a5fa;'
                f'white-space:nowrap;">{s}</span>'
                f'</div>'
            )
        else:
            pills += (
                f'<div style="display:flex;align-items:center;gap:7px;'
                f'padding:5px 14px 5px 8px;opacity:.45;">'
                f'<div style="width:20px;height:20px;border-radius:50%;background:#1e2d45;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:10px;font-weight:700;color:#94a3b8;flex-shrink:0;">{i+1}</div>'
                f'<span style="font-size:12px;font-weight:500;color:#94a3b8;'
                f'white-space:nowrap;">{s}</span>'
                f'</div>'
            )

    st.markdown(f"""
    <div style="background:#080c14;border-bottom:1px solid #1e2d45;
                display:flex;align-items:center;padding:0 28px;height:56px;
                position:sticky;top:0;z-index:100;">

      <!-- Logo -->
      <div style="display:flex;align-items:center;gap:10px;margin-right:36px;flex-shrink:0;">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <path d="M14 2L26 8.5V19.5L14 26L2 19.5V8.5L14 2Z"
                fill="#3b82f6" fill-opacity=".15"
                stroke="#3b82f6" stroke-width="1.5"/>
          <path d="M14 7L21 10.75V17.25L14 21L7 17.25V10.75L14 7Z"
                fill="#3b82f6" fill-opacity=".3"/>
          <circle cx="14" cy="14" r="3" fill="#60a5fa"/>
        </svg>
        <div>
          <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
                      color:#e2e8f0;letter-spacing:.5px;line-height:1.1;">PROCSENTINEL</div>
          <div style="font-size:9px;color:#475569;letter-spacing:.5px;line-height:1;">MEMORY FORENSICS</div>
        </div>
      </div>

      <!-- Step pills -->
      <div style="display:flex;align-items:center;gap:6px;">{pills}</div>

      <!-- Spacer -->
      <div style="flex:1;"></div>

      <!-- Status indicator -->
      <div style="display:flex;align-items:center;gap:8px;
                  background:#141e2e;border:1px solid #1e2d45;
                  border-radius:20px;padding:6px 14px;">
        <div style="width:7px;height:7px;border-radius:50%;
                    background:#10b981;animation:pulse 2s infinite;"></div>
        <span style="font-size:11px;color:#94a3b8;font-weight:500;">System Ready</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def page_header(eyebrow, heading, sub=None):
    """Section header: small label + large title + optional subtitle."""
    sub_html = (f'<p style="font-size:13px;color:#475569;margin-top:4px;'
                f'font-family:\'Inter\',sans-serif;">{sub}</p>') if sub else ""
    st.markdown(f"""
    <div style="padding:32px 40px 0;">
      <p style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:2.5px;
                text-transform:uppercase;margin-bottom:8px;
                font-family:'Inter',sans-serif;">{eyebrow}</p>
      <h1 style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;
                 color:#e2e8f0;margin:0;line-height:1.1;">{heading}</h1>
      {sub_html}
    </div>
    """, unsafe_allow_html=True)


def divider():
    st.markdown('<hr style="margin:24px 40px;border-top:1px solid #1e2d45;">', unsafe_allow_html=True)


def section_label(text):
    st.markdown(
        f'<p style="font-size:10px;font-weight:600;color:#475569;letter-spacing:2px;'
        f'text-transform:uppercase;margin-bottom:10px;font-family:\'Inter\',sans-serif;">'
        f'{text}</p>',
        unsafe_allow_html=True
    )


def card(content_fn, padding="24px 28px"):
    """Wrapper that renders content inside a styled card."""
    st.markdown(
        f'<div style="background:#141e2e;border:1px solid #1e2d45;border-radius:12px;'
        f'padding:{padding};margin-bottom:16px;">',
        unsafe_allow_html=True
    )
    content_fn()
    st.markdown('</div>', unsafe_allow_html=True)


def stat_card(label_text, value, color="#3b82f6", sub=None):
    sub_html = (f'<div style="font-size:11px;color:#475569;margin-top:4px;">{sub}</div>') if sub else ""
    st.markdown(f"""
    <div style="background:#141e2e;border:1px solid #1e2d45;border-radius:12px;
                padding:20px 24px;height:100%;">
      <div style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;
                  text-transform:uppercase;margin-bottom:10px;font-family:'Inter',sans-serif;">
        {label_text}
      </div>
      <div style="font-family:'Syne',sans-serif;font-size:34px;font-weight:800;
                  line-height:1;color:{color};">{value}</div>
      {sub_html}
    </div>
    """, unsafe_allow_html=True)


def stat_row(items):
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        with col:
            stat_card(it['label'], it['value'], it.get('color','#3b82f6'), it.get('sub'))


# ==============================================================================
# 4. Backend helpers (logic unchanged)
# ==============================================================================

def html_escape(t):
    """HTML-escape using stdlib for correctness."""
    import html as _html_mod
    if t is None: return ""
    return _html_mod.escape(str(t), quote=True)


def get_friendly_scan_name(plugin_name):
    mapping = {
        "windows.info":"Detecting operating system...",
        "windows.pslist":"Analyzing running processes...",
        "windows.psxview":"Scanning for hidden processes...",
        "windows.netscan":"Investigating network connections...",
        "windows.netstat":"Checking network statistics...",
        "windows.malfind":"Searching for injected code...",
        "windows.hollowprocesses":"Checking for hollowed processes...",
        "windows.ldrmodules":"Analyzing loaded modules for unlinked DLLs...",
        "windows.handles":"Inspecting process handles...",
        "windows.svcscan":"Scanning system services...",
        "windows.scheduled_tasks":"Reviewing scheduled tasks for persistence...",
        "windows.filescan":"Scanning for suspicious files in memory...",
        "windows.registry.printkey":"Querying registry keys for anomalies...",
        "windows.registry.userassist":"Analyzing user execution history...",
        "windows.sessions":"Inspecting user logon sessions...",
        "linux.pslist":"Analyzing Linux processes...",
        "linux.psscan":"Scanning Linux for hidden processes...",
        "linux.lsof":"Checking Linux open files and network connections...",
        "linux.sockstat":"Analyzing Linux socket statistics...",
        "linux.check_syscall":"Checking system call table integrity...",
        "linux.check_modules":"Checking Linux kernel modules...",
        "linux.bash":"Analyzing Linux Bash history...",
        "mac.pslist":"Analyzing macOS processes...",
        "mac.lsof":"Checking macOS open files and network connections...",
        "mac.netstat":"Checking macOS network statistics...",
        "mac.malfind":"Searching macOS for injected code...",
        "mac.bash":"Analyzing macOS Bash history...",
        "windows.dlllist":"Listing loaded DLLs for each process...",
        "windows.apihooks":"Detecting Windows API hooks...",
        "windows.devicetree":"Analyzing Windows device tree...",
        "windows.modscan":"Scanning Windows kernel modules...",
        "windows.consoles":"Recovering Windows console history...",
        "windows.clipboard":"Recovering clipboard contents...",
        "windows.registry.shimcache":"Analyzing Windows Shimcache...",
        "windows.registry.amcache":"Analyzing Windows Amcache...",
        "windows.envars":"Listing Windows environment variables...",
        "windows.callbacks":"Analyzing Windows kernel callbacks...",
        "linux.envars":"Listing Linux environment variables...",
        "linux.librarylist":"Enumerating Linux shared libraries...",
        "linux.lsmod":"Listing Linux loaded kernel modules...",
        "mac.sessions":"Listing macOS user sessions...",
        "mac.mount":"Displaying macOS mounted filesystems...",
        "mac.volumes":"Listing macOS volumes...",
        "mac.dmesg":"Recovering macOS kernel ring buffer messages...",
    }
    return mapping.get(plugin_name, f"Running scan: {plugin_name}...")


def load_findings(project_name):
    # Runner writes findings.jsonl directly into outdir (out/<case>/findings.jsonl).
    # Check both the case root and artifacts subfolder as fallback.
    candidates = [
        OUTPUT_FOLDER / project_name / "findings.jsonl",
        OUTPUT_FOLDER / project_name / "artifacts" / "findings.jsonl",
    ]
    findings = []
    for fpath in candidates:
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        findings.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            if findings:
                break
    return findings


def load_detections_config():
    if DETECTIONS_FILE_PATH.exists():
        with open(DETECTIONS_FILE_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


def load_baseline_config():
    if BASELINE_FILE_PATH.exists():
        with open(BASELINE_FILE_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


def get_narrative(finding_id, detections_config):
    if not detections_config: return "Detections config not found."
    for os_profile in detections_config.get('os_profiles', {}).values():
        for rule in os_profile.get('detections', []):
            if rule.get('id') == finding_id:
                n = rule.get('narrative', 'No narrative available.')
                n = n.replace("psxview mismatch","hidden process detection anomaly")
                n = n.replace("LdrModules","loaded modules").replace("ldrmodules","loaded modules")
                if ("network" in n.lower() or "c2" in n.lower()) and "command and control" not in n.lower():
                    n += " This communication often serves as a Command and Control (C2) channel."
                return n
    return "Narrative not found."


def weight_to_severity(w: int) -> str:
    """Map individual finding weight to severity label (per-finding, not cumulative).
    NOTE: The cumulative aggregate score uses separate severity bands in baseline.yaml.
    """
    w = int(w or 0)
    if w >= 85: return "Critical"
    if w >= 65: return "High"
    if w >= 45: return "Medium"
    if w >= 20: return "Low"
    return "Informational"


def categorize_findings(findings, detections_config):
    counts = {"Critical":0,"High":0,"Medium":0,"Low":0,"Informational":0}
    total_score = 0
    for f in findings:
        w = f.get('weight', 0)
        total_score += w
        sev = weight_to_severity(w)
        counts[sev] += 1
    # Overall severity based on highest individual finding
    if counts["Critical"] > 0:       overall = "Critical"
    elif counts["High"] > 0:         overall = "High"
    elif counts["Medium"] > 0:       overall = "Medium"
    elif counts["Low"] > 0:          overall = "Low"
    else:                            overall = "Informational"
    return counts, overall, total_score


def get_user_friendly_correlated_title(finding_id):
    mapping = {
        'psxview_hidden':'Hidden Process Detected',
        'suspicious_connection':'Suspicious Network Connection',
        'suspicious_port_activity':'Suspicious Port Usage',
        'suspicious_network_enrichment':'Malicious IP Communication',
        'malfind_injection':'Code Injection Found',
        'ldr_unlinked_module':'Hidden Module Loaded',
        'suspicious_cmdline_args':'Suspicious Command Line',
        'registry_run_key_persistence':'Registry Persistence',
        'exec_from_tmp':'Execution From Temp Directory',
        'filescan_suspicious_names':'Suspicious File Found',
        'unusual_parent_child':'Unusual Parent Process',
        'bash_history_suspicious':'Suspicious Shell Command',
        'kernel_callbacks_suspicious':'Kernel Callback Hook',
        'modules_hidden_vs_modscan':'Kernel Module Hiding',
        'registry_orphan_hives':'Orphaned Registry Hive',
    }
    return mapping.get(finding_id, finding_id.replace('_',' ').title())


# ==============================================================================
# 4-B. Cancel / PID file helpers  (used by Progress screen)
# ==============================================================================

def _pid_file(case: str) -> Path:
    """Temp file that holds the runner subprocess PID while it is running."""
    return OUTPUT_FOLDER / f".pid_{case}"

def _cancel_file(case: str) -> Path:
    """Sentinel file.  When it exists the progress loop kills the process."""
    return OUTPUT_FOLDER / f".cancel_{case}"


# ==============================================================================
# 4-C. PDF report generator
# ==============================================================================

def _hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

_SEV_HEX = {
    "Critical": "#ef4444", "High": "#f97316",
    "Medium": "#eab308",   "Low": "#3b82f6",
    "Informational": "#475569",
}

def _sanitize_pdf_text(text: str) -> str:
    """
    Replace Unicode characters that Helvetica (latin-1 / cp1252) cannot encode.
    fpdf2's core fonts only cover the Windows-1252 code page; anything outside
    that range raises FPDFUnicodeEncodingException.
    """
    if not text:
        return ""
    REPLACEMENTS = {
        "\u2014": "--",   # em dash          —
        "\u2013": "-",    # en dash          –
        "\u2026": "...",  # ellipsis         …
        "\u2018": "'",    # left single quote '
        "\u2019": "'",    # right single quote/apostrophe '
        "\u201c": '"',    # left double quote "
        "\u201d": '"',    # right double quote "
        "\u2022": "*",    # bullet           •
        "\u00b7": "·",    # middle dot (safe in cp1252)
        "\u2192": "->",   # right arrow      →
        "\u00ae": "(R)",  # registered sign  ®
        "\u00a0": " ",    # non-breaking space
        "\u200b": "",     # zero-width space
        "\u200e": "",     # left-to-right mark
        "\u200f": "",     # right-to-left mark
        "\u00e2\u0080\u0094": "--",  # utf-8 mis-decoded em dash
    }
    for char, replacement in REPLACEMENTS.items():
        text = text.replace(char, replacement)
    # Final safety net: drop any remaining characters outside latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf_report(case_name, findings, counts, overall, total_score, detections_cfg):
    """
    Build a formatted PDF and return (bytes_or_None, error_str_or_None).
    Requires fpdf2 ─ pip install fpdf2
    """
    if not _FPDF_OK:
        return None, "fpdf2 is not installed.  Run:  pip install fpdf2"

    # Sanitize all text that will pass through fpdf (latin-1 only)
    case_name = _sanitize_pdf_text(case_name)

    individual = sorted(
        [f for f in findings if not str(f.get('id', '')).startswith('correlation_')],
        key=lambda x: x.get('weight', 0), reverse=True,
    )
    n_total  = len(individual)
    sc_rgb   = _hex_to_rgb(_SEV_HEX.get(overall, "#94a3b8"))
    now_str  = datetime.now().strftime('%Y-%m-%d  %H:%M')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Cover page ─────────────────────────────────────────────────────────────
    pdf.add_page()

    # Dark header bar
    pdf.set_fill_color(6, 11, 20)
    pdf.rect(0, 0, 210, 46, 'F')
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(226, 232, 240)
    pdf.set_xy(14, 13)
    pdf.cell(0, 10, "PROCSENTINEL", ln=0)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_xy(14, 26)
    pdf.cell(0, 5, "Memory Forensics Platform  |  Incident Report", ln=0)
    pdf.set_xy(130, 23)
    pdf.cell(0, 5, f"Generated: {now_str}", ln=0)

    # Case title
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(226, 232, 240)
    pdf.set_xy(14, 56)
    pdf.cell(0, 12, f"Case: {case_name}", ln=1)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(148, 163, 184)
    pdf.set_x(14)
    pdf.cell(0, 6, f"{n_total} individual findings detected", ln=1)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*sc_rgb)
    pdf.set_x(14)
    pdf.cell(0, 6, f"Overall Threat Level: {overall}    Aggregate Risk Score: {total_score}", ln=1)

    # Divider
    pdf.set_draw_color(30, 58, 95)
    pdf.set_line_width(0.5)
    y_div = pdf.get_y() + 4
    pdf.line(14, y_div, 196, y_div)
    pdf.ln(10)

    # KPI cards (6 across)
    kpi_items = [
        ("TOTAL",    str(n_total),                    (226, 232, 240)),
        ("CRITICAL", str(counts.get("Critical", 0)), (239, 68,  68 )),
        ("HIGH",     str(counts.get("High", 0)),     (249, 115, 22 )),
        ("MEDIUM",   str(counts.get("Medium", 0)),   (234, 179, 8  )),
        ("LOW",      str(counts.get("Low", 0)),      (59,  130, 246)),
        ("SCORE",    str(total_score),                sc_rgb         ),
    ]
    card_w, gap = 29, 2
    base_y = pdf.get_y()
    for i, (lbl, val, rgb) in enumerate(kpi_items):
        x = 14 + i * (card_w + gap)
        pdf.set_fill_color(13, 27, 46)
        pdf.set_draw_color(30, 58, 95)
        pdf.rect(x, base_y, card_w, 22, 'FD')
        pdf.set_fill_color(*rgb)
        pdf.rect(x, base_y, card_w, 3, 'F')          # coloured top stripe
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(71, 85, 105)
        pdf.set_xy(x + 2, base_y + 5)
        pdf.cell(card_w - 4, 4, lbl, ln=0)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*rgb)
        pdf.set_xy(x + 2, base_y + 10)
        pdf.cell(card_w - 4, 9, val, ln=0)
    pdf.set_y(base_y + 30)

    # Severity breakdown bars
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_x(14)
    pdf.cell(0, 6, "SEVERITY BREAKDOWN", ln=1)
    for sev, clr_hex in [("Critical","#ef4444"),("High","#f97316"),
                          ("Medium","#eab308"),("Low","#3b82f6"),("Informational","#475569")]:
        n   = counts.get(sev, 0)
        pct = int((n / max(n_total, 1)) * 100)
        rgb = _hex_to_rgb(clr_hex)
        row_y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*rgb)
        pdf.set_x(14)
        pdf.cell(28, 5.5, sev, ln=0)
        pdf.set_text_color(148, 163, 184)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(12, 5.5, str(n), ln=0)
        bx, bw = 58, 118
        pdf.set_fill_color(10, 22, 40)
        pdf.rect(bx, row_y + 1, bw, 3.5, 'F')
        if pct > 0:
            pdf.set_fill_color(*rgb)
            pdf.rect(bx, row_y + 1, bw * pct / 100, 3.5, 'F')
        pdf.set_text_color(71, 85, 105)
        pdf.set_xy(178, row_y)
        pdf.cell(18, 5.5, f"{pct}%", ln=1, align='R')

    # Section header
    pdf.ln(6)
    pdf.set_draw_color(30, 58, 95)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.ln(7)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(226, 232, 240)
    pdf.set_x(14)
    pdf.cell(0, 7, f"INDIVIDUAL FINDINGS  ({n_total} total)", ln=1)
    pdf.ln(2)

    # ── Finding rows ───────────────────────────────────────────────────────────
    for f in individual:
        fid       = f.get('id', 'unknown')
        weight    = f.get('weight', 0)
        title     = _sanitize_pdf_text(f.get('title', 'Unknown Finding'))
        sev       = weight_to_severity(weight)
        sev_rgb   = _hex_to_rgb(_SEV_HEX.get(sev, "#475569"))
        raw_narr  = (get_narrative(fid, detections_cfg) or "-") if detections_cfg else "-"
        narrative = _sanitize_pdf_text(raw_narr[:600] + ("..." if len(raw_narr) > 600 else ""))
        mitre     = _sanitize_pdf_text(", ".join(f.get('mitre') or []))

        # Severity badge pill
        row_y = pdf.get_y()
        bw_badge = pdf.get_string_width(sev) + 8
        pdf.set_fill_color(*sev_rgb)
        pdf.rect(14, row_y, bw_badge, 7, 'F')
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(14, row_y)
        pdf.cell(bw_badge, 7, sev, ln=0, align='C')

        # Title
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(226, 232, 240)
        pdf.set_xy(14 + bw_badge + 4, row_y)
        pdf.cell(0, 7, (title[:88] + "...") if len(title) > 88 else title, ln=1)

        # Meta line
        meta = f"Rule ID: {fid}   |   Score: {weight}"
        if mitre:
            meta += f"   |   MITRE: {mitre[:60]}"
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.set_x(14)
        pdf.cell(0, 4.5, meta, ln=1)

        # Narrative
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.set_x(14)
        pdf.multi_cell(182, 4.2, narrative, ln=1)

        # Thin rule separator
        pdf.set_draw_color(30, 58, 95)
        pdf.set_line_width(0.2)
        pdf.line(14, pdf.get_y() + 1.5, 196, pdf.get_y() + 1.5)
        pdf.ln(5)

    return bytes(pdf.output()), None


# ==============================================================================
# 5. SCREEN: Login
# ==============================================================================

def screen_login():
    topbar("Login")

    # Three-column centering
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        # Brand block
        st.markdown("""
        <div style="text-align:center;margin:56px 0 32px;animation:fadein .4s ease;">
          <svg width="56" height="56" viewBox="0 0 28 28" fill="none"
               style="margin:0 auto 16px;display:block;">
            <path d="M14 2L26 8.5V19.5L14 26L2 19.5V8.5L14 2Z"
                  fill="#3b82f6" fill-opacity=".15"
                  stroke="#3b82f6" stroke-width="1.5"/>
            <path d="M14 7L21 10.75V17.25L14 21L7 17.25V10.75L14 7Z"
                  fill="#3b82f6" fill-opacity=".35"/>
            <circle cx="14" cy="14" r="3.5" fill="#60a5fa"/>
          </svg>
          <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
                      color:#e2e8f0;letter-spacing:1px;">PROCSENTINEL</div>
          <div style="font-size:12px;color:#475569;margin-top:5px;letter-spacing:.5px;">
            Memory Forensics Platform
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Login card
        st.markdown("""
        <div style="background:#141e2e;border:1px solid #1e2d45;border-radius:14px;
                    padding:32px 36px 28px;animation:fadein .5s ease .1s both;">
          <p style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:6px;font-family:'Inter',sans-serif;">
            Secure Access
          </p>
          <h2 style="font-family:'Syne',sans-serif;font-size:20px;font-weight:700;
                     color:#e2e8f0;margin:0 0 24px;">Sign in to continue</h2>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.text_input("Username / Email", placeholder="analyst@soc.local", key="login_user")
            st.text_input("Password / Token", placeholder="Enter your password", type="password", key="login_pass")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            col_chk, col_link = st.columns([1, 1])
            with col_chk:
                st.checkbox("Keep me signed in")
            with col_link:
                st.markdown(
                    '<div style="text-align:right;padding-top:4px;">'
                    '<a href="#" style="color:#3b82f6;font-size:12px;text-decoration:none;'
                    'font-family:\'Inter\',sans-serif;">Forgot password?</a></div>',
                    unsafe_allow_html=True
                )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Sign In  →", type="primary", use_container_width=True
            )

        st.markdown("""
        <div style="text-align:center;margin-top:20px;">
          <span style="font-size:11px;color:#475569;font-family:'Inter',sans-serif;">
            Need access? &nbsp;
            <a href="#" style="color:#3b82f6;text-decoration:none;">Contact your administrator</a>
          </span>
        </div>
        """, unsafe_allow_html=True)

    if submitted:
        u = st.session_state.get("login_user", "").strip()
        p = st.session_state.get("login_pass", "").strip()
        if "login_attempts" not in st.session_state:
            st.session_state.login_attempts = 0
        if st.session_state.login_attempts >= 5:
            st.error("Too many failed attempts. Restart the application to try again.")
        elif not u or not p:
            st.error("Please enter both your username and password.")
        else:
            import os as _os
            expected_user = _os.environ.get("PROCSENTINEL_USER", "admin")
            expected_pass = _os.environ.get("PROCSENTINEL_PASS", "procsentinel")
            if u == expected_user and p == expected_pass:
                st.session_state.logged_in = True
                st.session_state.login_attempts = 0
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                remaining = max(0, 5 - st.session_state.login_attempts)
                st.error(f"Invalid credentials. {remaining} attempt(s) remaining.")


# ==============================================================================
# 6. SCREEN: New Analysis
# ==============================================================================

def screen_new_analysis(case_files):
    topbar("New Analysis")

    # Show one-time warning if the previous analysis was cancelled
    if st.session_state.get('cancelled_case'):
        st.warning(
            f"⚠ Analysis for case **{st.session_state.cancelled_case}** was cancelled.  "
            "The runner process has been terminated."
        )
        st.session_state.cancelled_case = None

    page_header(
        "Analysis Setup",
        "New Memory Analysis",
        "Configure your analysis parameters below, then start the engine."
    )
    divider()

    _, body, _ = st.columns([1, 6, 1])
    with body:

        # File & case
        st.markdown("""
        <div style="background:#141e2e;border:1px solid #1e2d45;border-radius:12px;
                    padding:28px 32px;margin-bottom:16px;">
          <p style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:4px;font-family:'Inter',sans-serif;">
            Step 1 — Target
          </p>
          <p style="font-size:18px;font-weight:700;color:#e2e8f0;margin:0 0 20px;
                    font-family:'Syne',sans-serif;">Select Memory Image</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("new_analysis_form"):
            # Row 1: file + case name
            c1, c2 = st.columns(2)
            with c1:
                mem_file = st.selectbox(
                    "Memory Image File",
                    options=["— Select a file —"] + case_files,
                    help="Place your dump (.raw .mem .vmem .lime .aff4) in the memory/ folder."
                )
            with c2:
                default_case = (
                    mem_file.split('.')[0]
                    if mem_file and mem_file != "— Select a file —"
                    else "case_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                case_name = st.text_input(
                    "Case Name",
                    value=default_case,
                    help="Used as the output folder name inside out/"
                )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # Row 2: API key
            api_key = st.text_input(
                "AbuseIPDB API Key  (optional)",
                type="password",
                value=st.session_state.get('ip_enrichment_api_key', ''),
                help="Enriches suspicious IPs found in the memory dump with reputation data."
            )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # Row 3: options
            c3, c4, c5 = st.columns(3)
            with c3: st.checkbox("Save Raw Outputs")
            with c4: st.checkbox("Verbose Logging")
            with c5:
                st.markdown(
                    '<p style="font-size:11px;color:#475569;margin-top:6px;">'
                    'Supported: .raw .vmem .mem .lime .aff4</p>',
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Submit
            b1, b2 = st.columns([2, 5])
            with b1:
                submitted = st.form_submit_button(
                    "▶  Start Analysis", type="primary", use_container_width=True
                )

            if submitted:
                if mem_file == "— Select a file —":
                    st.error("Please select a memory image file.")
                elif not case_name:
                    st.error("Please enter a case name.")
                elif not re.match(r'^[a-zA-Z0-9_-]+$', case_name):
                    st.error("Case name may only contain letters, numbers, hyphens and underscores.")
                else:
                    st.session_state.current_case          = case_name
                    st.session_state.current_file          = mem_file
                    st.session_state.ip_enrichment_api_key = api_key
                    st.session_state.analysis_started      = True
                    st.session_state.analysis_successful   = False
                    st.rerun()


# ==============================================================================
# 7. SCREEN: Progress
# ==============================================================================

def screen_progress():
    topbar("Progress")

    case = st.session_state.current_case or ""
    file = st.session_state.current_file or ""

    # ── Handle cancel request from a previous render ────────────────────────
    # When the user clicks "Cancel", st.session_state.cancel_requested is set
    # True and a rerun fires.  On that rerun we land here, read the PID file,
    # terminate the process, then redirect back to New Analysis.
    if st.session_state.get('cancel_requested'):
        st.session_state.cancel_requested = False
        pid_f = _pid_file(case)
        if pid_f.exists():
            try:
                pid = int(pid_f.read_text().strip())
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                pid_f.unlink()
            except Exception:
                pass
        st.session_state.analysis_started    = False
        st.session_state.analysis_successful = False
        st.session_state.cancelled_case      = case   # carry the name for the warning
        st.rerun()
        return

    page_header(
        "Analysis In Progress",
        "Running Engine",
        f"Case: {html_escape(case)}   \u00b7   File: {html_escape(file)}"
    )
    divider()

    # ── Top bar: progress + ETA + cancel ────────────────────────────────────
    st.markdown("<div style='padding:0 40px;'>", unsafe_allow_html=True)

    top_left, top_right = st.columns([8, 2])
    with top_left:
        progress_bar = st.progress(0, text="Starting…")
        status_text  = st.empty()
    with top_right:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        eta_slot   = st.empty()
        cancel_btn = st.button(
            "■  Cancel Analysis",
            key="cancel_btn",
            use_container_width=True,
        )
        if cancel_btn:
            st.session_state.cancel_requested = True
            st.rerun()
            return

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Two-column body ──────────────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="large")

    # -- Checklist --
    with col_left:
        section_label("Task Checklist")
        check_labels = [
            "Initialization",
            "Plugin Execution",
            "Detection Engine",
            "Report Generation",
            "Complete",
        ]
        check_slots = []
        for i, lbl in enumerate(check_labels):
            border_bottom = "border-bottom:1px solid #1e2d45;" if i < len(check_labels) - 1 else ""
            slot = st.empty()
            slot.markdown(
                f'<div style="display:flex;align-items:center;gap:14px;padding:12px 0;{border_bottom}">'
                f'<div style="width:22px;height:22px;border-radius:50%;border:2px solid #1e2d45;'
                f'background:#080c14;flex-shrink:0;"></div>'
                f'<span style="font-size:13px;color:#475569;font-family:\'Inter\',sans-serif;">{lbl}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            check_slots.append((slot, lbl, i < len(check_labels) - 1))

    # -- Console --
    with col_right:
        section_label("Console Output")
        console_slot = st.empty()
        console_slot.markdown(
            '<div style="background:#080c14;border:1px solid #1e2d45;border-radius:12px;'
            'padding:16px 18px;height:264px;overflow-y:auto;'
            'font-family:\'JetBrains Mono\',monospace;font-size:11px;color:#475569;">'
            'Waiting for engine…'
            '</div>',
            unsafe_allow_html=True
        )

    # -- Plugin execution log (full width below) --
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    section_label("Plugin Execution Log")
    plugin_log_slot = st.empty()
    plugin_log_slot.markdown(
        '<div style="background:#080c14;border:1px solid #1e2d45;border-radius:12px;'
        'padding:14px 18px;min-height:60px;">'
        '<span style="font-size:11px;color:#475569;font-family:\'JetBrains Mono\',monospace;">'
        'Awaiting first plugin…</span></div>',
        unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Inner helpers ────────────────────────────────────────────────────────
    def tick(idx):
        slot, lbl, has_border = check_slots[idx]
        border_bottom = "border-bottom:1px solid #1e2d45;" if has_border else ""
        slot.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;padding:12px 0;{border_bottom}">'
            f'<div style="width:22px;height:22px;border-radius:50%;background:#3b82f6;'
            f'flex-shrink:0;display:flex;align-items:center;justify-content:center;">'
            f'<svg width="11" height="9" viewBox="0 0 11 9" fill="none">'
            f'<path d="M1 4.5L4 7.5L10 1.5" stroke="white" stroke-width="2"'
            f' stroke-linecap="round" stroke-linejoin="round"/></svg>'
            f'</div>'
            f'<span style="font-size:13px;color:#e2e8f0;font-weight:500;'
            f'font-family:\'Inter\',sans-serif;">{lbl}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    def push_console(logs):
        lines = ""
        for line in logs[-28:]:
            if   "[+]" in line:                                     clr = "#10b981"
            elif "[i]" in line:                                     clr = "#60a5fa"
            elif "[!]" in line:                                     clr = "#eab308"
            elif "error" in line.lower() or "fail" in line.lower(): clr = "#ef4444"
            else:                                                    clr = "#475569"
            lines += (
                f'<div style="color:{clr};line-height:1.9;'
                f'word-break:break-all;">{html_escape(line.strip())}</div>'
            )
        console_slot.markdown(
            '<div style="background:#080c14;border:1px solid #1e2d45;border-radius:12px;'
            f'padding:16px 18px;height:264px;overflow-y:auto;'
            'font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            + lines + '</div>',
            unsafe_allow_html=True
        )

    def push_plugin_log(plugin_rows):
        """plugin_rows is a list of (plugin_name, friendly_desc, success:bool)."""
        if not plugin_rows:
            return
        rows_html = ""
        for i, (pname, pdesc, ok) in enumerate(plugin_rows):
            dot_clr = "#10b981" if ok else "#ef4444"
            bg      = "#0d1b2e" if i % 2 == 0 else "#080c14"
            rows_html += (
                f'<div style="display:flex;align-items:center;gap:12px;padding:7px 14px;'
                f'background:{bg};border-radius:6px;">'
                f'<div style="width:8px;height:8px;border-radius:50%;background:{dot_clr};flex-shrink:0;"></div>'
                f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
                f'color:#60a5fa;min-width:240px;flex-shrink:0;">{html_escape(pname)}</span>'
                f'<span style="font-size:11px;color:#475569;font-family:\'Inter\',sans-serif;">{html_escape(pdesc)}</span>'
                f'</div>'
            )
        plugin_log_slot.markdown(
            f'<div style="background:#080c14;border:1px solid #1e2d45;border-radius:12px;'
            f'padding:8px;max-height:220px;overflow-y:auto;">{rows_html}</div>',
            unsafe_allow_html=True
        )

    def update_eta(step_times, steps_done, total):
        if len(step_times) < 2:
            eta_slot.markdown(
                '<p style="font-size:11px;color:#475569;text-align:center;'
                'font-family:\'Inter\',sans-serif;margin-top:4px;">ETA: calculating…</p>',
                unsafe_allow_html=True
            )
            return
        avg   = sum(step_times) / len(step_times)
        remaining = max(total - steps_done, 0)
        secs  = int(avg * remaining)
        mins  = secs // 60
        secs  = secs % 60
        label = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        eta_slot.markdown(
            f'<p style="font-size:11px;color:#94a3b8;text-align:center;'
            f'font-family:\'Inter\',sans-serif;margin-top:4px;">ETA ≈ {label}</p>',
            unsafe_allow_html=True
        )

    # ── Validate required files ──────────────────────────────────────────────
    for p, lbl in [(CLI_SCRIPT_PATH, "runner.py"),
                   (DETECTIONS_FILE_PATH, "detections.yaml"),
                   (BASELINE_FILE_PATH, "baseline.yaml")]:
        if not p.exists():
            status_text.error(f"FATAL ERROR: {lbl} not found at {p}")
            st.session_state.analysis_started = False
            return

    cmd = [
        sys.executable, '-u', str(CLI_SCRIPT_PATH),
        "--image",      str(MEMORY_FOLDER / st.session_state.current_file),
        "--case",       st.session_state.current_case,
        "--detections", str(DETECTIONS_FILE_PATH),
        "--baseline",   str(BASELINE_FILE_PATH),
        "--outdir",     str(OUTPUT_FOLDER),
        "--api-key",    st.session_state.ip_enrichment_api_key,
    ]

    logs        = []
    steps       = 0
    TOTAL       = 20
    step_times  = []           # seconds each plugin step took
    plugin_rows = []           # (plugin_name, friendly_desc, success)
    last_plugin_name  = None
    last_plugin_start = None

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', bufsize=1
    )

    # Write PID so cancel button can terminate it after a rerun
    try:
        _pid_file(case).write_text(str(process.pid))
    except Exception:
        pass

    status_text.info("Preparing analysis environment…")

    while True:
        # Check cancel sentinel (written by button click on previous rerun)
        if _cancel_file(case).exists():
            process.kill()
            try: _cancel_file(case).unlink()
            except: pass
            try: _pid_file(case).unlink()
            except: pass
            status_text.warning("Analysis cancelled by user.")
            st.session_state.analysis_started = False
            return

        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if not line:
            continue

        logs.append(line)
        push_console(logs)

        if "[+] Running plugin:" in line:
            now = time.time()

            # Close out the previous plugin's timing
            if last_plugin_start is not None:
                elapsed = now - last_plugin_start
                step_times.append(elapsed)
                if last_plugin_name:
                    plugin_rows.append((
                        last_plugin_name,
                        get_friendly_scan_name(last_plugin_name).rstrip("…").rstrip("."),
                        True,
                    ))
                    push_plugin_log(plugin_rows)

            # Start new plugin
            try:
                pname = line.split(":", 1)[1].strip().split()[0]
            except IndexError:
                pname = "unknown"
            last_plugin_name  = pname
            last_plugin_start = now

            steps += 1
            status_text.info(get_friendly_scan_name(pname))
            pf = min(1.0, steps / TOTAL)
            progress_bar.progress(pf, text=f"{int(pf * 100)}%  Complete")
            update_eta(step_times, steps, TOTAL)

            if steps >= 1: tick(0)
            if steps >= 3: tick(1)

        if "[i] Running detection engine:" in line:
            status_text.info(line.strip().replace("[i] ", ""))
            tick(2)

        if "[i] Starting correlation analysis:" in line:
            status_text.info(line.strip().replace("[i] ", ""))

        if "report" in line.lower() or "findings written" in line.lower():
            tick(3)

    # Flush last plugin into the log
    if last_plugin_name and (not plugin_rows or plugin_rows[-1][0] != last_plugin_name):
        plugin_rows.append((
            last_plugin_name,
            get_friendly_scan_name(last_plugin_name).rstrip("…").rstrip("."),
            True,
        ))
        push_plugin_log(plugin_rows)

    # Cleanup PID file
    try: _pid_file(case).unlink()
    except: pass

    try:
        process.wait(timeout=900)
    except subprocess.TimeoutExpired:
        process.kill()
        status_text.error("Analysis timed out after 15 minutes.")
        st.session_state.analysis_started = False
        return

    if process.returncode == 0:
        progress_bar.progress(1.0, text="100%  Complete")
        tick(4)
        eta_slot.markdown(
            '<p style="font-size:11px;color:#10b981;text-align:center;'
            'font-family:\'Inter\',sans-serif;margin-top:4px;">Done ✓</p>',
            unsafe_allow_html=True
        )
        status_text.success("Analysis complete — loading results…")
        st.session_state.analysis_successful = True
        st.rerun()
    else:
        status_text.error(f"Analysis failed (exit code {process.returncode}).")
        st.session_state.analysis_started = False
        with st.expander("Show Error Log"):
            st.code(''.join(logs), language='text')


# ==============================================================================
# 8. SCREEN: Results
# ==============================================================================

def _sev_color(sev):
    return {"Critical":"#ef4444","High":"#f97316","Medium":"#eab308","Low":"#3b82f6","Informational":"#475569"}.get(sev,"#475569")

def screen_results():
    topbar("Results")

    findings       = load_findings(st.session_state.current_case)
    detections_cfg = load_detections_config()
    baseline_cfg   = load_baseline_config()
    counts, overall, total_score = categorize_findings(findings, detections_cfg)
    sc = _sev_color(overall)
    case_name = st.session_state.current_case or "Unknown"

    st.markdown(
        f'''<div style="padding:28px 40px 0;">
          <p style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:3px;
                    text-transform:uppercase;margin:0 0 6px;">Memory Forensics Report</p>
          <h1 style="font-size:26px;font-weight:700;color:#e2e8f0;margin:0 0 4px;">
            Case: ''' + html_escape(case_name) + '''
          </h1>
          <p style="font-size:13px;color:#475569;margin:0 0 20px;">
            ''' + str(len(findings)) + ''' findings detected &nbsp;&bull;&nbsp;
            Threat level: <span style="color:''' + sc + ''';font-weight:600;">''' + overall + '''</span>
          </p>
        </div>
        <div style="margin:0 40px;border-bottom:1px solid #1e3a5f;"></div>''',
        unsafe_allow_html=True
    )

    _, col_html, col_pdf, col_btn = st.columns([7, 1, 1, 1])

    # ── HTML Report button ────────────────────────────────────────────────────
    with col_html:
        html_report_path = (
            OUTPUT_FOLDER / case_name / "artifacts" / "report.html"
        )
        # Fallback: some older runner versions write to case root
        if not html_report_path.exists():
            html_report_path = OUTPUT_FOLDER / case_name / "report.html"

        if html_report_path.exists():
            with open(html_report_path, "rb") as _fh:
                _html_b64 = base64.b64encode(_fh.read()).decode()
            _html_fname = f"ProcSentinel_{case_name}_report.html"
            st.markdown(
                f'<a href="data:text/html;base64,{_html_b64}" '
                f'download="{_html_fname}" target="_blank" '
                f'style="display:flex;align-items:center;justify-content:center;'
                f'gap:6px;background:#1a2540;color:#60a5fa;border:1px solid #2d4266;'
                f'border-radius:8px;padding:8px 14px;font-size:13px;font-weight:500;'
                f'font-family:Inter,sans-serif;text-decoration:none;'
                f'white-space:nowrap;margin-top:4px;">'
                f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
                f'stroke="currentColor" stroke-width="2" stroke-linecap="round">'
                f'<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
                f'<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>'
                f'</svg>Open HTML Report</a>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<p style="font-size:11px;color:#475569;margin-top:8px;'
                'font-family:Inter,sans-serif;">No report.html found</p>',
                unsafe_allow_html=True
            )

    # ── PDF download button ───────────────────────────────────────────────────
    with col_pdf:
        if st.button("⬇ Download PDF", use_container_width=True):
            with st.spinner("Generating PDF…"):
                pdf_bytes, pdf_err = generate_pdf_report(
                    case_name, findings, counts, overall, total_score, detections_cfg
                )
            if pdf_err:
                st.error(pdf_err)
            elif pdf_bytes:
                fname = f"ProcSentinel_{case_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                b64_pdf = base64.b64encode(pdf_bytes).decode()
                st.markdown(
                    f'<a href="data:application/pdf;base64,{b64_pdf}" download="{fname}"'
                    f' style="display:block;text-align:center;background:#10b981;color:#fff;'
                    f'border:1px solid #10b981;border-radius:8px;padding:8px 14px;'
                    f'font-size:13px;font-weight:600;font-family:Inter,sans-serif;'
                    f'text-decoration:none;margin-top:6px;">&#10003; Click to Save PDF</a>',
                    unsafe_allow_html=True
                )

    # ── New Analysis button ───────────────────────────────────────────────────
    with col_btn:
        if st.button("+ New Analysis", use_container_width=True):
            for k in ["current_case","current_file"]:
                st.session_state[k] = None
            for k in ["analysis_started","analysis_successful"]:
                st.session_state[k] = False
            st.rerun()

    if not findings:
        st.markdown("<div style='padding:40px;'>", unsafe_allow_html=True)
        st.warning(f"No findings detected for case: **{case_name}**.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("<div style='padding:24px 40px 0;'>", unsafe_allow_html=True)

    # ── KPI cards ──────────────────────────────────────────────────────────────
    kpi_data = [
        ("Total Findings",  str(sum(counts.values())),     "#e2e8f0"),
        ("Critical",        str(counts.get("Critical",0)), "#ef4444"),
        ("High",            str(counts.get("High",0)),     "#f97316"),
        ("Medium",          str(counts.get("Medium",0)),   "#eab308"),
        ("Low",             str(counts.get("Low",0)),      "#3b82f6"),
        ("Risk Score",      str(total_score),              sc),
    ]
    cols = st.columns(6, gap="small")
    for i, (lbl, val, clr) in enumerate(kpi_data):
        with cols[i]:
            st.markdown(
                f'<div style="background:#0d1b2e;border:1px solid #1e3a5f;border-radius:12px;'
                f'padding:18px 16px;border-top:3px solid {clr};">'
                f'<p style="font-size:9px;font-weight:600;color:#475569;letter-spacing:2px;'
                f'text-transform:uppercase;margin:0 0 8px;">{lbl}</p>'
                f'<p style="font-size:28px;font-weight:800;line-height:1;margin:0;'
                f'color:{clr};font-family:\'Inter\',sans-serif;">{val}</p>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Chart + severity bars ────────────────────────────────────────────────────
    col_chart, col_bars = st.columns([3, 2], gap="large")
    with col_chart:
        sev_order = ["Critical","High","Medium","Low","Informational"]
        sev_clrs  = ["#ef4444","#f97316","#eab308","#3b82f6","#475569"]
        fig = go.Figure(data=[go.Bar(
            x=sev_order, y=[counts.get(s,0) for s in sev_order],
            marker_color=sev_clrs, marker_line_width=0,
            text=[counts.get(s,0) for s in sev_order],
            textposition="outside",
            textfont=dict(color="#64748b", family="Inter", size=11),
        )])
        fig.update_layout(
            plot_bgcolor="#0d1b2e", paper_bgcolor="#0d1b2e",
            font=dict(color="#64748b", family="Inter"),
            xaxis=dict(categoryorder="array", categoryarray=sev_order,
                       gridcolor="#1e3a5f", tickfont=dict(size=12), showline=False),
            yaxis=dict(gridcolor="#1e3a5f", showline=False),
            margin=dict(l=0, r=0, t=16, b=0), height=220, bargap=0.45,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_bars:
        total_f = max(sum(counts.values()), 1)
        bars_html = '<div style="background:#0d1b2e;border:1px solid #1e3a5f;border-radius:12px;padding:22px;height:220px;display:flex;flex-direction:column;justify-content:center;">'
        bars_html += '<p style="font-size:9px;font-weight:600;color:#475569;letter-spacing:2px;text-transform:uppercase;margin:0 0 18px;">Breakdown</p>'
        for sev, clr in zip(["Critical","High","Medium","Low"],["#ef4444","#f97316","#eab308","#3b82f6"]):
            n   = counts.get(sev, 0)
            pct = int((n / total_f) * 100)
            bars_html += (
                f'<div style="margin-bottom:10px;">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                f'<span style="font-size:11px;font-weight:600;color:{clr};">{sev}</span>'
                f'<span style="font-size:11px;color:#475569;">{n}</span></div>'
                f'<div style="background:#0a1628;border-radius:4px;height:5px;">'
                f'<div style="background:{clr};height:100%;width:{pct}%;border-radius:4px;opacity:.75;"></div>'
                f'</div></div>'
            )
        bars_html += '</div>'
        st.markdown(bars_html, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='border-bottom:1px solid #1e3a5f;margin-bottom:0;'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["  Forensic Findings  ", "  Output Artifacts  ", "  Configuration  "])
    with tab1:
        render_findings_tab(findings, detections_cfg)
    with tab2:
        render_artifacts_tab(case_name)
    with tab3:
        render_config_tab(detections_cfg, baseline_cfg)

    st.markdown("</div>", unsafe_allow_html=True)





# ==============================================================================
# 9. Findings tab
# ==============================================================================

def render_findings_tab(findings, detections_cfg):
    st.markdown("<div style='padding:28px 0 0;'>", unsafe_allow_html=True)

    correlated = [f for f in findings if str(f.get('id','')).startswith('correlation_')]
    if correlated:
        st.markdown("""
        <p style="font-size:10px;font-weight:600;color:#475569;letter-spacing:2px;
                  text-transform:uppercase;margin:0 0 12px;">Correlated Attack Chain</p>
        """, unsafe_allow_html=True)
        for finding in correlated:
            with st.container(border=True):
                render_correlated(finding, detections_cfg)
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    individual = sorted(
        [f for f in findings if not str(f.get('id','')).startswith('correlation_')],
        key=lambda x: x.get('weight',0), reverse=True
    )

    st.markdown("""
    <p style="font-size:10px;font-weight:600;color:#475569;letter-spacing:2px;
              text-transform:uppercase;margin:0 0 16px;">All Detections</p>
    """, unsafe_allow_html=True)

    SEV_CLR = {"Critical":"#ef4444","High":"#f97316","Medium":"#eab308","Low":"#3b82f6","Informational":"#475569"}
    SEV_BG  = {"Critical":"rgba(239,68,68,.08)","High":"rgba(249,115,22,.08)",
               "Medium":"rgba(234,179,8,.07)","Low":"rgba(59,130,246,.07)","Informational":"rgba(71,85,105,.05)"}

    for f in individual:
        fid    = f.get('id','unknown')
        weight = f.get('weight', 0)
        sev    = weight_to_severity(weight)
        clr    = SEV_CLR.get(sev, "#475569")
        label  = f"{sev}  |  {f.get('title','Unknown')}  |  Score: {weight}"
        with st.expander(label):
            # Severity badge + metadata row
            mitre_tags = " ".join(
                f'<span style="background:#0d1b2e;border:1px solid #1e3a5f;color:#60a5fa;'
                f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;'
                f'font-family:JetBrains Mono,monospace;">{t}</span>'
                for t in (f.get('mitre') or [])
            )
            ev_count = len(f.get('evidence', []) or [])
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;'
                f'padding-bottom:14px;border-bottom:1px solid #1e3a5f;">'
                f'<span style="background:{SEV_BG.get(sev,chr(39))};border:1px solid {clr};color:{clr};'
                f'font-size:11px;font-weight:700;padding:3px 12px;border-radius:6px;'
                f'font-family:Inter,sans-serif;letter-spacing:.5px;">{sev.upper()}</span>'
                f'<span style="font-size:11px;color:#475569;">Score: <b style="color:#94a3b8;">{weight}</b></span>'
                f'<span style="font-size:11px;color:#475569;">Findings: <b style="color:#94a3b8;">{ev_count}</b></span>'
                f'<span style="font-size:11px;color:#475569;">Rule ID: <code style="color:#64748b;background:#060e1d;'
                f'padding:1px 6px;border-radius:4px;">{fid}</code></span>'
                f'<div style="margin-left:auto;display:flex;gap:6px;">{mitre_tags}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            # Narrative
            narrative = get_narrative(fid, detections_cfg)
            st.markdown(
                f'<div style="background:#060e1d;border-left:3px solid {clr};border-radius:0 8px 8px 0;'
                f'padding:12px 16px;margin-bottom:20px;">'
                f'<p style="font-size:12px;color:#94a3b8;line-height:1.8;margin:0;">' + html_escape(narrative) + '</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            ev = f.get('evidence', [])
            if fid in ["kernel_callbacks_suspicious","modules_hidden_vs_modscan",
                       "registry_orphan_hives","dumpit_present"]:
                render_evidence_list(ev, fid)
            elif not str(fid).startswith('correlation_'):
                st.markdown("<p style='font-size:10px;font-weight:600;color:#475569;letter-spacing:2px;text-transform:uppercase;margin:0 0 10px;'>Evidence</p>", unsafe_allow_html=True)
                render_evidence_table(ev, fid)

    st.markdown("</div>", unsafe_allow_html=True)


def render_correlated(finding, detections_cfg):
    st_html(
        f"<h4 style='color:#60a5fa;font-family:\"Inter\",sans-serif;font-weight:600;margin:0;'>"
        f"{html_escape(finding.get('title','Correlated Threat'))}</h4>",
        height=42
    )
    st.markdown(
        f"<p style='font-size:13px;color:#94a3b8;font-family:\"Inter\",sans-serif;line-height:1.7;'>"
        f"{html_escape(get_narrative(finding.get('id'), detections_cfg))}</p>",
        unsafe_allow_html=True
    )
    for item in finding.get('evidence', []):
        pid = item.get('correlated_pid')
        st_html(
            f"<h5 style='color:#60a5fa;font-family:\"Inter\",sans-serif;font-weight:600;'>"
            f"Involved PID: {html_escape(str(pid))}</h5>",
            height=32
        )
        details = sorted(item.get('correlated_findings',[]), key=lambda f: (
            0 if any(k in f.get('finding_id','') for k in
                     ['exec_from_tmp','psxview_hidden','malfind_injection','cmdline_args','parent_child','registry_run_key','userassist'])
            else 1 if any(k in f.get('finding_id','') for k in
                          ['network','connection','port','netstat','netscan','enrichment'])
            else 2
        ))

        path_html = "<div class='attack-path-container'>"
        for i, fd in enumerate(details):
            fid   = fd.get('finding_id')
            ev    = fd.get('evidence',[{}])[0]
            ttl   = get_user_friendly_correlated_title(fid)
            pname = ev.get('name') or ev.get('process') or ev.get('owner') or ev.get('ImageFileName')

            if fid == 'psxview_hidden':
                desc = f"Process <code>{html_escape(str(pname))}</code> hid its presence."
            elif fid in ('suspicious_connection','suspicious_port_activity','suspicious_network_enrichment'):
                rip = ev.get('ForeignAddr') or ev.get('ip')
                rpt = ev.get('ForeignPort')
                if rip and rip not in ['None','0.0.0.0']:
                    desc = f"Communicated with: <code>{html_escape(str(rip))}:{html_escape(str(rpt))}</code>."
                else:
                    desc = f"Opened suspicious port: <code>{html_escape(str(ev.get('LocalPort')))}</code>."
            elif fid == 'malfind_injection':
                desc = "Injected malicious code into process memory."
            elif fid == 'ldr_unlinked_module':
                desc = "Loaded a <b>hidden or unlinked module</b>."
            elif fid == 'suspicious_cmdline_args':
                desc = f"Suspicious command: <code>{html_escape(str(ev.get('command_line')))}</code>."
            elif fid == 'registry_run_key_persistence':
                desc = "Configured for <b>auto-start</b> via Registry Run Key."
            elif fid == 'exec_from_tmp':
                desc = f"Executed from temp dir: <code>{html_escape(str(ev.get('path')))}</code>."
            elif fid == 'unusual_parent_child':
                desc = (f"`{html_escape(str(ev.get('name','?')))}` spawned by unexpected "
                        f"parent `{html_escape(str(ev.get('parent_name','?')))}`.")
            elif fid == 'bash_history_suspicious':
                desc = f"{html_escape(str(ev.get('User','A user')))} ran a <b>suspicious shell command</b>."
            else:
                desc = html_escape(get_narrative(fid, detections_cfg))

            path_html += f"<div class='attack-step'><b>{html_escape(ttl)}</b><hr><p>{desc}</p></div>"
            if i < len(details)-1:
                path_html += "<div class='attack-arrow'>→</div>"
        path_html += "</div>"
        st.markdown(path_html, unsafe_allow_html=True)
        st.markdown("---")


def render_evidence_list(evidence_list, fid):
    if not evidence_list:
        st.info("No detailed evidence provided.")
        return
    st.markdown("<ul style='list-style-type:none;padding-left:0;'>", unsafe_allow_html=True)
    for item in evidence_list[:10]:
        if fid == 'kernel_callbacks_suspicious':
            detail = f"Callback: `{html_escape(item.get('Details','N/A'))}`, Owner: `{html_escape(item.get('OwnerModule','N/A'))}`"
        elif fid == 'modules_hidden_vs_modscan':
            detail = f"Module: `{html_escape(item.get('Module','N/A'))}`, Base: `{html_escape(item.get('Base','N/A'))}`"
        elif fid == 'registry_orphan_hives':
            detail = f"Orphaned Hive: `{html_escape(item.get('HivePath','N/A'))}`"
        elif fid == 'dumpit_present':
            detail = f"Tool Path: `{html_escape(item.get('Path','N/A'))}`"
        else:
            detail = str(item)
        st.markdown(
            f"<li style='font-size:13px;color:#94a3b8;margin-bottom:6px;"
            f"font-family:\"Inter\",sans-serif;'>{detail}</li>",
            unsafe_allow_html=True
        )
    if len(evidence_list) > 10:
        st.markdown(
            f"<li style='color:#475569;font-size:12px;'>...and {len(evidence_list)-10} more.</li>",
            unsafe_allow_html=True
        )
    st.markdown("</ul>", unsafe_allow_html=True)


def render_evidence_table(evidence_list, fid):
    if not evidence_list:
        st.info("No detailed evidence provided.")
        return

    processed = []
    if (fid == "suspicious_network_enrichment" and evidence_list
            and isinstance(evidence_list[0], dict)
            and evidence_list[0].get('id') == fid
            and isinstance(evidence_list[0].get('evidence'), list)):
        for item in evidence_list:
            processed.extend(item.get('evidence', [item]))
    else:
        processed = evidence_list

    if not processed:
        st.info("No detailed evidence artifacts found.")
        return

    df = pd.DataFrame(processed)
    df.replace(['', None, 'None'], np.nan, inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    if df.empty:
        st.info("No detailed evidence artifacts found.")
        return

    # ── Masquerade-specific column configs — path shown prominently ─────────
    MASQ_BOOL_COLS = {"missing_required_flag", "path_not_allowed", "user_writable_hint"}

    COL_CFG = {
        # Masquerade rules
        "masquerade_wrong_path":     {"columns":["pid","name","path","command_line","user_writable_hint"],
                                      "rename":{"pid":"PID","name":"Process Name","path":"Execution Path","command_line":"Command Line","user_writable_hint":"User-Writable Dir"}},
        "masquerade_typosquat":      {"columns":["pid","name","looks_like","distance","path"],
                                      "rename":{"pid":"PID","name":"Suspicious Name","looks_like":"Impersonating","distance":"Edit Distance","path":"Path"}},
        "masquerade_svchost_no_k":   {"columns":["pid","name","path","command_line","missing_required_flag","path_not_allowed"],
                                      "rename":{"pid":"PID","name":"Process","path":"Execution Path","command_line":"Command Line","missing_required_flag":"Missing -k?","path_not_allowed":"Wrong Path?"}},
        "masquerade_boot_chain":     {"columns":["child_pid","child_name","parent_pid","parent_name","expected_parents"],
                                      "rename":{"child_pid":"Child PID","child_name":"Child Process","parent_pid":"Parent PID","parent_name":"Actual Parent","expected_parents":"Expected Parent"}},
        "masquerade_explorer":       {"columns":["pid","name","path","command_line"],
                                      "rename":{"pid":"PID","name":"Process","path":"Execution Path","command_line":"Command Line"}},
        "masquerade_unicode_padding":{"columns":["pid","name_repr","reason"],
                                      "rename":{"pid":"PID","name_repr":"Raw Name","reason":"Reason"}},
        "unusual_parent_child":      {"columns":["child_name","child_pid","parent_name","parent_pid"],
                                      "rename":{"child_name":"Child Process","child_pid":"Child PID","parent_name":"Actual Parent","parent_pid":"Parent PID"}},
        "shell_spawned_by_office_or_browser": {"columns":["child_pid","child_name","parent_pid","parent_name","command_line"],
                                      "rename":{"child_pid":"Child PID","child_name":"Shell","parent_pid":"Parent PID","parent_name":"Launched By","command_line":"Command Line"}},
        "verinfo_mismatch":          {"columns":["pid","process","Path","Notes"],
                                      "rename":{"pid":"PID","process":"Process","Path":"File Path","Notes":"Issue"}},
        # Other rules
        "psxview_hidden":            {"columns":["pid","name","pslist","psscan"],             "rename":{"pid":"PID","name":"Process Name","pslist":"In pslist","psscan":"In psscan"}},
        "exec_from_tmp":             {"columns":["pid","name","path"],                        "rename":{"pid":"PID","name":"Process Name","path":"Execution Path"}},
        "malfind_injection":         {"columns":["process","pid","Start","Protection"],       "rename":{"process":"Process","pid":"PID","Start":"Start Address","Protection":"Memory Protection"}},
        "handles_lsass_access":      {"columns":["requestor_pid","requestor_name","target_name","GrantedAccess"], "rename":{"requestor_pid":"PID","requestor_name":"Process","target_name":"Target","GrantedAccess":"Access"}},
        "services_suspicious":       {"columns":["ServiceName","ServiceType","ImagePath","Start","Pid"], "rename":{"ServiceName":"Service Name","ServiceType":"Type","ImagePath":"Executable Path","Start":"Start Type","Pid":"PID"}},
        "suspicious_cmdline_args":   {"columns":["pid","name","command_line"],                "rename":{"pid":"PID","name":"Process","command_line":"Suspicious Command Line"}},
        "suspicious_connection":     {"columns":["owner","LocalAddr","LocalPort","ForeignAddr","ForeignPort"],"rename":{"owner":"Process","LocalAddr":"Local","LocalPort":"L.Port","ForeignAddr":"Remote","ForeignPort":"R.Port"}},
        "suspicious_network_enrichment":{"columns":["pid","owner","ip","country","isp","reputation","notes"],"rename":{"pid":"PID","owner":"Process","ip":"Remote IP","country":"Country","isp":"ISP","reputation":"Reputation","notes":"Reason"}},
        "filescan_suspicious_names": {"columns":["Path","Offset"],                           "rename":{"Path":"File Path","Offset":"Memory Offset"}},
        "registry_run_key_persistence":{"columns":["Key","Name","Decoded"],                  "rename":{"Key":"Registry Key","Name":"Entry","Decoded":"Command Executed"}},
        "exec_from_tmp":             {"columns":["pid","name","path"],                       "rename":{"pid":"PID","name":"Process Name","path":"Execution Path"}},
        "bash_history_suspicious":   {"columns":["User","Command"],                          "rename":{"User":"User","Command":"Command Executed"}},
        "userassist_suspicious":     {"columns":["Path","Count","LastUpdated"],              "rename":{"Path":"Program Path","Count":"Execution Count","LastUpdated":"Last Executed"}},
        "ldr_unlinked_module":       {"columns":["Details"],                                 "rename":{"Details":"Module Details"}},
    }

    cfg     = COL_CFG.get(fid)
    df_show = df
    if cfg:
        exist = [c for c in cfg["columns"] if c in df.columns]
        if exist:
            df_show = df[exist].rename(columns=cfg["rename"])
            if fid == 'psxview_hidden':
                if 'Visible in List' in df_show.columns:
                    df_show['Visible in List'] = df_show['Visible in List'].apply(
                        lambda x: 'Yes' if str(x).lower()=='true' else 'No (Hidden)')
                if 'Found by Scan' in df_show.columns:
                    df_show['Found by Scan'] = df_show['Found by Scan'].apply(
                        lambda x: 'Yes' if str(x).lower()=='true' else 'No')

    # Convert boolean/YES/NO columns to readable text
    for col in df_show.columns:
        if col in MASQ_BOOL_COLS or col in {"Missing -k?","Wrong Path?","User-Writable Dir","In pslist","In psscan"}:
            df_show[col] = df_show[col].apply(
                lambda v: "YES" if str(v).strip().lower() in ("true","yes","1") else
                          "NO"  if str(v).strip().lower() in ("false","no","0","none","") else str(v)
            )
    # Replace empty strings with N/A for readability
    df_show = df_show.replace({"": "N/A", None: "N/A", "(path unavailable)": "N/A - path not in memory"})
    st.dataframe(df_show, use_container_width=True, hide_index=True)


# ==============================================================================
# 10. Artifacts tab
# ==============================================================================

ARTIFACT_DESCS = {
    "report.html":                 {"title":"Full Analysis Report (HTML)",     "description":"Complete HTML report."},
    "findings.jsonl":              {"title":"Detected Findings (JSONL)",       "description":"Raw JSON Lines of all findings."},
    "console_output.log":          {"title":"CLI Console Output Log",          "description":"Full log of the analysis process."},
    "windows_info.txt":            {"title":"Windows System Info",             "description":"OS and kernel details."},
    "windows_pslist.csv":          {"title":"Windows Process List",            "description":"Active processes including PID, PPID."},
    "windows_psscan.csv":          {"title":"Windows PsScan",                  "description":"Deep scan for hidden processes."},
    "windows_psxview.csv":         {"title":"Windows PsXView",                 "description":"Hidden process mismatches."},
    "windows_pstree.txt":          {"title":"Windows Process Tree",            "description":"Hierarchical process tree."},
    "windows_cmdline.csv":         {"title":"Windows Command Line Args",       "description":"Full command-line arguments."},
    "windows_netstat.csv":         {"title":"Windows Netstat",                 "description":"Active network connections."},
    "windows_netscan.csv":         {"title":"Windows Netscan",                 "description":"Detailed network scan."},
    "windows_malfind.txt":         {"title":"Windows Malfind",                 "description":"Injected code from process memory."},
    "windows_hollowprocesses.txt": {"title":"Windows Hollow Processes",        "description":"Process hollowing detection."},
    "windows_ldrmodules.txt":      {"title":"Windows Loaded Modules",          "description":"Loaded DLLs and unlinked modules."},
    "windows_svcscan.csv":         {"title":"Windows Service Scan",            "description":"Windows services and status."},
    "windows_sessions.csv":        {"title":"Windows Sessions",                "description":"Active user logon sessions."},
    "windows_callbacks.txt":       {"title":"Windows Kernel Callbacks",        "description":"Kernel callback analysis."},
    "linux_pslist.csv":            {"title":"Linux Process List",              "description":"Active Linux processes."},
    "linux_psscan.csv":            {"title":"Linux PsScan",                    "description":"Deep scan for hidden Linux processes."},
    "linux_bash.txt":              {"title":"Linux Bash History",              "description":"Shell command history."},
    "mac_pslist.csv":              {"title":"macOS Process List",              "description":"Active macOS processes."},
    "mac_bash.txt":                {"title":"macOS Bash History",              "description":"Shell command history on macOS."},
}


def render_artifacts_tab(current_case):
    section_label("Output Artifacts")
    folder = OUTPUT_FOLDER / current_case / "artifacts"

    if not folder.exists():
        st.warning("Artifacts folder not found.")
        return

    files = sorted([f for f in os.listdir(folder) if f not in [".",".."]])
    if not files:
        st.info("No output artifacts found.")
        return

    # st.download_button streams files — safe even for large artifacts (no OOM)
    st.markdown("""
    <div style="background:#141e2e;border:1px solid #1e2d45;border-radius:12px;
                padding:0;overflow:hidden;margin-bottom:16px;">
      <div style="display:grid;grid-template-columns:2fr 2fr 1fr 1fr;
                  background:#0f1623;border-bottom:1px solid #1e2d45;padding:10px 16px;gap:8px;">
        <span style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;">File</span>
        <span style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;">Description</span>
        <span style="font-size:10px;font-weight:600;color:#475569;letter-spacing:1.5px;text-transform:uppercase;">Size</span>
        <span></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    for i, filename in enumerate(files):
        path   = folder / filename
        sz     = path.stat().st_size
        sz_str = f"{sz/(1024*1024):.2f} MB" if sz > 1024*1024 else f"{sz/1024:.2f} KB"
        info   = ARTIFACT_DESCS.get(filename, {"title": filename, "description": "Raw Volatility 3 output."})
        bg     = "#141e2e" if i % 2 == 0 else "#111827"
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            st.markdown(f'<div style="background:{bg};padding:10px 16px;font-size:13px;'
                        f'color:#e2e8f0;font-family:Inter,sans-serif;">{info["title"]}</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="background:{bg};padding:10px 16px;font-size:12px;'
                        f'color:#475569;font-family:Inter,sans-serif;">{info["description"]}</div>',
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div style="background:{bg};padding:10px 16px;font-size:12px;'
                        f'color:#475569;font-family:JetBrains Mono,monospace;">{sz_str}</div>',
                        unsafe_allow_html=True)
        with c4:
            with open(path, "rb") as fh:
                st.download_button(
                    label="↓ Download",
                    data=fh,
                    file_name=filename,
                    key=f"dl_{filename}_{i}",
                )


# ==============================================================================
# 11. Config tab
# ==============================================================================

def render_config_tab(detections_cfg, baseline_cfg):
    section_label("Configuration Files")
    if detections_cfg:
        with st.expander("detections.yaml"):
            st.code(yaml.dump(detections_cfg, indent=2, sort_keys=False), language='yaml')
    if baseline_cfg:
        with st.expander("baseline.yaml"):
            st.code(yaml.dump(baseline_cfg, indent=2, sort_keys=False), language='yaml')
    if not detections_cfg or not baseline_cfg:
        st.warning("One or more config files were not found.")


# ==============================================================================
# 12. Main
# ==============================================================================

def main():
    defaults = {
        'logged_in':             False,
        'current_case':          None,
        'current_file':          None,
        'analysis_started':      False,
        'analysis_successful':   False,
        'analysis_logs':         [],
        'ip_enrichment_api_key': '',
        'cancel_requested':      False,   # set True by cancel button
        'cancelled_case':        None,    # carry case name to show warning
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    case_files = [
        f.name for f in MEMORY_FOLDER.iterdir()
        if f.is_file() and f.name != ".gitkeep"
    ]

    if not st.session_state.logged_in:
        screen_login()

    elif st.session_state.analysis_started and not st.session_state.analysis_successful:
        screen_progress()

    elif st.session_state.current_case and st.session_state.analysis_successful:
        screen_results()

    else:
        screen_new_analysis(case_files)


if __name__ == '__main__':
    main()
