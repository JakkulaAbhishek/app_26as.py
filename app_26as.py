import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
import hashlib
import logging
from rapidfuzz import process, fuzz
from datetime import datetime

# ============ CONFIGURATION & CONSTANTS ============
STANDARD_TDS_RATES = {1.0, 2.0, 5.0, 10.0, 20.0, 30.0}
TOLERANCE_DEFAULT = 10
FUZZY_CUTOFF_DEFAULT = 70
MAX_FILE_SIZE_MB = 50
CACHE_TTL_SECONDS = 3600
PREVIEW_LIMIT_DEFAULT = 50

# ============ LOGGING SETUP ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ STREAMLIT CONFIG ============
st.set_page_config(page_title="26AS Enterprise Reconciliation", layout="wide", page_icon="📊")

# ============ ROBUST DECODING FUNCTION ============
def safe_decode(file_bytes: bytes) -> str:
    """Try multiple encodings to safely decode file content."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            return file_bytes.decode(enc)
            logger.info(f"Successfully decoded file using {enc}")
        except UnicodeDecodeError:
            continue
    logger.warning("All encodings failed, using utf-8 with replace")
    return file_bytes.decode('utf-8', errors='replace')

# ============ HASHING FOR CACHE KEYS ============
def hash_bytes(data: bytes) -> str:
    """Generate SHA256 hash for bytes to use as cache key."""
    return hashlib.sha256(data).hexdigest()

# ============ GLASSMORPHIC UI CSS ============
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

:root {
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --card-bg: rgba(255, 255, 255, 0.25);
    --card-border: rgba(255, 255, 255, 0.18);
    --text-primary: #2d3748;
    --text-secondary: #4a5568;
    --accent: #667eea;
    --accent-light: #9f7aea;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: rgba(17, 25, 40, 0.75);
        --card-border: rgba(255, 255, 255, 0.1);
        --text-primary: #f7fafc;
        --text-secondary: #e2e8f0;
        --accent: #9f7aea;
        --accent-light: #b794f4;
    }
    .stApp {
        background: #0f172a;
    }
}

@media (prefers-reduced-motion: reduce) {
    .stApp {
        animation: none !important;
        background: var(--bg-gradient) !important;
    }
    .glass-card {
        transition: none !important;
    }
    .glass-card:hover {
        transform: none !important;
    }
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
    background-size: 400% 400%;
    animation: gradient 15s ease infinite;
    min-height: 100vh;
}

@keyframes gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.glass-card {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-radius: 20px;
    border: 1px solid var(--card-border);
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
}

.header-title {
    font-weight: 800;
    font-size: 3.5rem;
    text-align: center;
    background: linear-gradient(90deg, #fff, #e0e7ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    line-height: 1.2;
    letter-spacing: -0.02em;
}

.header-sub {
    font-size: 1.2rem;
    font-weight: 600;
    text-align: center;
    color: var(--text-primary);
    opacity: 0.9;
    margin-top: 6px;
}

.dev-credit {
    font-size: 1rem;
    text-align: center;
    margin-top: 8px;
    color: var(--text-secondary);
}

.dev-credit b {
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.zone {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    padding: 16px;
    border-radius: 50px;
    border: 1px solid var(--card-border);
    text-align: center;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 18px;
    font-size: 1.1rem;
    letter-spacing: 0.5px;
}

[data-testid="stFileUploader"] {
    background: var(--card-bg) !important;
    backdrop-filter: blur(10px);
    border-radius: 15px !important;
    border: 2px dashed var(--accent-light) !important;
    padding: 1.2em !important;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: rgba(255,255,255,0.15) !important;
}

.stButton>button,
.stDownloadButton>button {
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
    color: white !important;
    border-radius: 50px;
    padding: 12px 30px;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    text-transform: uppercase;
    letter-spacing: 1px;
    width: 100%;
}

.stButton>button:hover,
.stDownloadButton>button:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
}

[data-testid="stMetric"] {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 20px;
    border: 1px solid var(--card-border);
    transition: transform 0.3s ease;
}

[data-testid="stMetric"]:hover {
    transform: scale(1.02);
}

[data-testid="stMetricValue"] {
    font-weight: 800;
    font-size: 1.8rem;
    color: var(--text-primary);
}

[data-testid="stMetricLabel"] {
    color: var(--text-secondary);
}

.alert-box-red {
    background: rgba(239, 68, 68, 0.15);
    backdrop-filter: blur(10px);
    border-left: 5px solid var(--danger);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.alert-box-yellow {
    background: rgba(245, 158, 11, 0.15);
    backdrop-filter: blur(10px);
    border-left: 5px solid var(--warning);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.alert-box-blue {
    background: rgba(37, 99, 235, 0.15);
    backdrop-filter: blur(10px);
    border-left: 5px solid var(--accent);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.alert-box-green {
    background: rgba(16, 185, 129, 0.15);
    backdrop-filter: blur(10px);
    border-left: 5px solid var(--success);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

[data-testid="stDataFrame"] {
    background: transparent;
}

[data-testid="stDataFrame"] table {
    background: var(--card-bg);
    backdrop-filter: blur(5px);
    border-radius: 15px;
    overflow: hidden;
}

[data-testid="stDataFrame"] th {
    background: var(--accent) !important;
    color: white !important;
    font-weight: 600;
}

[data-testid="stDataFrame"] td {
    color: var(--text-primary);
}

.streamlit-expanderHeader {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    font-weight: 600;
    color: var(--text-primary);
}

.streamlit-expanderContent {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border-radius: 0 0 15px 15px;
    border-top: none;
}

.css-1d391kg, .css-12oz5g7 {
    background: var(--card-bg) !important;
    backdrop-filter: blur(10px);
}

footer {visibility: hidden;}

/* Progress bar styling */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-light));
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="glass-card">', unsafe_allow_html=True)

# ============ HEADER ============
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <div class="header-title">26AS Enterprise Reconciliation</div>
    <div class="header-sub">RapidFuzz AI | Smart Memory | TDS Rate Auditor</div>
    <div class="dev-credit">Developed by <b>Abhishek Jakkula</b></div>
</div>
""", unsafe_allow_html=True)

