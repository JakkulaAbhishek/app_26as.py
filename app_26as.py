import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import hashlib
import logging
from rapidfuzz import process, fuzz
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============ CONFIGURATION ============
STANDARD_TDS_RATES = {1.0, 2.0, 5.0, 10.0, 20.0, 30.0}
CONFIG = {
    "tolerance_default": 10,
    "fuzzy_cutoff_default": 70,
    "max_file_size_mb": 50,
    "cache_ttl_seconds": 3600,
    "preview_limit": 50,
    "app_title": "26AS Enterprise Reconciliation Pro",
    "app_icon": "📊"
}

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============ STREAMLIT SETUP ============
st.set_page_config(
    page_title=CONFIG["app_title"],
    layout="wide",
    page_icon=CONFIG["app_icon"],
    initial_sidebar_state="expanded"
)

# ============ ENHANCED GLASSMORPHIC UI ============
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    --warning-gradient: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    --danger-gradient: linear-gradient(135deg, #ff0844 0%, #ffb199 100%);
    
    --glass-bg: rgba(255, 255, 255, 0.15);
    --glass-border: rgba(255, 255, 255, 0.25);
    --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.25);
    
    --text-primary: #1a1a2e;
    --text-secondary: #4a4a6a;
    --text-on-accent: #ffffff;
    
    --card-radius: 24px;
    --button-radius: 50px;
    --input-radius: 16px;
}

@media (prefers-color-scheme: dark) {
    :root {
        --glass-bg: rgba(30, 30, 50, 0.6);
        --glass-border: rgba(255, 255, 255, 0.12);
        --text-primary: #f0f0f8;
        --text-secondary: #b0b0c8;
    }
    .stApp { background: #0f0f1e !important; }
}

@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
}

/* Global Styles */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
}

.stApp {
    background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #4facfe);
    background-size: 400% 400%;
    animation: gradientShift 20s ease infinite;
    min-height: 100vh;
    padding: 1rem;
}

@keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Glass Cards */
.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: var(--card-radius);
    padding: 1.5rem 2rem;
    margin: 1rem 0;
    box-shadow: var(--glass-shadow);
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px 0 rgba(31, 38, 135, 0.4);
    border-color: rgba(102, 126, 234, 0.5);
}

