"""
26AS Enterprise Reconciliation Pro v3.0
=======================================
Author: Abhishek Jakkula
License: MIT
Description: AI-powered TDS reconciliation between TRACES Form 26AS (.txt) and Books Excel (.xlsx)
Features: RapidFuzz matching, Smart Memory, TDS Rate Auditor, Glassmorphic UI, Interactive Dashboard, 
          Multi-sheet Excel Export, Advanced Filtering, Session Persistence, and Production-Grade Caching.
"""

import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import logging
import os
from rapidfuzz import process, fuzz
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

# ============================================================
# 1. CONFIGURATION & CONSTANTS
# ============================================================
CONFIG = {
    "app_title": "26AS Enterprise Reconciliation Pro",
    "app_icon": "📊",
    "version": "3.0.0",
    "developer": "Abhishek Jakkula",
    "contact": "jakkulaabhishek5@gmail.com",
    "max_file_size_mb": 50,
    "cache_ttl_seconds": 3600,
    "preview_limit": 50,
    "tolerance_default": 10,
    "fuzzy_cutoff_default": 70,
    "standard_tds_rates": {1.0, 2.0, 5.0, 10.0, 20.0, 30.0}
}

# ============================================================
# 2. LOGGING & UTILITIES
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def hash_bytes(data: bytes) -> str:
    """Generate SHA256 hash for cache key generation."""
    if not isinstance(data, bytes):
        data = str(data).encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def safe_decode(file_bytes: bytes) -> str:
    """Robust multi-encoding decoder for TRACES files."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    logger.warning("All standard encodings failed. Falling back to utf-8 replacement.")
    return file_bytes.decode('utf-8', errors='replace')

def validate_dataframe_columns(df: pd.DataFrame, required_cols: List[str], source_name: str) -> Optional[str]:
    """Validate required columns exist in DataFrame. Returns error message or None."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return f"❌ {source_name} is missing required columns: {', '.join(missing)}"
    return None

def format_currency(value: float) -> str:
    """Format float to Indian currency string."""
    try:
        return f"₹{value:,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"

# ============================================================
# 3. STREAMLIT PAGE CONFIGURATION & CSS
# ============================================================
st.set_page_config(
    page_title=CONFIG["app_title"],
    layout="wide",
    page_icon=CONFIG["app_icon"],
    initial_sidebar_state="expanded"
)

ENHANCED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    --glass-bg: rgba(255, 255, 255, 0.15);
    --glass-border: rgba(255, 255, 255, 0.25);
    --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.25);
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a6a;
    --card-radius: 24px;
    --button-radius: 50px;
    --input-radius: 16px;
}