# ============ SIDEBAR SETTINGS ============
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    tolerance = st.number_input("Mismatch Tolerance (₹)", min_value=0, value=TOLERANCE_DEFAULT, step=1)
    fuzzy_cutoff = st.slider("Fuzzy Match Score Cutoff (%)", min_value=50, max_value=95, value=FUZZY_CUTOFF_DEFAULT, step=5)
    
    st.markdown("---")
    st.markdown("### 🧠 AI Smart Memory")
    st.info("Upload a previously saved Mapping Dictionary to auto-match custom vendor names.")
    mapping_file = st.file_uploader("Upload Dictionary (CSV)", type=['csv'])

    known_mappings = {}
    if mapping_file:
        try:
            map_df = pd.read_csv(mapping_file)
            if 'TAN of Deductor' in map_df.columns and 'Mapped Books Party' in map_df.columns:
                known_mappings = dict(zip(
                    map_df['TAN of Deductor'].astype(str).str.strip().str.upper(),
                    map_df['Mapped Books Party'].astype(str).str.strip().str.upper()
                ))
                st.success(f"✅ Loaded {len(known_mappings)} custom mappings!")
                logger.info(f"Loaded {len(known_mappings)} mappings from dictionary")
        except Exception as e:
            st.error(f"❌ Invalid dictionary format: {str(e)}")
            logger.error(f"Failed to load mapping file: {e}")

# ============ SAMPLE TEMPLATES ============
st.markdown('<div class="zone">📄 Step 1: Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd", "XYZ Corp"],
    "TAN": ["HYDA00000A", ""],
    "Books Amount": [100000, 50000],
    "Books TDS": [10000, 5000]
})
books_buf = io.BytesIO()
sample_books.to_excel(books_buf, index=False, engine='openpyxl')
books_buf.seek(0)