.glass-card.critical { border-left: 4px solid #ef4444; }
.glass-card.warning { border-left: 4px solid #f59e0b; }
.glass-card.success { border-left: 4px solid #10b981; }
.glass-card.info { border-left: 4px solid #3b82f6; }

/* Header */
.header-container {
    text-align: center;
    padding: 2rem 1rem;
    margin-bottom: 1rem;
}

.header-title {
    font-size: 3.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #fff, #e0e7ff, #fff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: 0 4px 20px rgba(0,0,0,0.15);
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin: 0;
}

.header-subtitle {
    font-size: 1.15rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin: 0.5rem 0 0.25rem;
    opacity: 0.95;
}

.header-credit {
    font-size: 0.95rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
}

.header-credit b {
    background: linear-gradient(90deg, #667eea, #f093fb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
}

/* Zone Badges */
.zone-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    padding: 0.75rem 1.5rem;
    border-radius: 50px;
    border: 1px solid var(--glass-border);
    font-weight: 600;
    font-size: 1.05rem;
    margin: 0.5rem 0;
    color: var(--text-primary);
}

/* File Uploaders */
[data-testid="stFileUploader"] {
    background: var(--glass-bg) !important;
    backdrop-filter: blur(12px);
    border-radius: var(--input-radius) !important;
    border: 2px dashed var(--glass-border) !important;
    padding: 1.25rem !important;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: #667eea !important;
    background: rgba(255,255,255,0.2) !important;
}

/* Buttons */
.stButton > button,
.stDownloadButton > button {
    background: var(--primary-gradient) !important;
    color: var(--text-on-accent) !important;
    border: none !important;
    border-radius: var(--button-radius) !important;
    padding: 0.85rem 2rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.35);
    transition: all 0.3s ease !important;
    width: 100%;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 8px 30px rgba(102, 126, 234, 0.55) !important;
    filter: brightness(1.05);
}

.stButton > button:active {
    transform: translateY(-1px) !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    border-radius: var(--card-radius);
    padding: 1.25rem;
    border: 1px solid var(--glass-border);
    transition: all 0.3s ease;
}

[data-testid="stMetric"]:hover {
    transform: scale(1.03);
    border-color: rgba(102, 126, 234, 0.4);
}

[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-primary);
}

[data-testid="stMetricLabel"] {
    color: var(--text-secondary);
    font-weight: 500;
}

/* Alert Boxes */
.alert-box {
    backdrop-filter: blur(12px);
    padding: 1rem 1.25rem;
    border-radius: 16px;
    margin: 0.75rem 0;
    border-left: 4px solid;
    color: var(--text-primary);
    font-size: 0.95rem;
    line-height: 1.5;
}

.alert-box.critical {
    background: rgba(239, 68, 68, 0.12);
    border-left-color: #ef4444;
}

.alert-box.warning {
    background: rgba(245, 158, 11, 0.12);
    border-left-color: #f59e0b;
}

.alert-box.info {
    background: rgba(59, 130, 246, 0.12);
    border-left-color: #3b82f6;
}

.alert-box.success {
    background: rgba(16, 185, 129, 0.12);
    border-left-color: #10b981;
}

.alert-box b { font-weight: 700; }
.alert-box i { font-style: italic; opacity: 0.9; }

/* DataFrames */
[data-testid="stDataFrame"] table {
    background: var(--glass-bg);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--glass-border);
}

[data-testid="stDataFrame"] th {
    background: var(--primary-gradient) !important;
    color: white !important;
    font-weight: 700;
    font-size: 0.9rem;
    padding: 0.75rem;
}

[data-testid="stDataFrame"] td {
    color: var(--text-primary);
    padding: 0.6rem 0.75rem;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    border-radius: var(--input-radius);
    font-weight: 600;
    color: var(--text-primary);
    border: 1px solid var(--glass-border);
}

.streamlit-expanderContent {
    background: var(--glass-bg);
    backdrop-filter: blur(12px);
    border-radius: 0 0 var(--input-radius) var(--input-radius);
    border: 1px solid var(--glass-border);
    border-top: none;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    border-right: 1px solid var(--glass-border);
}

/* Progress Bar */
.stProgress > div > div {
    background: var(--success-gradient);
    border-radius: 10px;
}

/* Hide footer */
footer { visibility: hidden; }

/* Responsive */
@media (max-width: 768px) {
    .header-title { font-size: 2.2rem; }
    .glass-card { padding: 1.25rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
}
</style>
""", unsafe_allow_html=True)

# ============ HEADER ============
st.markdown("""
<div class="glass-card" style="margin-bottom: 0;">
<div class="header-container">
    <h1 class="header-title">26AS Enterprise Reconciliation Pro</h1>
    <p class="header-subtitle">🤖 AI-Powered Matching • 📊 Real-Time Analytics • 🔍 TDS Rate Auditor</p>
    <p class="header-credit">Developed by <b>Abhishek Jakkula</b> • <span style="opacity:0.8">v2.0 Enhanced</span></p>
</div>
</div>
""", unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    st.markdown("### ⚙️ Engine Configuration")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        tolerance = st.number_input(
            "Mismatch Tolerance (₹)", 
            min_value=0, 
            value=CONFIG["tolerance_default"], 
            step=1,
            help="Maximum allowed difference for exact matches"
        )
    with col_s2:
        fuzzy_cutoff = st.slider(
            "Fuzzy Match Score (%)", 
            min_value=50, 
            max_value=95, 
            value=CONFIG["fuzzy_cutoff_default"], 
            step=5,
            help="Minimum similarity score for fuzzy name matching"
        )
    
    st.markdown("---")
    st.markdown("### 🧠 Smart Memory")
    st.info("Upload a Mapping Dictionary to auto-match custom vendor names across sessions.")
    
    mapping_file = st.file_uploader("📁 Upload Dictionary (CSV)", type=['csv'], label_visibility="collapsed")
    
    known_mappings = {}
    if mapping_file:
        try:
            map_df = pd.read_csv(mapping_file)
            if 'TAN of Deductor' in map_df.columns and 'Mapped Books Party' in map_df.columns:
                known_mappings = dict(zip(
                    map_df['TAN of Deductor'].astype(str).str.strip().str.upper(),
                    map_df['Mapped Books Party'].astype(str).str.strip().str.upper()
                ))
                st.success(f"✅ Loaded **{len(known_mappings)}** custom mappings!")
                logger.info(f"Loaded {len(known_mappings)} mappings from dictionary")
        except Exception as e:
            st.error(f"❌ Invalid format: {str(e)[:100]}")
    
    st.markdown("---")
    
    # Quick Stats
    st.markdown("### 📈 Quick Stats")
    st.metric("Standard TDS Rates", ", ".join(map(str, sorted(STANDARD_TDS_RATES))))
    st.metric("Max File Size", f"{CONFIG['max_file_size_mb']} MB")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============ SAMPLE FILES SECTION ============
st.markdown('<div class="zone-badge">📄 Step 1: Upload Your Files</div>', unsafe_allow_html=True)

# Create sample files
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

col_s1, col_s2 = st.columns(2)
with col_s1:
    st.download_button(
        "⬇️ Sample Books Excel", 
        books_buf, 
        "Sample_Books.xlsx", 
        use_container_width=True,
        type="secondary"
    )
with col_s2:
    st.download_button(
        "⬇️ Sample Mapping CSV", 
        dict_csv, 
        "Sample_Mapping.csv", 
        mime="text/csv", 
        use_container_width=True,
        type="secondary"
    )

st.markdown("<br>", unsafe_allow_html=True)

# ============ FILE UPLOAD ============
col_f1, col_f2 = st.columns(2)
with col_f1:
    txt_file = st.file_uploader("📄 TRACES 26AS (.txt)", type=["txt"], label_visibility="collapsed")
with col_f2:
    books_file = st.file_uploader("📊 Books Data (.xlsx/.xls)", type=["xlsx", "xls"], label_visibility="collapsed")

# File validation
file_error = False
if txt_file and txt_file.size > CONFIG["max_file_size_mb"] * 1024 * 1024:
    st.error(f"❌ 26AS file exceeds {CONFIG['max_file_size_mb']}MB limit")
    file_error = True
if books_file and books_file.size > CONFIG["max_file_size_mb"] * 1024 * 1024:
    st.error(f"❌ Books file exceeds {CONFIG['max_file_size_mb']}MB limit")
    file_error = True

# Extract metadata from 26AS
extracted_pan = "Unknown"
extracted_ay = "Unknown"
extracted_fy = "Unknown"

if txt_file and not file_error:
    raw_text = txt_file.getvalue().decode("utf-8", errors="ignore")
    
    # Enhanced pattern matching
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
                extracted_pan, extracted_fy, extracted_ay = match.groups()
                break
            elif groups == 1:
                val = match.group(1)
                if re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]', val):
                    extracted_pan = val
                elif re.fullmatch(r'\d{4}-\d{4}', val):
                    if extracted_fy == "Unknown":
                        extracted_fy = val
                    else:
                        extracted_ay = val
    
    # Fallback PAN detection
    if extracted_pan == "Unknown":
        pan_match = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', raw_text)
        if pan_match:
            extracted_pan = pan_match.group(0)
    
    # Display detected info
    st.markdown(f"""
    <div class="alert-box success">
        <b>📌 Detected:</b> PAN <b>{extracted_pan}</b> | FY <b>{extracted_fy}</b> | AY <b>{extracted_ay}</b><br>
        <i>Ensure your Books data matches this period for accurate reconciliation</i>
    </div>
    """, unsafe_allow_html=True)

# ============ PREVIEW MODE ============
preview_mode = st.checkbox(
    "🔍 Preview Mode (Process first 50 records)", 
    value=False,
    help="Enable for faster testing with large files"
)
if preview_mode:
    st.info(f"⚡ Preview mode: Only first {CONFIG['preview_limit']} records will be processed")

# ============ RUN BUTTON ============
st.markdown("<br>", unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3 = st.columns([1, 3, 1])
with col_btn2:
    run_engine = st.button(
        "🚀 LAUNCH RECONCILIATION ENGINE", 
        use_container_width=True, 
        type="primary",
        disabled=file_error or not (txt_file and books_file)
    )

# ============ CORE FUNCTIONS ============
def safe_decode(file_bytes: bytes) -> str:
    """Robust multi-encoding decoder."""
    for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode('utf-8', errors='replace')

def hash_bytes(data: bytes) -> str:
    """Generate SHA256 hash for cache keys."""
    return hashlib.sha256(data).hexdigest()

@st.cache_data(ttl=CONFIG["cache_ttl_seconds"], show_spinner="🔍 Parsing 26AS file...")
def extract_26as_detailed(content_hash: str, content: str):
    """Extract transactions from 26AS PART-I with enhanced parsing."""
    logger.info(f"Extracting 26AS data (hash: {content_hash[:12]}...)")
    
    lines = content.splitlines()
    transactions = []
    current_name = current_tan = None
    
    # Find PART-I
    part1_idx = next((i for i, l in enumerate(lines) if "PART-I - Details of Tax Deducted at Source" in l), -1)
    if part1_idx == -1:
        logger.warning("PART-I section not found")
        return pd.DataFrame()
    
    i = part1_idx + 1
    while i < len(lines):
        line = lines[i].strip()
        
        # Stop at next PART
        if line.startswith("^PART-") and "PART-I" not in line:
            break
        
        if not line:
            i += 1
            continue
        
        parts = [p.strip() for p in line.split("^") if p.strip()]
        if not parts:
            i += 1
            continue
        
        # Summary line detection
        if len(parts) >= 3 and re.fullmatch(r'\d+', parts[0]) and re.fullmatch(r'[A-Z]{4}\d{5}[A-Z]', parts[2]):
            current_name, current_tan = parts[1], parts[2]
            i += 2  # Skip header
            continue
        
        # Transaction line
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
                except (ValueError, IndexError):
                    pass
        i += 1
    
    df = pd.DataFrame(transactions)
    logger.info(f"✓ Extracted {len(df)} transactions")
    return df

@st.cache_data(ttl=CONFIG["cache_ttl_seconds"], show_spinner="🔄 Running AI matching engine...")
def run_reconciliation(txt_hash, books_hash, tolerance, fuzzy_cutoff, mapping_hash, preview):
    """Main reconciliation logic with optimized fuzzy matching."""
    logger.info("Starting reconciliation process")
    
    # Extract 26AS data
    raw_26as = extract_26as_detailed(txt_hash, safe_decode(txt_file.getvalue()))
    if raw_26as.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # Preview mode
    if preview and len(raw_26as) > CONFIG["preview_limit"]:
        raw_26as = raw_26as.head(CONFIG["preview_limit"])
    
    # Aggregate by section
    agg_section = raw_26as.groupby(['TAN of Deductor', 'Name of Deductor', 'Section'], as_index=False).agg({
        'Amount paid/credited': 'sum',
        'Total tax deducted': 'sum'
    }).rename(columns={
        'Amount paid/credited': 'Total Amount Paid / Credited',
        'Total tax deducted': 'Total TDS Deposited'
    })
    
    # TAN -> Sections lookup
    tan_sections = agg_section.groupby('TAN of Deductor')['Section'].agg(
        lambda x: ','.join(sorted(set(x)))
    ).to_dict()
    
    # Aggregate by deductor
    agg_deductor = agg_section.groupby(['TAN of Deductor', 'Name of Deductor'], as_index=False).agg({
        'Total Amount Paid / Credited': 'sum',
        'Total TDS Deposited': 'sum'
    })
    
    # Load books
    books = pd.read_excel(io.BytesIO(books_file.getvalue()))
    
    # Validate required columns
    required = ["Party Name", "Books Amount", "Books TDS"]
    missing = [c for c in required if c not in books.columns]
    if missing:
        st.error(f"❌ Books missing: {missing}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    if "TAN" not in books.columns:
        books["TAN"] = ""
    
    # Clean books data
    books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()
    books["Party Name"] = books["Party Name"].fillna("").astype(str).str.strip().str.upper()
    
    for col in ["Books Amount", "Books TDS"]:
        books[col] = pd.to_numeric(books[col], errors="coerce").fillna(0)
    
    books = books.groupby(['Party Name', 'TAN'], as_index=False)[["Books Amount", "Books TDS"]].sum()
    
    # Exact TAN matching
    agg_deductor["TAN of Deductor"] = agg_deductor["TAN of Deductor"].astype(str).str.strip().str.upper()
    exact = pd.merge(agg_deductor, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
    exact["Match Type"] = "Exact (TAN)"
    
    matched_tans = exact["TAN of Deductor"].unique()
    unmatched_26as = agg_deductor[~agg_deductor["TAN of Deductor"].isin(matched_tans)].copy()
    unmatched_books = books[~books["TAN"].isin(matched_tans)].copy()
    
    # Dictionary matching
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
    
    # Optimized fuzzy matching
    fuzzy_results = []
    matched_book_idx = set()
    book_list = [(idx, row["Party Name"]) for idx, row in unmatched_books.iterrows()]
    
    for _, row_26 in unmatched_26as.iterrows():
        name_26 = str(row_26["Name of Deductor"]).upper()
        
        if not book_list:
            result = row_26.to_dict()
            result["Match Type"] = "Missing in Books"
            fuzzy_results.append(result)
            continue
        
        # Pre-filter by first character for performance
        candidates = [(i, n) for i, n in book_list if n and n[0] == name_26[0]] if len(book_list) > 50 else book_list
        if not candidates:
            candidates = book_list
        
        match = process.extractOne(name_26, [n for _, n in candidates], scorer=fuzz.token_sort_ratio, score_cutoff=fuzzy_cutoff)
        
        if match:
            _, score, c_idx = match
            orig_idx = candidates[c_idx][0]
            if orig_idx not in matched_book_idx:
                result = row_26.to_dict()
                result.update({k: unmatched_books.loc[orig_idx][k] for k in ["Party Name", "TAN", "Books Amount", "Books TDS"]})
                result["Match Type"] = "Fuzzy Match"
                result["Fuzzy Score"] = round(score, 1)
                fuzzy_results.append(result)
                matched_book_idx.add(orig_idx)
        else:
            result = row_26.to_dict()
            result["Match Type"] = "Missing in Books"
            fuzzy_results.append(result)
    
    # Books missing in 26AS
    for idx, row in unmatched_books.iterrows():
        if idx not in matched_book_idx:
            result = row.to_dict()
            for c in ["Name of Deductor", "TAN of Deductor", "Total Amount Paid / Credited", "Total TDS Deposited", "Section"]:
                result[c] = ""
            result["Match Type"] = "Missing in 26AS"
            fuzzy_results.append(result)
    
    # Combine results
    recon = pd.concat([exact, pd.DataFrame(fuzzy_results) if fuzzy_results else pd.DataFrame()], ignore_index=True)
    
    # Fill missing columns
    for col in ["Name of Deductor", "Party Name", "TAN of Deductor", "TAN", "Section"]:
        if col not in recon.columns:
            recon[col] = ""
    
    # Unified name and TAN columns
    recon["Deductor / Party Name"] = recon["Name of Deductor"].where(
        recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""), 
        recon["Party Name"]
    )
    recon["Final TAN"] = recon["TAN of Deductor"].where(
        recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""), 
        recon["TAN"]
    )
    recon['26AS Sections'] = recon['TAN of Deductor'].map(tan_sections).fillna('')
    
    logger.info(f"✓ Reconciliation complete: {len(recon)} records")
    return recon, agg_section, raw_26as, books

def add_totals_row(df, numeric_cols):
    """Add totals row to DataFrame."""
    if df.empty:
        return df
    totals = {col: df[col].sum() if col in numeric_cols else "TOTAL" for col in df.columns}
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

# ============ MAIN EXECUTION ============
if run_engine and not file_error:
    with st.spinner("🚀 Processing with AI Engine..."):
        # Generate cache keys
        txt_h = hash_bytes(txt_file.getvalue())
        books_h = hash_bytes(books_file.getvalue())
        map_h = hash_bytes(str(known_mappings).encode()) if known_mappings else "none"
        
        try:
            recon_raw, agg_section, raw_26as, books = run_reconciliation(
                txt_h, books_h, tolerance, fuzzy_cutoff, map_h, preview_mode
            )
        except Exception as e:
            st.error(f"❌ Processing failed: {str(e)}")
            logger.exception("Reconciliation error")
            st.stop()
    
    if recon_raw.empty:
        st.error("❌ No valid data found in 26AS PART-I")
        st.stop()
    
    recon = recon_raw.copy()
    
    # ============ CALCULATIONS ============
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
    
    # Status classification
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
    
    # Final output columns
    final_recon = recon[[
        "26AS Sections", "Match Status", "Deductor / Party Name", "Final TAN",
        "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
        "Total TDS Deposited", "Books TDS", "Difference TDS", "Effective Rate 26AS (%)", "Reason for Difference"
    ]].rename(columns={"Final TAN": "TAN"})
    
    # ============ ALERTS ============
    st.markdown('<div class="glass-card critical">', unsafe_allow_html=True)
    st.markdown("### 🚨 Compliance Alerts")
    
    # TDS Rate Anomalies
    anomalies = recon[
        (recon['Effective Rate 26AS (%)'] > 0) & 
        (~recon['Effective Rate 26AS (%)'].isin(STANDARD_TDS_RATES))
    ]
    if not anomalies.empty:
        top = anomalies.nlargest(1, 'Total TDS Deposited').iloc[0]
        st.markdown(f"""
        <div class="alert-box info">
            <b>🔎 Rate Anomaly:</b> Non-standard TDS rate detected<br>
            <i>👉 <b>{top['Deductor / Party Name']}</b>: <b>{top['Effective Rate 26AS (%)']}%</b> (Expected: {', '.join(map(str, sorted(STANDARD_TDS_RATES)))}%)</i>
        </div>
        """, unsafe_allow_html=True)
    
    # Missing in Books
    miss_books = recon[recon["Match Status"] == "❌ Missing in Books"]
    if not miss_books.empty and miss_books["Total TDS Deposited"].sum() > 0:
        total = miss_books["Total TDS Deposited"].sum()
        top = miss_books.loc[miss_books["Total TDS Deposited"].idxmax()]
        st.markdown(f"""
        <div class="alert-box critical">
            <b>🚨 URGENT: Unclaimed TDS!</b> ₹{total:,.2f} in 26AS but <b>MISSING</b> in Books<br>
            <i>👉 Largest: <b>{top['Deductor / Party Name']}</b> (₹{top['Total TDS Deposited']:,.2f})</i>
        </div>
        """, unsafe_allow_html=True)
    
    # Missing in 26AS
    miss_26as = recon[recon["Match Status"] == "❌ Missing in 26AS"]
    if not miss_26as.empty and miss_26as["Books TDS"].sum() > 0:
        total = miss_26as["Books TDS"].sum()
        top = miss_26as.loc[miss_26as["Books TDS"].idxmax()]
        st.markdown(f"""
        <div class="alert-box warning">
            <b>⚠️ Compliance Risk:</b> ₹{total:,.2f} claimed in Books but <b>NOT in 26AS</b><br>
            <i>👉 Largest: <b>{top['Deductor / Party Name']}</b> (₹{top['Books TDS']:,.2f})</i>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ============ ENHANCED DASHBOARD ============
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Executive Dashboard")
    
    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    total_26as = recon['Total TDS Deposited'].sum()
    total_books = recon['Books TDS'].sum()
    net_var = total_26as - total_books
    exact_pct = (recon["Match Status"] == "✅ Exact Match").sum() / len(recon) * 100 if len(recon) > 0 else 0
    
    m1.metric("🏦 TDS in 26AS", f"₹{total_26as:,.0f}")
    m2.metric("📒 TDS in Books", f"₹{total_books:,.0f}")
    m3.metric("📐 Net Variance", f"₹{net_var:,.0f}", delta=f"₹{net_var:,.0f}", delta_color="inverse")
    m4.metric("🎯 Match Rate", f"{exact_pct:.1f}%", delta=f"{exact_pct:.1f}% exact")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Charts row
    chart1, chart2 = st.columns(2)
    
    with chart1:
        # Enhanced pie chart with interactivity
        status_counts = final_recon["Match Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        
        color_map = {
            "✅ Exact Match": "#10b981", "🔍 Fuzzy Match": "#3b82f6",
            "⚠️ Value Mismatch": "#f59e0b", "❌ Missing in Books": "#ef4444", "❌ Missing in 26AS": "#8b5cf6", "❓ Unknown": "#6b7280"
        }
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=status_counts["Status"],
            values=status_counts["Count"],
            hole=0.45,
            marker=dict(colors=[color_map.get(s, "#94a3b8") for s in status_counts["Status"]]),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>"
        )])
        fig_pie.update_layout(
            title="📊 Match Status Distribution",
            height=350,
            margin=dict(t=40, b=0, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="var(--text-primary)", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with chart2:
        # Section-wise bar chart with sorting
        section_data = []
        for _, row in recon.iterrows():
            if row['26AS Sections']:
                for sec in str(row['26AS Sections']).split(','):
                    section_data.append({'Section': sec.strip(), 'TDS': row['Total TDS Deposited']})
        
        if section_data:
            sec_df = pd.DataFrame(section_data)
            sec_summary = sec_df.groupby('Section')['TDS'].sum().reset_index().sort_values('TDS', ascending=False)
            
            fig_bar = go.Figure(data=[go.Bar(
                x=sec_summary['Section'],
                y=sec_summary['TDS'],
                marker=dict(color=sec_summary['TDS'], colorscale='Blues', showscale=True),
                hovertemplate="<b>%{x}</b><br>TDS: ₹%{y:,.0f}<extra></extra>"
            )])
            fig_bar.update_layout(
                title="📑 TDS by Section (26AS)",
                height=350,
                margin=dict(t=40, b=0, l=0, r=0),
                xaxis_title="Section",
                yaxis_title="TDS Amount (₹)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="var(--text-primary)", family="Inter")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("ℹ️ No section data available")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ============ ADVANCED ANALYTICS ============
    with st.expander("🔬 Advanced Analytics", expanded=False):
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            # Top 10 by TDS
            top_26as = final_recon[final_recon["Total TDS Deposited"] > 0].nlargest(10, "Total TDS Deposited")
            fig_top = px.bar(
                top_26as, x="Total TDS Deposited", y="Deductor / Party Name",
                orientation='h', title="🏆 Top 10 by TDS (26AS)",
                color="Total TDS Deposited", color_continuous_scale="Viridis"
            )
            fig_top.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col_a2:
            # Variance analysis
            variance_data = final_recon[final_recon["Difference TDS"] != 0].copy()
            if not variance_data.empty:
                variance_data["Abs Variance"] = variance_data["Difference TDS"].abs()
                fig_var = px.scatter(
                    variance_data.nlargest(20, "Abs Variance"),
                    x="Total TDS Deposited", y="Books TDS",
                    size="Abs Variance", color="Match Status",
                    hover_name="Deductor / Party Name",
                    title="📉 Variance Analysis (Top 20)",
                    color_discrete_map={k: v for k, v in color_map.items() if k in variance_data["Match Status"].unique()}
                )
                fig_var.add_trace(go.Scatter(
                    x=[0, variance_data["Total TDS Deposited"].max()],
                    y=[0, variance_data["Total TDS Deposited"].max()],
                    mode='lines', line=dict(dash='dash', color='gray'),
                    name='Perfect Match Line', showlegend=True
                ))
                fig_var.update_layout(height=400)
                st.plotly_chart(fig_var, use_container_width=True)
            else:
                st.success("✅ No variances detected - all records match perfectly!")
    
    # ============ DATA TABLES ============
    with st.expander("📋 View Reconciliation Data", expanded=True):
        # Filter controls
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            status_filter = st.multiselect(
                "Filter by Status", 
                options=final_recon["Match Status"].unique(),
                default=final_recon["Match Status"].unique()
            )
        with col_f2:
            min_tds = st.number_input("Min TDS (₹)", min_value=0, value=0, step=1000)
        with col_f3:
            search_term = st.text_input("🔍 Search Party/TAN", placeholder="Type to filter...")
        
        # Apply filters
        filtered = final_recon[
            final_recon["Match Status"].isin(status_filter) &
            (final_recon["Total TDS Deposited"] >= min_tds)
        ]
        if search_term:
            filtered = filtered[
                filtered["Deductor / Party Name"].str.contains(search_term, case=False, na=False) |
                filtered["TAN"].str.contains(search_term, case=False, na=False)
            ]
        
        # Display table
        st.dataframe(
            filtered.style.format({
                "Total Amount Paid / Credited": "₹{:,.0f}",
                "Books Amount": "₹{:,.0f}",
                "Difference Amount": "₹{:+,.0f}",
                "Total TDS Deposited": "₹{:,.0f}",
                "Books TDS": "₹{:,.0f}",
                "Difference TDS": "₹{:+,.0f}",
                "Effective Rate 26AS (%)": "{:.2f}%"
            }).background_gradient(
                subset=["Difference TDS"], cmap="RdYlGn_r", vmin=-10000, vmax=10000
            ),
            use_container_width=True,
            height=400
        )
    
    # ============ EXCEL EXPORT ============
    output = io.BytesIO()
    last_row = len(final_recon) + 3
    
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book
        
        # Formats
        fmt_title = wb.add_format({"bold": True, "font_size": 16, "bg_color": "#1e1e3f", "font_color": "#667eea", "align": "center"})
        fmt_header = wb.add_format({"bold": True, "bg_color": "#4f46e5", "font_color": "white", "border": 1, "align": "center"})
        fmt_number = wb.add_format({"num_format": "#,##0.00"})
        fmt_currency = wb.add_format({"num_format": '"₹"#,##0.00'})
        fmt_percent = wb.add_format({"num_format": "0.00%"})
        fmt_total = wb.add_format({"bold": True, "bg_color": "#e0e7ff", "border": 1, "num_format": '"₹"#,##0.00'})
        
        # Dashboard sheet
        dash = wb.add_worksheet("Dashboard")
        dash.merge_range("A1:K2", f"26AS RECONCILIATION REPORT | FY: {extracted_fy} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_title)
        
        # Summary metrics
        metrics = [
            ("Total Records", len(final_recon)),
            ("Exact Matches", (final_recon["Match Status"] == "✅ Exact Match").sum()),
            ("Total TDS (26AS)", total_26as),
            ("Total TDS (Books)", total_books),
            ("Net Variance", net_var),
            ("Match Rate %", f"{exact_pct:.1f}%")
        ]
        for i, (label, value) in enumerate(metrics):
            dash.write(i+3, 0, label, wb.add_format({"bold": True}))
            dash.write(i+3, 1, value)
        
        # Status breakdown
        dash.write(10, 0, "Status Breakdown", fmt_header)
        for i, (status, count) in enumerate(status_counts.values):
            dash.write(11+i, 0, status)
            dash.write(11+i, 1, count)
        
        # Reconciliation sheet
        recon_sheet = wb.add_worksheet("Reconciliation")
        final_recon.to_excel(writer, sheet_name="Reconciliation", startrow=2, index=False, header=False)
        
        # Format headers
        for col, name in enumerate(final_recon.columns):
            recon_sheet.write(1, col, name, fmt_header)
            if "Amount" in name or "TDS" in name:
                recon_sheet.set_column(col, col, None, fmt_currency)
            elif "Rate" in name:
                recon_sheet.set_column(col, col, None, fmt_percent)
            else:
                recon_sheet.set_column(col, col, max(15, len(name) + 2))
        
        # Add totals row
        for col, name in enumerate(final_recon.columns):
            if name in ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS", "Difference Amount", "Difference TDS"]:
                col_letter = chr(65 + col)
                recon_sheet.write_formula(0, col, f'=SUBTOTAL(9,{col_letter}3:{col_letter}{last_row})', fmt_total)
        
        recon_sheet.autofilter(1, 0, last_row, len(final_recon.columns)-1)
        
        # Additional sheets
        if not agg_section.empty:
            agg_sheet = wb.add_worksheet("26AS by Section")
            agg_with_total = add_totals_row(agg_section, ["Total Amount Paid / Credited", "Total TDS Deposited"])
            agg_with_total.to_excel(writer, sheet_name="26AS by Section", startrow=1, index=False, header=False)
            for col in range(len(agg_with_total.columns)):
                if "Amount" in agg_with_total.columns[col] or "TDS" in agg_with_total.columns[col]:
                    agg_sheet.set_column(col, col, None, fmt_currency)
        
        if not raw_26as.empty:
            raw_sheet = wb.add_worksheet("26AS Raw Data")
            raw_26as.to_excel(writer, sheet_name="26AS Raw Data", index=False)
        
        books.to_excel(writer, sheet_name="Books Raw", index=False)
    
    output.seek(0)
    
    # Download button
    st.markdown('<div class="glass-card success">', unsafe_allow_html=True)
    fy_tag = extracted_fy.replace('-', '_') if extracted_fy != 'Unknown' else 'Latest'
    st.download_button(
        "⬇️ Download Complete Excel Report",
        output,
        f"26AS_Recon_{fy_tag}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        use_container_width=True,
        type="primary"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.success("✅ Reconciliation completed successfully! Review alerts and download your report.")

# ============ FOOTER ============
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; padding:2rem; opacity:0.85;">
    <div style="font-weight:700; font-size:1.1rem;">✨ 26AS Enterprise Reconciliation Pro ✨</div>
    <div style="margin:0.5rem 0;">
        <span>👨‍💻 Developed by <b>Abhishek Jakkula</b></span> • 
        <span>📧 <a href="mailto:jakkulaabhishek5@gmail.com" style="color:#667eea;text-decoration:none">jakkulaabhishek5@gmail.com</a></span>
    </div>
    <div style="font-size:0.9rem; opacity:0.9;">
        🔐 Secure • ⚡ Fast • 🎯 Accurate • 📱 Responsive
    </div>
</div>
""", unsafe_allow_html=True)