@media (prefers-color-scheme: dark) {
    :root {
        --glass-bg: rgba(30, 30, 50, 0.65);
        --glass-border: rgba(255, 255, 255, 0.12);
        --text-primary: #f0f0f8;
        --text-secondary: #b0b0c8;
    }
    .stApp { background: #0f0f1e !important; }
}

@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; color: var(--text-primary); }
.stApp {
    background: linear-gradient(-45deg, #667eea, #764ba2, #4facfe, #f093fb);
    background-size: 400% 400%;
    animation: gradientShift 20s ease infinite;
    min-height: 100vh;
    padding: 1rem;
}
@keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: var(--card-radius);
    padding: 1.5rem 2rem;
    margin: 1rem 0;
    box-shadow: var(--glass-shadow);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.glass-card:hover { transform: translateY(-4px); box-shadow: 0 16px 48px rgba(31, 38, 135, 0.4); }
.glass-card.critical { border-left: 4px solid #ef4444; }
.glass-card.warning { border-left: 4px solid #f59e0b; }
.glass-card.success { border-left: 4px solid #10b981; }
.glass-card.info { border-left: 4px solid #3b82f6; }

.header-title { font-size: 3.2rem; font-weight: 800; background: linear-gradient(90deg, #fff, #e0e7ff, #fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; text-align: center; }
.header-subtitle { font-size: 1.15rem; font-weight: 500; color: var(--text-secondary); text-align: center; margin: 0.5rem 0; }
.header-credit { font-size: 0.95rem; color: var(--text-secondary); text-align: center; }
.header-credit b { background: linear-gradient(90deg, #667eea, #f093fb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

.zone-badge { display: inline-flex; align-items: center; gap: 0.5rem; background: var(--glass-bg); backdrop-filter: blur(12px); padding: 0.75rem 1.5rem; border-radius: 50px; border: 1px solid var(--glass-border); font-weight: 600; margin: 0.5rem 0; }

[data-testid="stFileUploader"] { background: var(--glass-bg) !important; border-radius: var(--input-radius) !important; border: 2px dashed var(--glass-border) !important; padding: 1.25rem !important; }
.stButton>button, .stDownloadButton>button { background: var(--primary-gradient) !important; color: white !important; border: none !important; border-radius: var(--button-radius) !important; padding: 0.85rem 2rem !important; font-weight: 600 !important; box-shadow: 0 4px 20px rgba(102, 126, 234, 0.35) !important; width: 100%; transition: all 0.2s ease !important; }
.stButton>button:hover, .stDownloadButton>button:hover { transform: translateY(-3px) !important; filter: brightness(1.05) !important; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.55) !important; }

[data-testid="stMetric"] { background: var(--glass-bg); backdrop-filter: blur(12px); border-radius: var(--card-radius); padding: 1.25rem; border: 1px solid var(--glass-border); }
[data-testid="stMetricValue"] { font-size: 2rem; font-weight: 800; }
[data-testid="stMetricLabel"] { color: var(--text-secondary); font-weight: 500; }

.alert-box { backdrop-filter: blur(12px); padding: 1rem 1.25rem; border-radius: 16px; margin: 0.75rem 0; border-left: 4px solid; color: var(--text-primary); }
.alert-box.critical { background: rgba(239,68,68,0.12); border-left-color: #ef4444; }
.alert-box.warning { background: rgba(245,158,11,0.12); border-left-color: #f59e0b; }
.alert-box.info { background: rgba(59,130,246,0.12); border-left-color: #3b82f6; }
.alert-box.success { background: rgba(16,185,129,0.12); border-left-color: #10b981; }

[data-testid="stDataFrame"] table { background: var(--glass-bg); backdrop-filter: blur(8px); border-radius: 16px; overflow: hidden; border: 1px solid var(--glass-border); }
[data-testid="stDataFrame"] th { background: var(--primary-gradient) !important; color: white !important; font-weight: 700; padding: 0.75rem; }
[data-testid="stDataFrame"] td { padding: 0.6rem 0.75rem; }

.streamlit-expanderHeader { background: var(--glass-bg); backdrop-filter: blur(12px); border-radius: var(--input-radius); font-weight: 600; border: 1px solid var(--glass-border); }
.streamlit-expanderContent { background: var(--glass-bg); backdrop-filter: blur(12px); border: 1px solid var(--glass-border); border-top: none; }

footer { visibility: hidden; }
.stProgress > div > div { background: var(--secondary-gradient) !important; border-radius: 10px; }

@media (max-width: 768px) {
    .header-title { font-size: 2.2rem; }
    .glass-card { padding: 1.25rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
}
"""
st.markdown(f"<style>{ENHANCED_CSS}</style>", unsafe_allow_html=True)

# ============================================================
# 4. UI COMPONENTS: HEADER & SIDEBAR
# ============================================================
def render_header():
    """Render application header."""
    st.markdown("""
    <div class="glass-card" style="margin-bottom: 0;">
        <h1 class="header-title">26AS Enterprise Reconciliation Pro</h1>
        <p class="header-subtitle">🤖 AI-Powered Matching • 📊 Real-Time Analytics • 🔍 TDS Rate Auditor</p>
        <p class="header-credit">Developed by <b>Abhishek Jakkula</b> • <span style="opacity:0.8">v3.0 Stable</span></p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar() -> Tuple[float, int, Dict[str, str]]:
    """Render configuration sidebar. Returns tolerance, fuzzy_cutoff, known_mappings."""
    with st.sidebar:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### ⚙️ Engine Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            tolerance = st.number_input(
                "Mismatch Tolerance (₹)", 
                min_value=0, 
                value=CONFIG["tolerance_default"], 
                step=1,
                help="Maximum allowed TDS difference for exact matches"
            )
        with col2:
            fuzzy_cutoff = st.slider(
                "Fuzzy Match Score (%)", 
                min_value=50, 
                max_value=95, 
                value=CONFIG["fuzzy_cutoff_default"], 
                step=5,
                help="Minimum similarity score for fuzzy vendor name matching"
            )
        
        st.markdown("---")
        st.markdown("### 🧠 Smart Memory")
        st.info("Upload a Mapping Dictionary CSV to auto-match custom vendor names across sessions.")
        
        mapping_file = st.file_uploader("📁 Upload Dictionary (CSV)", type=['csv'], label_visibility="collapsed")
        
        known_mappings = {}
        if mapping_file is not None:
            try:
                map_df = pd.read_csv(mapping_file)
                req_cols = ['TAN of Deductor', 'Mapped Books Party']
                if all(c in map_df.columns for c in req_cols):
                    known_mappings = dict(zip(
                        map_df['TAN of Deductor'].astype(str).str.strip().str.upper(),
                        map_df['Mapped Books Party'].astype(str).str.strip().str.upper()
                    ))
                    st.success(f"✅ Loaded **{len(known_mappings)}** custom mappings!")
                    logger.info(f"Loaded {len(known_mappings)} dictionary mappings")
                else:
                    st.warning(f"CSV must contain columns: {req_cols}")
            except Exception as e:
                st.error(f"❌ Invalid dictionary format: {str(e)[:100]}")
                logger.error(f"Dictionary load failed: {e}")
        
        st.markdown("---")
        st.markdown("### 📈 System Info")
        st.metric("Standard TDS Rates", ", ".join(map(str, sorted(CONFIG["standard_tds_rates"]))))
        st.metric("Max Upload Size", f"{CONFIG['max_file_size_mb']} MB")
        st.markdown("</div>", unsafe_allow_html=True)
        
    return tolerance, fuzzy_cutoff, known_mappings

# ============================================================
# 5. FILE MANAGEMENT & SESSION STATE
# ============================================================
def initialize_session_state():
    """Initialize session state variables for persistence across reruns."""
    defaults = {
        "uploaded_txt_bytes": None,
        "uploaded_books_bytes": None,
        "txt_filename": "",
        "books_filename": "",
        "metadata_extracted": False,
        "pan": "Unknown", "fy": "Unknown", "ay": "Unknown",
        "is_ready": False,
        "processed_data": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def handle_file_uploads() -> bool:
    """Handle file uploaders, validate size, and store in session state. Returns True if ready."""
    st.markdown('<div class="zone-badge">📄 Step 1: Upload Your Files</div>', unsafe_allow_html=True)
    
    # Create sample files for download
    sample_books = pd.DataFrame({
        "Party Name": ["ABC Technologies Pvt Ltd", "XYZ Corporation", "Global Services Inc"],
        "TAN": ["HYDA00000A", "MUMC12345B", ""],
        "Books Amount": [100000, 50000, 75000],
        "Books TDS": [10000, 5000, 7500]
    })
    books_buf = io.BytesIO()
    sample_books.to_excel(books_buf, index=False, engine='openpyxl')
    books_buf.seek(0)
    
    sample_dict = pd.DataFrame({
        "TAN of Deductor": ["HYDA00000A", "MUMC12345B"],
        "Mapped Books Party": ["ABC Technologies Pvt Ltd", "XYZ Corporation"]
    })
    dict_csv = sample_dict.to_csv(index=False).encode('utf-8')
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Sample Books Excel", books_buf, "Sample_Books.xlsx", use_container_width=True, type="secondary")
    with col2:
        st.download_button("⬇️ Sample Mapping CSV", dict_csv, "Sample_Mapping.csv", mime="text/csv", use_container_width=True, type="secondary")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        txt_file = st.file_uploader("📄 TRACES 26AS (.txt)", type=["txt"], label_visibility="collapsed")
    with col_f2:
        books_file = st.file_uploader("📊 Books Data (.xlsx/.xls)", type=["xlsx", "xls"], label_visibility="collapsed")
    
    # Update session state immediately on upload
    if txt_file is not None:
        st.session_state.uploaded_txt_bytes = txt_file.getvalue()
        st.session_state.txt_filename = txt_file.name
        
    if books_file is not None:
        st.session_state.uploaded_books_bytes = books_file.getvalue()
        st.session_state.books_filename = books_file.name
    
    # Validation
    txt_bytes = st.session_state.uploaded_txt_bytes
    books_bytes = st.session_state.uploaded_books_bytes
    
    if txt_bytes and len(txt_bytes) > CONFIG["max_file_size_mb"] * 1024 * 1024:
        st.error(f"❌ 26AS file exceeds {CONFIG['max_file_size_mb']}MB limit")
        return False
    if books_bytes and len(books_bytes) > CONFIG["max_file_size_mb"] * 1024 * 1024:
        st.error(f"❌ Books file exceeds {CONFIG['max_file_size_mb']}MB limit")
        return False
    
    return bool(txt_bytes and books_bytes)

def extract_metadata() -> bool:
    """Extract PAN, FY, AY from 26AS text. Updates session state."""
    txt_bytes = st.session_state.uploaded_txt_bytes
    if not txt_bytes:
        return False
    
    raw_text = safe_decode(txt_bytes)
    pan, fy, ay = "Unknown", "Unknown", "Unknown"
    
    patterns = [
        (r'\d{2}-\d{2}-\d{4}\^([A-Z]{5}\d{4}[A-Z])\^[^\^]*\^(\d{4}-\d{4})\^(\d{4}-\d{4})', 3),
        (r'PAN[:\s]*([A-Z]{5}\d{4}[A-Z])', 1),
        (r'Financial\s+Year[:\s]*(\d{4}-\d{4})', 1),
        (r'Assessment\s+Year[:\s]*(\d{4}-\d{4})', 1)
    ]
    
    for pattern, groups in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            if groups == 3:
                pan, fy, ay = match.groups()
                break
            elif groups == 1:
                val = match.group(1)
                if re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]', val): pan = val
                elif re.fullmatch(r'\d{4}-\d{4}', val):
                    if fy == "Unknown": fy = val
                    else: ay = val
    
    if pan == "Unknown":
        fallback = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', raw_text)
        if fallback: pan = fallback.group(0)
    
    st.session_state.pan, st.session_state.fy, st.session_state.ay = pan, fy, ay
    st.session_state.metadata_extracted = True
    
    st.markdown(f"""
    <div class="alert-box success">
        <b>📌 Detected:</b> PAN <b>{pan}</b> | FY <b>{fy}</b> | AY <b>{ay}</b><br>
        <i>Ensure your Books data matches this financial period for accurate reconciliation</i>
    </div>
    """, unsafe_allow_html=True)
    return True

# ============================================================
# 6. CORE ENGINE FUNCTIONS (CACHED & PURE)
# ============================================================
@st.cache_data(ttl=CONFIG["cache_ttl_seconds"], show_spinner="🔍 Parsing 26AS PART-I transactions...")
def parse_26as_data(txt_bytes: bytes) -> pd.DataFrame:
    """Extract transaction-level details from TRACES Form 26AS PART-I."""
    logger.info("Starting 26AS parsing...")
    lines = safe_decode(txt_bytes).splitlines()
    transactions = []
    current_name, current_tan = None, None
    
    part1_idx = next((i for i, l in enumerate(lines) if "PART-I - Details of Tax Deducted at Source" in l), -1)
    if part1_idx == -1:
        logger.warning("PART-I section not found in uploaded file.")
        return pd.DataFrame()
    
    i = part1_idx + 1
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("^PART-") and "PART-I" not in line:
            break
        if not line:
            i += 1
            continue
            
        parts = [p.strip() for p in line.split("^") if p.strip()]
        if not parts:
            i += 1
            continue
            
        # Summary line: SlNo ^ Name ^ TAN ^ ...
        if len(parts) >= 3 and re.fullmatch(r'\d+', parts[0]) and re.fullmatch(r'[A-Z]{4}\d{5}[A-Z]', parts[2]):
            current_name, current_tan = parts[1], parts[2]
            i += 2  # Skip header row
            continue
            
        # Transaction line: SlNo ^ Section ^ Date ^ ... ^ Amount ^ TDS ^ ...
        if current_name and current_tan and len(parts) >= 9:
            if re.fullmatch(r'\d+', parts[0]) and re.fullmatch(r'\d+[A-Z]+', parts[1]):
                try:
                    transactions.append({
                        "Sl. No.": int(parts[0]),
                        "Section": parts[1],
                        "Name of Deductor": current_name,
                        "TAN of Deductor": current_tan,
                        "Amount paid/credited": float(parts[6].replace(",", "")),
                        "Date of Payment/Credit": parts[2],
                        "Total tax deducted": float(parts[7].replace(",", "")),
                        "Amount claimed for this year": 0.0,
                        "C/F Tax": 0.0
                    })
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipped malformed line {i}: {e}")
        i += 1
        
    df = pd.DataFrame(transactions)
    logger.info(f"Successfully extracted {len(df)} transactions.")
    return df

@st.cache_data(ttl=CONFIG["cache_ttl_seconds"], show_spinner="🔄 Running AI Matching Engine...")
def run_reconciliation_engine(
    txt_bytes: bytes,
    books_bytes: bytes,
    known_mappings: Dict[str, str],
    tolerance: float,
    fuzzy_cutoff: int,
    preview: bool
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Main reconciliation pipeline. Returns (final_recon, agg_section, raw_26as, books_clean)."""
    logger.info("Initializing reconciliation pipeline...")
    
    # 1. Parse 26AS
    raw_26as = parse_26as_data(txt_bytes)
    if raw_26as.empty:
        logger.error("No transaction data found in 26AS PART-I.")
        raise ValueError("Empty 26AS dataset after parsing. Please verify file format.")
    
    if preview and len(raw_26as) > CONFIG["preview_limit"]:
        raw_26as = raw_26as.head(CONFIG["preview_limit"])
        logger.info(f"Preview mode active: Limited to {CONFIG['preview_limit']} records.")
        
    # 2. Aggregate by Section
    agg_section = raw_26as.groupby(['TAN of Deductor', 'Name of Deductor', 'Section'], as_index=False).agg({
        'Amount paid/credited': 'sum',
        'Total tax deducted': 'sum'
    }).rename(columns={
        'Amount paid/credited': 'Total Amount Paid / Credited',
        'Total tax deducted': 'Total TDS Deposited'
    })
    
    # TAN to Sections lookup
    tan_sections = agg_section.groupby('TAN of Deductor')['Section'].agg(lambda x: ','.join(sorted(set(x)))).to_dict()
    
    # 3. Aggregate by Deductor
    agg_deductor = agg_section.groupby(['TAN of Deductor', 'Name of Deductor'], as_index=False).agg({
        'Total Amount Paid / Credited': 'sum',
        'Total TDS Deposited': 'sum'
    })
    
    # 4. Load & Clean Books
    books = pd.read_excel(io.BytesIO(books_bytes))
    err = validate_dataframe_columns(books, ["Party Name", "Books Amount", "Books TDS"], "Books")
    if err:
        raise ValueError(err)
    if "TAN" not in books.columns:
        books["TAN"] = ""
        
    books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()
    books["Party Name"] = books["Party Name"].fillna("").astype(str).str.strip().str.upper()
    
    for col in ["Books Amount", "Books TDS"]:
        books[col] = pd.to_numeric(books[col], errors="coerce").fillna(0)
    books = books.groupby(['Party Name', 'TAN'], as_index=False)[["Books Amount", "Books TDS"]].sum()
    
    # 5. Exact TAN Match
    agg_deductor["TAN of Deductor"] = agg_deductor["TAN of Deductor"].astype(str).str.strip().str.upper()
    exact = pd.merge(agg_deductor, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
    exact["Match Type"] = "Exact (TAN)"
    
    matched_tans = exact["TAN of Deductor"].unique()
    unmatched_26as = agg_deductor[~agg_deductor["TAN of Deductor"].isin(matched_tans)].copy()
    unmatched_books = books[~books["TAN"].isin(matched_tans)].copy()
    
    # 6. Dictionary Match
    if known_mappings:
        for tan_26, target_name in known_mappings.items():
            r26 = unmatched_26as[unmatched_26as["TAN of Deductor"] == tan_26]
            rbk = unmatched_books[unmatched_books["Party Name"] == target_name]
            if not r26.empty and not rbk.empty:
                merged = r26.iloc[0].to_dict()
                merged.update({k: rbk.iloc[0][k] for k in ["Party Name", "TAN", "Books Amount", "Books TDS"]})
                merged["Match Type"] = "Dictionary Match"
                exact = pd.concat([exact, pd.DataFrame([merged])], ignore_index=True)
                unmatched_26as = unmatched_26as[unmatched_26as["TAN of Deductor"] != tan_26]
                unmatched_books = unmatched_books[unmatched_books["Party Name"] != target_name]
                
    # 7. Fuzzy Match
    fuzzy_results = []
    matched_book_idx = set()
    book_list = [(idx, row["Party Name"]) for idx, row in unmatched_books.iterrows()]
    
    for _, row_26 in unmatched_26as.iterrows():
        name_26 = str(row_26["Name of Deductor"]).upper()
        if not book_list:
            fuzzy_results.append({**row_26.to_dict(), "Match Type": "Missing in Books"})
            continue
            
        # Pre-filter by first letter for O(n) performance on large lists
        candidates = [(i, n) for i, n in book_list if n and n[0] == name_26[0]] if len(book_list) > 50 else book_list
        if not candidates: candidates = book_list
        
        match = process.extractOne(
            name_26, 
            [n for _, n in candidates], 
            scorer=fuzz.token_sort_ratio, 
            score_cutoff=fuzzy_cutoff
        )
        
        if match:
            _, score, c_idx = match
            orig_idx = candidates[c_idx][0]
            if orig_idx not in matched_book_idx:
                res = row_26.to_dict()
                res.update({k: unmatched_books.loc[orig_idx][k] for k in ["Party Name", "TAN", "Books Amount", "Books TDS"]})
                res["Match Type"] = "Fuzzy Match"
                res["Fuzzy Score"] = round(score, 1)
                fuzzy_results.append(res)
                matched_book_idx.add(orig_idx)
        else:
            fuzzy_results.append({**row_26.to_dict(), "Match Type": "Missing in Books"})
            
    # 8. Books Missing in 26AS
    for idx, row in unmatched_books.iterrows():
        if idx not in matched_book_idx:
            res = row.to_dict()
            for c in ["Name of Deductor", "TAN of Deductor", "Total Amount Paid / Credited", "Total TDS Deposited", "Section"]:
                res[c] = ""
            res["Match Type"] = "Missing in 26AS"
            fuzzy_results.append(res)
            
    # 9. Combine & Finalize
    recon = pd.concat([exact, pd.DataFrame(fuzzy_results) if fuzzy_results else pd.DataFrame()], ignore_index=True)
    
    for col in ["Name of Deductor", "Party Name", "TAN of Deductor", "TAN", "Section"]:
        if col not in recon.columns:
            recon[col] = ""
            
    recon["Deductor / Party Name"] = recon["Name of Deductor"].where(
        recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""), recon["Party Name"]
    )
    recon["Final TAN"] = recon["TAN of Deductor"].where(
        recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""), recon["TAN"]
    )
    recon['26AS Sections'] = recon['TAN of Deductor'].map(tan_sections).fillna('')
    
    logger.info(f"Pipeline complete. {len(recon)} records reconciled.")
    return recon, agg_section, raw_26as, books

def add_totals_row(df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
    """Append a totals row to a DataFrame."""
    if df.empty: return df
    totals = {col: df[col].sum() if col in numeric_cols else "TOTAL" for col in df.columns}
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

# ============================================================
# 7. MAIN APPLICATION LOGIC
# ============================================================
def main():
    """Main Streamlit app execution flow."""
    render_header()
    tolerance, fuzzy_cutoff, known_mappings = render_sidebar()
    initialize_session_state()
    
    if not handle_file_uploads():
        st.markdown('<div class="alert-box info" style="text-align:center;"><b>ℹ️ Please upload both files to begin.</b></div>', unsafe_allow_html=True)
        return
        
    if not extract_metadata():
        st.warning("⚠️ Could not extract PAN/FY/AY metadata. Continuing anyway...")
        
    preview_mode = st.checkbox("🔍 Preview Mode (Process first 50 records)", value=False)
    if preview_mode:
        st.info(f"⚡ Preview mode enabled: Only first {CONFIG['preview_limit']} records will be processed for rapid testing.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 3, 1])
    with col_btn2:
        # Button is enabled only when both files are in session state
        run_btn = st.button(
            "🚀 LAUNCH RECONCILIATION ENGINE", 
            use_container_width=True, 
            type="primary",
            disabled=not (st.session_state.uploaded_txt_bytes and st.session_state.uploaded_books_bytes)
        )
        
    if not run_btn:
        return
        
    # --- EXECUTION BLOCK ---
    with st.spinner("🚀 Processing files with AI Engine..."):
        try:
            txt_bytes = st.session_state.uploaded_txt_bytes
            books_bytes = st.session_state.uploaded_books_bytes
            
            # Cache keys (bytes are hashable in modern Streamlit)
            txt_h = hash_bytes(txt_bytes)
            books_h = hash_bytes(books_bytes)
            map_h = hash_bytes(str(known_mappings))
            
            recon_raw, agg_section, raw_26as, books_clean = run_reconciliation_engine(
                txt_bytes, books_bytes, known_mappings, tolerance, fuzzy_cutoff, preview_mode
            )
        except Exception as e:
            logger.exception("Reconciliation failed")
            st.error(f"❌ Processing Error: {str(e)}")
            st.markdown("""
            <div class="alert-box warning">
                <b>💡 Troubleshooting Tips:</b><br>
                1. Ensure 26AS file is a valid TRACES `.txt` export.<br>
                2. Books Excel must contain: <code>Party Name</code>, <code>Books Amount</code>, <code>Books TDS</code><br>
                3. File size must be under {0} MB.
            </div>
            """.format(CONFIG["max_file_size_mb"]), unsafe_allow_html=True)
            return
            
    if recon_raw.empty:
        st.error("❌ No valid transaction data found in 26AS PART-I. Please verify the file content.")
        return
        
    st.session_state.processed_data = True
    recon = recon_raw.copy()
    
    # --- CALCULATIONS ---
    num_cols = ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS"]
    for col in num_cols:
        if col in recon.columns:
            recon[col] = pd.to_numeric(recon[col], errors="coerce").fillna(0)
            
    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]
    recon['Effective Rate 26AS (%)'] = np.where(
        recon['Total Amount Paid / Credited'] > 0,
        (recon['Total TDS Deposited'] / recon['Total Amount Paid / Credited']) * 100,
        0
    ).round(2)
    
    diff_tds = recon["Difference TDS"].abs()
    conditions = [
        (recon["Match Type"].isin(["Exact (TAN)", "Dictionary Match"])) & (diff_tds <= tolerance),
        (recon["Match Type"].isin(["Exact (TAN)", "Dictionary Match"])) & (diff_tds > tolerance),
        (recon["Match Type"] == "Fuzzy Match") & (diff_tds <= tolerance),
        (recon["Match Type"] == "Fuzzy Match") & (diff_tds > tolerance),
        (recon["Match Type"] == "Missing in Books"),
        (recon["Match Type"] == "Missing in 26AS")
    ]
    statuses = ["✅ Exact Match", "⚠️ Value Mismatch", "🔍 Fuzzy Match", "⚠️ Value Mismatch", "❌ Missing in Books", "❌ Missing in 26AS"]
    reasons = ["Perfect match", "TDS amount differs", "Name matched with fuzzy logic", "TDS amount differs", "Not in Books", "Not in 26AS"]
    
    recon["Match Status"] = np.select(conditions, statuses, default="❓ Unknown")
    recon["Reason for Difference"] = np.select(conditions, reasons, default="Unknown")
    
    final_recon = recon[[
        "26AS Sections", "Match Status", "Deductor / Party Name", "Final TAN",
        "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
        "Total TDS Deposited", "Books TDS", "Difference TDS", "Effective Rate 26AS (%)", "Reason for Difference"
    ]].rename(columns={"Final TAN": "TAN"})
    
    # --- ALERTS ---
    st.markdown('<div class="glass-card critical">', unsafe_allow_html=True)
    st.markdown("### 🚨 Compliance Alerts")
    
    anomalies = recon[(recon['Effective Rate 26AS (%)'] > 0) & (~recon['Effective Rate 26AS (%)'].isin(CONFIG["standard_tds_rates"]))]
    if not anomalies.empty:
        top = anomalies.nlargest(1, 'Total TDS Deposited').iloc[0]
        st.markdown(f"""<div class="alert-box info"><b>🔎 Rate Anomaly:</b> <b>{top['Deductor / Party Name']}</b> deducted at <b>{top['Effective Rate 26AS (%)']}%</b><br><i>Expected rates: {', '.join(map(str, sorted(CONFIG['standard_tds_rates'])))}%</i></div>""", unsafe_allow_html=True)
        
    miss_books = recon[recon["Match Status"] == "❌ Missing in Books"]
    if not miss_books.empty and miss_books["Total TDS Deposited"].sum() > 0:
        top = miss_books.loc[miss_books["Total TDS Deposited"].idxmax()]
        st.markdown(f"""<div class="alert-box critical"><b>🚨 URGENT: Unclaimed TDS!</b> ₹{miss_books['Total TDS Deposited'].sum():,.2f} in 26AS but <b>MISSING</b> in Books<br><i>👉 Largest: <b>{top['Deductor / Party Name']}</b> (₹{top['Total TDS Deposited']:,.2f})</i></div>""", unsafe_allow_html=True)
        
    miss_26as = recon[recon["Match Status"] == "❌ Missing in 26AS"]
    if not miss_26as.empty and miss_26as["Books TDS"].sum() > 0:
        top = miss_26as.loc[miss_26as["Books TDS"].idxmax()]
        st.markdown(f"""<div class="alert-box warning"><b>⚠️ Compliance Risk:</b> ₹{miss_26as['Books TDS'].sum():,.2f} claimed in Books but <b>NOT in 26AS</b><br><i>👉 Largest: <b>{top['Deductor / Party Name']}</b> (₹{top['Books TDS']:,.2f})</i></div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- DASHBOARD ---
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Executive Dashboard")
    
    m1, m2, m3, m4 = st.columns(4)
    total_26as = recon['Total TDS Deposited'].sum()
    total_books = recon['Books TDS'].sum()
    net_var = total_26as - total_books
    exact_count = (recon["Match Status"] == "✅ Exact Match").sum()
    exact_pct = (exact_count / len(recon) * 100) if len(recon) > 0 else 0
    
    m1.metric("🏦 TDS in 26AS", format_currency(total_26as))
    m2.metric("📒 TDS in Books", format_currency(total_books))
    m3.metric("📐 Net Variance", format_currency(net_var), delta=format_currency(net_var), delta_color="inverse")
    m4.metric("🎯 Match Rate", f"{exact_pct:.1f}%", delta=f"{exact_count} records exact")
    
    st.markdown("<br>", unsafe_allow_html=True)
    chart1, chart2 = st.columns(2)
    
    with chart1:
        status_counts = final_recon["Match Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        color_map = {
            "✅ Exact Match": "#10b981", "🔍 Fuzzy Match": "#3b82f6",
            "⚠️ Value Mismatch": "#f59e0b", "❌ Missing in Books": "#ef4444", 
            "❌ Missing in 26AS": "#8b5cf6", "❓ Unknown": "#6b7280"
        }
        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts["Status"], values=status_counts["Count"], hole=0.45,
            marker=dict(colors=[color_map.get(s, "#94a3b8") for s in status_counts["Status"]]),
            textinfo="label+percent", hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
        )])
        fig_pie.update_layout(
            title="📊 Match Status Distribution", height=350, margin=dict(t=40, b=0, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter"), legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
        
    with chart2:
        section_data = []
        for _, row in recon.iterrows():
            if row['26AS Sections']:
                for sec in str(row['26AS Sections']).split(','):
                    section_data.append({'Section': sec.strip(), 'TDS': row['Total TDS Deposited']})
        if section_data:
            sec_df = pd.DataFrame(section_data)
            sec_summary = sec_df.groupby('Section')['TDS'].sum().reset_index().sort_values('TDS', ascending=False)
            fig_bar = go.Figure(data=[go.Bar(
                x=sec_summary['Section'], y=sec_summary['TDS'],
                marker=dict(color=sec_summary['TDS'], colorscale='Blues', showscale=True),
                hovertemplate="<b>%{x}</b><br>TDS: ₹%{y:,.0f}<extra></extra>"
            )])
            fig_bar.update_layout(
                title="📑 TDS by Section (26AS)", height=350, margin=dict(t=40, b=0, l=0, r=0),
                xaxis_title="Section", yaxis_title="TDS Amount (₹)",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter")
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("ℹ️ No section data available")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- ADVANCED ANALYTICS ---
    with st.expander("🔬 Advanced Analytics", expanded=False):
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            top_26as = final_recon[final_recon["Total TDS Deposited"] > 0].nlargest(10, "Total TDS Deposited")
            if not top_26as.empty:
                fig_top = px.bar(top_26as, x="Total TDS Deposited", y="Deductor / Party Name", orientation='h',
                                 title="🏆 Top 10 by TDS (26AS)", color="Total TDS Deposited", color_continuous_scale="Viridis")
                fig_top.update_layout(height=400, yaxis={'categoryorder':'total ascending'}, margin=dict(l=10))
                st.plotly_chart(fig_top, use_container_width=True)
                
        with col_a2:
            variance_data = final_recon[final_recon["Difference TDS"] != 0].copy()
            if not variance_data.empty:
                variance_data["Abs Variance"] = variance_data["Difference TDS"].abs()
                top_var = variance_data.nlargest(20, "Abs Variance")
                fig_var = px.scatter(top_var, x="Total TDS Deposited", y="Books TDS", size="Abs Variance",
                                     color="Match Status", hover_name="Deductor / Party Name",
                                     title="📉 Variance Analysis (Top 20)",
                                     color_discrete_map={k: v for k, v in color_map.items() if k in top_var["Match Status"].unique()})
                max_val = max(variance_data["Total TDS Deposited"].max(), variance_data["Books TDS"].max())
                fig_var.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode='lines', 
                                             line=dict(dash='dash', color='gray'), name='Perfect Match', showlegend=True))
                fig_var.update_layout(height=400)
                st.plotly_chart(fig_var, use_container_width=True)
            else:
                st.success("✅ Zero variance detected! All matched records align perfectly.")
                
    # --- DATA TABLE ---
    with st.expander("📋 View Reconciliation Data", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_opts = final_recon["Match Status"].unique()
            status_filter = st.multiselect("Filter by Status", options=status_opts, default=list(status_opts))
        with col_f2:
            min_tds = st.number_input("Min TDS (₹)", min_value=0, value=0, step=1000)
        with col_f3:
            search_term = st.text_input("🔍 Search Party/TAN", placeholder="Type to filter...")
            
        filtered = final_recon[
            final_recon["Match Status"].isin(status_filter) & 
            (final_recon["Total TDS Deposited"] >= min_tds)
        ]
        if search_term:
            mask = (
                filtered["Deductor / Party Name"].str.contains(search_term, case=False, na=False) | 
                filtered["TAN"].str.contains(search_term, case=False, na=False)
            )
            filtered = filtered[mask]
            
        if filtered.empty:
            st.info("🔍 No records match your current filters. Adjust criteria above.")
        else:
            # Safe formatting without matplotlib dependency
            fmt_cols = {
                "Total Amount Paid / Credited": "₹{:,.0f}", "Books Amount": "₹{:,.0f}", 
                "Difference Amount": "₹{:+,.0f}", "Total TDS Deposited": "₹{:,.0f}", 
                "Books TDS": "₹{:,.0f}", "Difference TDS": "₹{:+,.0f}", "Effective Rate 26AS (%)": "{:.2f}%"
            }
            safe_fmt = {k: v for k, v in fmt_cols.items() if k in filtered.columns}
            st.dataframe(
                filtered.style.format(safe_fmt), 
                use_container_width=True, 
                height=450,
                column_config={"Match Status": st.column_config.TextColumn("Status", help="Reconciliation outcome")}
            )
            
    # --- EXCEL EXPORT ---
    output = io.BytesIO()
    last_row = len(final_recon) + 3
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book
        fmt_title = wb.add_format({"bold": True, "font_size": 16, "bg_color": "#1e1e3f", "font_color": "#667eea", "align": "center"})
        fmt_header = wb.add_format({"bold": True, "bg_color": "#4f46e5", "font_color": "white", "border": 1, "align": "center"})
        fmt_currency = wb.add_format({"num_format": '"₹"#,##0.00'})
        fmt_percent = wb.add_format({"num_format": "0.00%"})
        fmt_total = wb.add_format({"bold": True, "bg_color": "#e0e7ff", "border": 1, "num_format": '"₹"#,##0.00'})
        
        # Dashboard Sheet
        dash = wb.add_worksheet("Dashboard")
        fy_tag = st.session_state.fy if st.session_state.fy != "Unknown" else "N/A"
        dash.merge_range("A1:K2", f"26AS RECONCILIATION REPORT | FY: {fy_tag} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_title)
        
        metrics = [
            ("Total Records", len(final_recon)), ("Exact Matches", exact_count),
            ("Total TDS (26AS)", total_26as), ("Total TDS (Books)", total_books),
            ("Net Variance", net_var), ("Match Rate %", f"{exact_pct:.1f}%")
        ]
        for i, (lbl, val) in enumerate(metrics):
            dash.write(i+3, 0, lbl, wb.add_format({"bold": True}))
            dash.write(i+3, 1, val)
        dash.write(10, 0, "Status Breakdown", fmt_header)
        for i, (_, row) in enumerate(status_counts.iterrows()):
            dash.write(11+i, 0, row["Status"])
            dash.write(11+i, 1, row["Count"])
            
        # Reconciliation Sheet
        recon_sheet = wb.add_worksheet("Reconciliation")
        final_recon.to_excel(writer, sheet_name="Reconciliation", startrow=2, index=False, header=False)
        for col, name in enumerate(final_recon.columns):
            recon_sheet.write(1, col, name, fmt_header)
            if "Amount" in name or "TDS" in name: recon_sheet.set_column(col, col, None, fmt_currency)
            elif "Rate" in name: recon_sheet.set_column(col, col, None, fmt_percent)
            else: recon_sheet.set_column(col, col, max(15, len(name) + 2))
            
        for col, name in enumerate(final_recon.columns):
            if name in ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS", "Difference Amount", "Difference TDS"]:
                col_letter = chr(65 + col)
                recon_sheet.write_formula(0, col, f'=SUBTOTAL(9,{col_letter}3:{col_letter}{last_row})', fmt_total)
        recon_sheet.autofilter(1, 0, last_row, len(final_recon.columns)-1)
        
        # 26AS by Section Sheet
        if not agg_section.empty:
            agg_sheet = wb.add_worksheet("26AS by Section")
            agg_with_total = add_totals_row(agg_section, ["Total Amount Paid / Credited", "Total TDS Deposited"])
            agg_with_total.to_excel(writer, sheet_name="26AS by Section", startrow=1, index=False, header=False)
            for col in range(len(agg_with_total.columns)):
                if "Amount" in agg_with_total.columns[col] or "TDS" in agg_with_total.columns[col]:
                    agg_sheet.set_column(col, col, None, fmt_currency)
                    
        # Raw Data Sheets
        if not raw_26as.empty: raw_26as.to_excel(writer, sheet_name="26AS Raw Data", index=False)
        books_clean.to_excel(writer, sheet_name="Books Raw", index=False)
        
    output.seek(0)
    st.markdown('<div class="glass-card success">', unsafe_allow_html=True)
    fy_safe = st.session_state.fy.replace('-', '_') if st.session_state.fy != 'Unknown' else 'Latest'
    st.download_button(
        "⬇️ Download Complete Excel Report", 
        output, 
        f"26AS_Recon_{fy_safe}_{datetime.now().strftime('%Y%m%d')}.xlsx", 
        use_container_width=True, 
        type="primary"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.success("✅ Enterprise Reconciliation completed successfully! Review alerts and download your report.")

# ============================================================
# 8. ENTRY POINT
# ============================================================
if __name__ == "__main__":
    main()
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center; padding:2rem; opacity:0.85;">
        <div style="font-weight:700; font-size:1.1rem;">✨ {CONFIG['app_title']} ✨</div>
        <div style="margin:0.5rem 0;">
            <span>👨‍💻 Developed by <b>{CONFIG['developer']}</b></span> • 
            <span>📧 <a href="mailto:{CONFIG['contact']}" style="color:#667eea;text-decoration:none">{CONFIG['contact']}</a></span>
        </div>
        <div style="font-size:0.9rem; opacity:0.9;">🔐 Secure • ⚡ Fast • 🎯 Accurate • 📱 Responsive</div>
    </div>
    """, unsafe_allow_html=True)