sample_dict = pd.DataFrame({
    "TAN of Deductor": ["HYDA00000A"],
    "Mapped Books Party": ["ABC Pvt Ltd"]
})
dict_csv = sample_dict.to_csv(index=False).encode('utf-8')

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.download_button("⬇ Download Sample Books Excel", books_buf, "Sample_Books.xlsx", use_container_width=True)
with col_t2:
    st.download_button("⬇ Download Sample Mapping Dictionary", dict_csv, "Sample_Mapping.csv", mime="text/csv", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============ FILE UPLOAD WITH VALIDATION ============
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx", "xls"])

# File size validation
if txt_file and txt_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
    st.error(f"❌ 26AS file too large! Maximum allowed: {MAX_FILE_SIZE_MB}MB")
    st.stop()
if books_file and books_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
    st.error(f"❌ Books file too large! Maximum allowed: {MAX_FILE_SIZE_MB}MB")
    st.stop()

# Extract metadata from 26AS file
extracted_pan = "Unknown"
extracted_ay = "Unknown"
extracted_fy = "Unknown"

if txt_file:
    raw_text = safe_decode(txt_file.getvalue())

    patterns = [
        r'\d{2}-\d{2}-\d{4}\^([A-Z]{5}\d{4}[A-Z])\^[^\^]*\^(\d{4}-\d{4})\^(\d{4}-\d{4})\^?',
        r'PAN[:\s]*([A-Z]{5}\d{4}[A-Z])',
        r'Financial\s+Year[:\s]*(\d{4}-\d{4})',
        r'Assessment\s+Year[:\s]*(\d{4}-\d{4})'
    ]

    for pat in patterns:
        match = re.search(pat, raw_text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 1:
                grp = groups[0]
                if re.fullmatch(r'[A-Z]{5}\d{4}[A-Z]', grp):
                    extracted_pan = grp
                elif re.fullmatch(r'\d{4}-\d{4}', grp):
                    if extracted_fy == "Unknown":
                        extracted_fy = grp
                    else:
                        extracted_ay = grp
            else:
                extracted_pan, extracted_fy, extracted_ay = groups[0], groups[1], groups[2]
            break

    if extracted_pan == "Unknown":
        pan_match = re.search(r'([A-Z]{5}\d{4}[A-Z])', raw_text)
        if pan_match:
            extracted_pan = pan_match.group(1)

    st.markdown(f"""
    <div class="alert-box-green" style="text-align:center;">
        <b>📌 Data Detected:</b> You are reconciling PAN <b>{extracted_pan}</b> for Financial Year <b>{extracted_fy}</b> (AY {extracted_ay}). Please ensure your Books match this period!
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============ PREVIEW MODE OPTION ============
preview_mode = st.checkbox("🔍 Preview Mode (Process first 50 records only)", value=False)
if preview_mode:
    st.info(f"⚡ Preview mode enabled: Only first {PREVIEW_LIMIT_DEFAULT} records will be processed for faster testing")

# ============ RUN BUTTON ============
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    run_engine = st.button("🚀 RUN ENTERPRISE ENGINE", use_container_width=True, type="primary")

# ============ EXTRACTION FUNCTION (CACHED) ============
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="🔍 Parsing 26AS file...")
def extract_26as_detailed_cached(content_hash: str, content: str):
    """
    Extract transaction-level details from 26AS PART-I.
    Returns DataFrame with columns for reconciliation.
    """
    logger.info(f"Starting 26AS extraction (hash: {content_hash[:16]}...)")
    lines = content.splitlines()
    transactions = []
    current_name = None
    current_tan = None
    in_part1 = False

    # Find start of PART-I
    part1_start = -1
    for i, line in enumerate(lines):
        if "PART-I - Details of Tax Deducted at Source" in line:
            part1_start = i
            break
    
    if part1_start == -1:
        logger.warning("PART-I section not found in 26AS file")
        return pd.DataFrame()

    # Process lines from part1_start onward
    i = part1_start + 1
    while i < len(lines):
        line = lines[i]
        
        # Stop when we hit another PART section
        if line.startswith("^PART-") and "PART-I" not in line:
            break

        if not line.strip():
            i += 1
            continue

        parts = [p.strip() for p in line.split("^") if p.strip()]
        if not parts:
            i += 1
            continue

        # Check if it's a summary line
        is_summary = (len(parts) >= 3 and
                      re.fullmatch(r'\d+', parts[0]) and
                      re.fullmatch(r'[A-Z]{4}[0-9]{5}[A-Z]', parts[2]))
        
        if is_summary:
            current_name = parts[1]
            current_tan = parts[2]
            i += 2  # Skip header line after summary
            continue

        # Process transaction line
        if current_name and current_tan and len(parts) >= 9:
            if (re.fullmatch(r'\d+', parts[0]) and re.fullmatch(r'\d+[A-Z]+', parts[1])):
                try:
                    trans = {
                        "Sl. No.": int(parts[0]),
                        "Section": parts[1],
                        "Name of Deductor": current_name,
                        "TAN of Deductor": current_tan,
                        "Amount paid/credited": float(parts[6].replace(",", "")),
                        "Date of Payment/Credit": parts[2],
                        "Total tax deducted": float(parts[7].replace(",", "")),
                        "Amount claimed for this year": 0.0,
                        "C/F Tax": 0.0
                    }
                    transactions.append(trans)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipped malformed transaction line: {e}")
        i += 1

    df = pd.DataFrame(transactions)
    logger.info(f"Extracted {len(df)} transactions from 26AS")
    return df

# ============ RECONCILIATION ENGINE (CACHED) ============
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="🔄 Running reconciliation engine...")
def run_reconciliation_cached(
    txt_hash: str, books_hash: str, tolerance: float, 
    fuzzy_cutoff: int, mapping_hash: str, preview: bool
):
    """Cached reconciliation function with hash-based cache keys."""
    logger.info("Starting reconciliation process")
    
    # Re-extract 26AS data (will use cache)
    raw_26as_detailed = extract_26as_detailed_cached(txt_hash, safe_decode(txt_file.getvalue()))
    
    if raw_26as_detailed.empty:
        logger.error("No transaction data found in 26AS")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Preview mode limit
    if preview and len(raw_26as_detailed) > PREVIEW_LIMIT_DEFAULT:
        raw_26as_detailed = raw_26as_detailed.head(PREVIEW_LIMIT_DEFAULT)
        logger.info(f"Preview mode: Limited to {PREVIEW_LIMIT_DEFAULT} records")

    # 1. Section-wise aggregated 26AS
    agg_26as_section = raw_26as_detailed.groupby(
        ['TAN of Deductor', 'Name of Deductor', 'Section'], as_index=False
    ).agg({
        'Amount paid/credited': 'sum',
        'Total tax deducted': 'sum'
    }).rename(columns={
        'Amount paid/credited': 'Total Amount Paid / Credited',
        'Total tax deducted': 'Total TDS Deposited'
    })

    # Build TAN to sections lookup
    tan_to_sections = agg_26as_section.groupby('TAN of Deductor')['Section'].agg(
        lambda x: ','.join(sorted(set(x)))
    ).to_dict()

    # 2. Deductor-level aggregated 26AS
    agg_26as_deductor = agg_26as_section.groupby(
        ['TAN of Deductor', 'Name of Deductor'], as_index=False
    ).agg({
        'Total Amount Paid / Credited': 'sum',
        'Total TDS Deposited': 'sum'
    })

    # Load and validate books
    try:
        books = pd.read_excel(io.BytesIO(books_file.getvalue()))
    except Exception as e:
        logger.error(f"Failed to read books file: {e}")
        raise

    REQUIRED_BOOKS_COLS = ["Party Name", "Books Amount", "Books TDS"]
    missing_cols = [col for col in REQUIRED_BOOKS_COLS if col not in books.columns]
    if missing_cols:
        logger.error(f"Books file missing columns: {missing_cols}")
        st.error(f"❌ Books file missing required columns: {missing_cols}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Ensure TAN column exists
    if "TAN" not in books.columns:
        books["TAN"] = ""
    
    # Clean and aggregate books data
    books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()
    books["Party Name"] = books["Party Name"].fillna("").astype(str).str.strip().str.upper()
    
    numeric_cols = ["Books Amount", "Books TDS"]
    for col in numeric_cols:
        books[col] = pd.to_numeric(books[col], errors="coerce").fillna(0)
    
    books = books.groupby(['Party Name', 'TAN'], as_index=False)[numeric_cols].sum()

    # Exact match by TAN
    agg_26as_deductor["TAN of Deductor"] = agg_26as_deductor["TAN of Deductor"].astype(str).str.strip().str.upper()
    exact_match = pd.merge(agg_26as_deductor, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
    exact_match["Match Type"] = "Exact (TAN)"

    matched_tans = exact_match["TAN of Deductor"].unique()
    unmatched_26as = agg_26as_deductor[~agg_26as_deductor["TAN of Deductor"].isin(matched_tans)].copy()
    unmatched_books = books[~books["TAN"].isin(matched_tans)].copy()

    # Dictionary mappings
    if known_mappings:
        for tan_26, target_bk_name in known_mappings.items():
            row_26 = unmatched_26as[unmatched_26as["TAN of Deductor"] == tan_26]
            if row_26.empty:
                continue
            row_bk = unmatched_books[unmatched_books["Party Name"] == target_bk_name]
            if row_bk.empty:
                continue
            
            merged = row_26.iloc[0].to_dict()
            bk_row = row_bk.iloc[0].to_dict()
            merged.update({k: bk_row[k] for k in ["Party Name", "TAN", "Books Amount", "Books TDS"]})
            merged["Match Type"] = "Dictionary Match"
            exact_match = pd.concat([exact_match, pd.DataFrame([merged])], ignore_index=True)
            
            unmatched_26as = unmatched_26as[unmatched_26as["TAN of Deductor"] != tan_26]
            unmatched_books = unmatched_books[unmatched_books["Party Name"] != target_bk_name]

    # Fuzzy matching with optimized approach
    fuzzy_records = []
    matched_book_indices = set()
    book_items = [(idx, row["Party Name"]) for idx, row in unmatched_books.iterrows()]

    for idx_26, row_26 in unmatched_26as.iterrows():
        name_26 = str(row_26["Name of Deductor"]).upper()
        
        if not book_items:
            combined = row_26.to_dict()
            combined["Match Type"] = "Missing in Books"
            fuzzy_records.append(combined)
            continue
        
        # Pre-filter candidates by first letter for performance
        if len(book_items) > 100:
            candidates = [(idx, name) for idx, name in book_items if name and name[0] == name_26[0]]
            if not candidates:
                candidates = book_items  # Fallback if no matches
        else:
            candidates = book_items
        
        if not candidates:
            combined = row_26.to_dict()
            combined["Match Type"] = "Missing in Books"
            fuzzy_records.append(combined)
            continue
            
        result = process.extractOne(
            name_26, 
            [name for _, name in candidates], 
            scorer=fuzz.token_sort_ratio, 
            score_cutoff=fuzzy_cutoff
        )
        
        if result:
            best_match_str, best_score, best_idx_in_list = result
            best_orig_idx = candidates[best_idx_in_list][0]
            
            # Only process if not already matched
            if best_orig_idx not in matched_book_indices:
                combined = row_26.to_dict()
                bk_row = unmatched_books.loc[best_orig_idx].to_dict()
                combined.update({k: bk_row[k] for k in ["Party Name", "TAN", "Books Amount", "Books TDS"]})
                combined["Match Type"] = "Fuzzy Match"
                fuzzy_records.append(combined)
                matched_book_indices.add(best_orig_idx)
        else:
            combined = row_26.to_dict()
            combined["Match Type"] = "Missing in Books"
            fuzzy_records.append(combined)

    # Add books missing in 26AS
    for idx, row in unmatched_books.iterrows():
        if idx not in matched_book_indices:
            combined = row.to_dict()
            for col in ["Name of Deductor", "TAN of Deductor", "Total Amount Paid / Credited", "Total TDS Deposited", "Section"]:
                combined[col] = "" if col != "Section" else ""
            combined["Match Type"] = "Missing in 26AS"
            fuzzy_records.append(combined)

    fuzzy_df = pd.DataFrame(fuzzy_records) if fuzzy_records else pd.DataFrame()
    recon = pd.concat([exact_match, fuzzy_df], ignore_index=True)

    # Fill missing columns
    for col in ["Name of Deductor", "Party Name", "TAN of Deductor", "TAN", "Section"]:
        if col not in recon.columns:
            recon[col] = ""

    recon["Deductor / Party Name"] = np.where(
        recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""), 
        recon["Name of Deductor"], 
        recon["Party Name"]
    )
    recon["Final TAN"] = np.where(
        recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""), 
        recon["TAN of Deductor"], 
        recon["TAN"]
    )

    # Add sections column from lookup
    recon['26AS Sections'] = recon['TAN of Deductor'].map(tan_to_sections).fillna('')

    logger.info(f"Reconciliation complete: {len(recon)} records processed")
    return recon, agg_26as_section, raw_26as_detailed, books

# ============ HELPER: ADD TOTALS ROW ============
def add_totals_row(df, numeric_cols):
    """Append a totals row to a DataFrame."""
    if df.empty:
        return df
    totals = {}
    for col in df.columns:
        if col in numeric_cols:
            totals[col] = df[col].sum()
        else:
            totals[col] = "TOTAL"
    totals_df = pd.DataFrame([totals])
    return pd.concat([df, totals_df], ignore_index=True)

# ============ MAIN EXECUTION ============
if run_engine:
    if not txt_file or not books_file:
        st.warning("⚠️ Please upload both the 26AS and Books files to proceed.")
    else:
        with st.spinner("🚀 Running High-Speed AI Engine & Rate Auditor..."):
            # Generate cache keys
            txt_hash = hash_bytes(txt_file.getvalue())
            books_hash = hash_bytes(books_file.getvalue())
            mapping_hash = hash_bytes(str(known_mappings).encode()) if known_mappings else "none"
            
            try:
                raw_recon, agg_26as_section, raw_26as_detailed, books = run_reconciliation_cached(
                    txt_hash, books_hash, tolerance, fuzzy_cutoff, mapping_hash, preview_mode
                )
            except Exception as e:
                st.error(f"❌ Processing error: {str(e)}")
                logger.exception("Reconciliation failed")
                st.stop()

        if raw_recon.empty:
            st.error("❌ No valid transaction data found in PART-I of the 26AS text file.")
            st.stop()

        recon = raw_recon.copy()

        # Core Calculations
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
        conditions_status = [
            (recon["Match Type"].isin(["Exact (TAN)", "Dictionary Match"])) & (diff_tds <= tolerance),
            (recon["Match Type"].isin(["Exact (TAN)", "Dictionary Match"])) & (diff_tds > tolerance),
            (recon["Match Type"] == "Fuzzy Match") & (diff_tds <= tolerance),
            (recon["Match Type"] == "Fuzzy Match") & (diff_tds > tolerance),
            (recon["Match Type"] == "Missing in Books"),
            (recon["Match Type"] == "Missing in 26AS")
        ]
        statuses = ["Exact Match", "Value Mismatch", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
        reasons = ["Matched perfectly", "TDS value mismatch", "Matched ignoring name formatting", "TDS value mismatch", "Not recorded in Books", "Not reflected in 26AS"]

        recon["Match Status"] = np.select(conditions_status, statuses, default="Unknown")
        recon["Reason for Difference"] = np.select(conditions_status, reasons, default="Unknown")

        # Build final reconciliation DataFrame
        final_recon = recon[[
            "26AS Sections", "Match Status", "Deductor / Party Name", "Final TAN",
            "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
            "Total TDS Deposited", "Books TDS", "Difference TDS", "Effective Rate 26AS (%)", "Reason for Difference"
        ]].rename(columns={"Final TAN": "TAN"})

        # ============ ALERTS ============
        st.markdown("### 🚨 Compliance & Anomaly Alerts")

        # TDS Rate Anomaly
        anomalies = recon[
            (recon['Effective Rate 26AS (%)'] > 0) & 
            (~recon['Effective Rate 26AS (%)'].isin(STANDARD_TDS_RATES))
        ]
        if not anomalies.empty:
            top_anomaly = anomalies.nlargest(1, 'Total TDS Deposited').iloc[0]
            st.markdown(f"""
            <div class="alert-box-blue">
                <b>🔎 TDS Rate Anomaly Detected:</b> Non-standard deduction rates identified.<br>
                <span style="color: #7dd3fc; font-size: 0.95rem;"><i>👉 <b>{top_anomaly['Deductor / Party Name']}</b> deducted TDS at an effective rate of <b>{top_anomaly['Effective Rate 26AS (%)']}%</b>.</i></span>
            </div>
            """, unsafe_allow_html=True)

        # Missing in Books
        miss_in_books = recon[recon["Match Status"] == "Missing in Books"]
        if not miss_in_books.empty and miss_in_books["Total TDS Deposited"].sum() > 0:
            top_missed = miss_in_books.loc[miss_in_books["Total TDS Deposited"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-red">
                <b>URGENT: Unclaimed TDS Leakage!</b> ₹ {miss_in_books["Total TDS Deposited"].sum():,.2f} is in 26AS but completely <b>MISSING</b> in books.<br>
                <span style="color: #fca5a5; font-size: 0.95rem;"><i>👉 Top Missing Party: <b>{top_missed['Deductor / Party Name']}</b> (₹ {top_missed['Total TDS Deposited']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)

        # Missing in 26AS
        miss_in_26as = recon[recon["Match Status"] == "Missing in 26AS"]
        if not miss_in_26as.empty and miss_in_26as["Books TDS"].sum() > 0:
            top_excess = miss_in_26as.loc[miss_in_26as["Books TDS"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-yellow">
                <b>COMPLIANCE RISK:</b> ₹ {miss_in_26as["Books TDS"].sum():,.2f} of TDS is claimed in Books but <b>NOT uploaded in 26AS</b>.<br>
                <span style="color: #fcd34d; font-size: 0.95rem;"><i>👉 Top Unreflected Party: <b>{top_excess['Deductor / Party Name']}</b> (₹ {top_excess['Books TDS']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)

        # ============ DASHBOARD ============
        st.markdown("---")
        st.markdown("### 📊 Live Summary Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total TDS in 26AS", f"₹ {recon['Total TDS Deposited'].sum():,.2f}")
        m2.metric("Total TDS in Books", f"₹ {recon['Books TDS'].sum():,.2f}")
        net_diff = recon['Total TDS Deposited'].sum() - recon['Books TDS'].sum()
        m3.metric("Net Variance", f"₹ {net_diff:,.2f}", delta=f"₹ {net_diff:,.2f}", delta_color="inverse")

        st.markdown("### 📈 Reconciliation Analytics")
        c1, c2 = st.columns(2)

        with c1:
            status_counts = final_recon["Match Status"].value_counts().reset_index()
            status_counts.columns = ["Match Status", "Count"]
            color_map = {
                "Exact Match": "#10b981", "Fuzzy Match": "#38bdf8",
                "Value Mismatch": "#ef4444", "Missing in Books": "#f97316", "Missing in 26AS": "#8b5cf6"
            }
            fig_status = px.pie(
                status_counts, names="Match Status", values="Count", 
                title="Match Status Distribution", hole=0.4, 
                color="Match Status", color_discrete_map=color_map
            )
            fig_status.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)", 
                font=dict(color="#f8fafc", family="Poppins")
            )
            st.plotly_chart(fig_status, use_container_width=True)

        with c2:
            # Section-wise bar chart
            section_data = []
            for _, row in recon.iterrows():
                if row['26AS Sections'] and row['26AS Sections'] != "":
                    for sec in row['26AS Sections'].split(','):
                        section_data.append({
                            'Section': sec.strip(), 
                            'Total TDS Deposited': row['Total TDS Deposited']
                        })
            
            if section_data:
                section_df = pd.DataFrame(section_data)
                section_summary = section_df.groupby('Section')['Total TDS Deposited'].sum().reset_index()
                fig_sec = px.bar(
                    section_summary, x='Section', y='Total TDS Deposited', 
                    title="TDS Deposited by Section (26AS)"
                )
                fig_sec.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", 
                    paper_bgcolor="rgba(0,0,0,0)", 
                    font=dict(color="#f8fafc", family="Poppins")
                )
                st.plotly_chart(fig_sec, use_container_width=True)
            else:
                st.info("ℹ️ No section data to display.")

        # ============ EXCEL EXPORT ============
        output = io.BytesIO()
        actual_last_row = len(final_recon) + 2  # header row + data start at row 2
        
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            
            # Formats
            brand_format = workbook.add_format({
                "bold": True, "font_size": 18, "bg_color": "#0f172a", 
                "font_color": "#38bdf8", "align": "center", "valign": "vcenter"
            })
            dev_format = workbook.add_format({
                "italic": True, "font_size": 10, "bg_color": "#0f172a", 
                "font_color": "#94a3b8", "align": "center"
            })
            fmt_dark_blue_white = workbook.add_format({
                "bold": True, "bg_color": "#0052cc", "font_color": "white", 
                "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"
            })
            fmt_subtotal = workbook.add_format({
                "bold": True, "bg_color": "#f2f2f2", "border": 1, "num_format": "#,##0.00"
            })
            fmt_number = workbook.add_format({"num_format": "#,##0.00"})

            # Dashboard sheet
            dash = workbook.add_worksheet("Dashboard")
            dash.hide_gridlines(2)
            fy_title = f"(FY: {extracted_fy})" if extracted_fy != "Unknown" else ""
            dash.merge_range("A1:M2", f"26AS ENTERPRISE RECON - EXECUTIVE SUMMARY {fy_title}", brand_format)
            dash.merge_range("A3:M3", f"Developed by ABHISHEK JAKKULA | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", dev_format)

            dash.write_row("B5", ["Match Status", "Record Count", "TDS Impact (26AS)", "TDS Impact (Books)"], fmt_dark_blue_white)
            dash.set_column('B:B', 25)
            dash.set_column('C:E', 18)

            dashboard_statuses = ["Exact Match", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
            status_start_row = 6
            
            for i, status in enumerate(dashboard_statuses):
                row = status_start_row + i
                dash.write(row, 1, status)
                # Use dynamic row reference for formulas
                dash.write_formula(row, 2, f'=COUNTIF(Reconciliation!$B$3:$B${actual_last_row}, "{status}")')
                dash.write_formula(row, 3, f'=SUMIF(Reconciliation!$B$3:$B${actual_last_row}, "{status}", Reconciliation!$H$3:$H${actual_last_row})')
                dash.write_formula(row, 4, f'=SUMIF(Reconciliation!$B$3:$B${actual_last_row}, "{status}", Reconciliation!$I$3:$I${actual_last_row})')

            # Top suppliers tables
            top_26as = final_recon[final_recon["Total TDS Deposited"] > 0].nlargest(10, "Total TDS Deposited")
            top_books = final_recon[final_recon["Books TDS"] > 0].nlargest(10, "Books TDS")

            dash.write("G5", "Top 10 Suppliers (26AS)", fmt_dark_blue_white)
            dash.write_row("G6", ["Deductor / Party Name", "Total Amount (26AS)", "Total TDS (26AS)"], fmt_dark_blue_white)
            for i, (_, row) in enumerate(top_26as.iterrows()):
                dash.write_row(i + 6, 6, [row["Deductor / Party Name"], row["Total Amount Paid / Credited"], row["Total TDS Deposited"]])
            dash.set_column('G:G', 35)
            dash.set_column('H:I', 18)

            dash.write("K5", "Top 10 Suppliers (Books)", fmt_dark_blue_white)
            dash.write_row("K6", ["Deductor / Party Name", "Books Amount", "Books TDS"], fmt_dark_blue_white)
            for i, (_, row) in enumerate(top_books.iterrows()):
                dash.write_row(i + 6, 10, [row["Deductor / Party Name"], row["Books Amount"], row["Books TDS"]])
            dash.set_column('K:K', 35)
            dash.set_column('L:M', 18)

            # Pie chart for status distribution
            status_end_row = status_start_row + len(dashboard_statuses) - 1
            pie_chart = workbook.add_chart({'type': 'pie'})
            pie_chart.add_series({
                'name': 'Status Distribution',
                'categories': f'=Dashboard!$B${status_start_row}:$B${status_end_row}',
                'values': f'=Dashboard!$C${status_start_row}:$C${status_end_row}',
                'data_labels': {'percentage': True, 'show_leader_lines': True}
            })
            dash.insert_chart('B13', pie_chart)

            # Reconciliation sheet
            sheet_recon = workbook.add_worksheet("Reconciliation")
            final_recon.to_excel(writer, sheet_name="Reconciliation", startrow=2, index=False, header=False)

            for col_num, col_name in enumerate(final_recon.columns):
                sheet_recon.write(1, col_num, col_name, fmt_dark_blue_white)
                if pd.api.types.is_numeric_dtype(final_recon[col_name]) and col_name != "Effective Rate 26AS (%)":
                    col_letter = chr(65 + col_num)
                    formula = f"=SUBTOTAL(9,{col_letter}3:{col_letter}{actual_last_row})"
                    sheet_recon.write_formula(0, col_num, formula, fmt_subtotal)

                max_len = max(final_recon[col_name].astype(str).str.len().max(), len(str(col_name)))
                sheet_recon.set_column(col_num, col_num, min(max_len + 3, 45))

            sheet_recon.autofilter(1, 0, actual_last_row, len(final_recon.columns) - 1)

            # 26AS Aggregated sheet
            if not agg_26as_section.empty:
                agg_sheet = workbook.add_worksheet("26AS Aggregated")
                numeric_agg = ["Total Amount Paid / Credited", "Total TDS Deposited"]
                agg_with_total = add_totals_row(agg_26as_section, numeric_agg)
                agg_with_total.to_excel(writer, sheet_name="26AS Aggregated", startrow=1, index=False, header=False)
                
                for col_num, col_name in enumerate(agg_with_total.columns):
                    agg_sheet.write(0, col_num, col_name, fmt_dark_blue_white)
                    max_len = max(agg_with_total[col_name].astype(str).str.len().max(), len(col_name))
                    agg_sheet.set_column(col_num, col_num, min(max_len + 3, 45))
                    if col_name in numeric_agg:
                        agg_sheet.set_column(col_num, col_num, None, fmt_number)
                agg_sheet.autofilter(0, 0, len(agg_with_total), len(agg_with_total.columns)-1)

            # 26AS Raw sheet
            if not raw_26as_detailed.empty:
                raw_sheet = workbook.add_worksheet("26AS Raw (Detailed)")
                raw_columns = ["Section", "Sl. No.", "Name of Deductor", "TAN of Deductor",
                               "Amount paid/credited", "Date of Payment/Credit",
                               "Total tax deducted", "Amount claimed for this year", "C/F Tax"]
                for col in raw_columns:
                    if col not in raw_26as_detailed.columns:
                        raw_26as_detailed[col] = ""
                raw_data = raw_26as_detailed[raw_columns]
                numeric_raw = ["Amount paid/credited", "Total tax deducted", "Amount claimed for this year", "C/F Tax"]
                raw_with_total = add_totals_row(raw_data, numeric_raw)
                raw_with_total.to_excel(writer, sheet_name="26AS Raw (Detailed)", startrow=1, index=False, header=False)
                
                for col_num, col_name in enumerate(raw_columns):
                    raw_sheet.write(0, col_num, col_name, fmt_dark_blue_white)
                    max_len = max(raw_with_total[col_name].astype(str).str.len().max(), len(col_name))
                    raw_sheet.set_column(col_num, col_num, min(max_len + 3, 45))
                    if col_name in numeric_raw:
                        raw_sheet.set_column(col_num, col_num, None, fmt_number)
                raw_sheet.autofilter(0, 0, len(raw_with_total), len(raw_columns)-1)

            # Books Raw sheet
            books.to_excel(writer, sheet_name="Books Raw", index=False)
            sheet_bk_raw = writer.sheets["Books Raw"]
            for i, col in enumerate(books.columns):
                max_len = max(books[col].astype(str).str.len().max(), len(str(col)))
                sheet_bk_raw.set_column(i, i, min(max_len + 3, 45))

        output.seek(0)
        st.success("✅ Enterprise Reconciliation completed successfully.")
        logger.info("Reconciliation report generated successfully")

        fy_safe = extracted_fy.replace('-', '_') if extracted_fy != 'Unknown' else 'Latest'
        col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
        with col_dl2:
            st.download_button(
                "⚡ Download Final Excel Report", 
                output, 
                f"26AS_Recon_FY_{fy_safe}.xlsx", 
                use_container_width=True,
                type="primary"
            )

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; margin-top:30px; margin-bottom:20px; opacity:0.8;">
    <span style="font-weight:700;">Tool Developed by Abhishek Jakkula</span><br>
    <span>📧 <a href="mailto:jakkulaabhishek5@gmail.com" style="color: var(--accent-light); text-decoration:none;">jakkulaabhishek5@gmail.com</a></span>
</div>
""", unsafe_allow_html=True)
