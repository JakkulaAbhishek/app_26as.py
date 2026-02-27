import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
from rapidfuzz import process, fuzz

st.set_page_config(page_title="26AS Enterprise Reconciliation", layout="wide")

# ----------- ULTRA PREMIUM NEXT‑LEVEL UI -----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Playfair+Display:wght@700&display=swap');

:root {
    --bg-deep: #0b0c1a;
    --bg-gradient-1: #1a1f3c;
    --bg-gradient-2: #2a1e3c;
    --accent-primary: #9f7aea;
    --accent-secondary: #f687b3;
    --accent-glow: rgba(159, 122, 234, 0.5);
    --text-light: #f7fafc;
    --text-muted: #cbd5e0;
    --card-bg: rgba(20, 25, 45, 0.7);
    --card-border: rgba(255, 255, 255, 0.08);
    --glass-blur: 20px;
}

/* Dark background with animated particles */
.stApp {
    background: linear-gradient(135deg, var(--bg-deep), var(--bg-gradient-1), var(--bg-gradient-2));
    background-size: 400% 400%;
    animation: gradientFlow 18s ease infinite;
    position: relative;
    overflow-x: hidden;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at 20% 30%, rgba(159, 122, 234, 0.15) 0%, transparent 30%),
                radial-gradient(circle at 80% 70%, rgba(246, 135, 179, 0.1) 0%, transparent 35%);
    pointer-events: none;
    z-index: 0;
}

@keyframes gradientFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Premium Glass Card */
.glass-card {
    background: var(--card-bg);
    backdrop-filter: blur(var(--glass-blur));
    -webkit-backdrop-filter: blur(var(--glass-blur));
    border-radius: 32px;
    border: 1px solid var(--card-border);
    padding: 2.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5),
                inset 0 1px 1px rgba(255, 255, 255, 0.1);
    transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275),
                box-shadow 0.4s ease;
    position: relative;
    z-index: 1;
}

.glass-card:hover {
    transform: translateY(-8px) scale(1.01);
    box-shadow: 0 30px 60px -15px rgba(159, 122, 234, 0.4),
                inset 0 1px 2px rgba(255, 255, 255, 0.2);
    border-color: rgba(159, 122, 234, 0.3);
}

.glass-card::after {
    content: '';
    position: absolute;
    top: -1px;
    left: -1px;
    right: -1px;
    bottom: -1px;
    background: linear-gradient(135deg, rgba(159,122,234,0.3), rgba(246,135,179,0.3));
    border-radius: 33px;
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
    z-index: -1;
}

.glass-card:hover::after {
    opacity: 0.15;
}

/* Header with gold gradient */
.header-title {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 4rem;
    background: linear-gradient(135deg, #f6e05e, #fbbf24, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 2px 20px rgba(245, 158, 11, 0.3);
    line-height: 1.2;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
}

.header-sub {
    font-size: 1.4rem;
    font-weight: 400;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    opacity: 1;
    margin-top: 0;
}

.dev-credit {
    font-size: 1.1rem;
    margin-top: 0.5rem;
    color: var(--text-muted);
    font-style: italic;
}

.dev-credit b {
    background: linear-gradient(135deg, #f687b3, #9f7aea);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}

/* Premium Buttons with shine */
.stButton>button,
.stDownloadButton>button {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    color: white !important;
    border-radius: 60px;
    padding: 14px 36px;
    font-weight: 700;
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 8px 20px rgba(159, 122, 234, 0.3),
                0 0 0 1px rgba(255,255,255,0.1) inset;
    position: relative;
    overflow: hidden;
    width: 100%;
}

.stButton>button::after,
.stDownloadButton>button::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -60%;
    width: 200%;
    height: 200%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transform: rotate(30deg);
    transition: left 0.5s ease;
}

.stButton>button:hover::after,
.stDownloadButton>button:hover::after {
    left: 100%;
}

.stButton>button:hover,
.stDownloadButton>button:hover {
    transform: translateY(-4px);
    box-shadow: 0 15px 30px rgba(159, 122, 234, 0.5),
                0 0 0 2px rgba(255,255,255,0.2) inset;
}

/* Premium Metrics */
[data-testid="stMetric"] {
    background: rgba(20, 25, 45, 0.5);
    backdrop-filter: blur(12px);
    border-radius: 28px;
    padding: 1.5rem 1rem;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 15px 35px -10px rgba(0,0,0,0.5);
    transition: all 0.3s ease;
}

[data-testid="stMetric"]:hover {
    transform: scale(1.02);
    border-color: rgba(159,122,234,0.3);
}

[data-testid="stMetricValue"] {
    font-weight: 800;
    font-size: 2rem;
    color: #f7fafc;
    text-shadow: 0 0 10px rgba(159,122,234,0.5);
}

[data-testid="stMetricLabel"] {
    color: #a0aec0;
    font-weight: 400;
    letter-spacing: 0.5px;
}

/* File uploader – luxury glass */
[data-testid="stFileUploader"] {
    background: rgba(20, 25, 45, 0.4) !important;
    backdrop-filter: blur(12px);
    border-radius: 28px !important;
    border: 2px dashed rgba(159,122,234,0.5) !important;
    padding: 2rem !important;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--accent-secondary) !important;
    background: rgba(20,25,45,0.6) !important;
    box-shadow: 0 0 20px rgba(159,122,234,0.3);
}

/* Alert Boxes – ultra vibrant */
.alert-box-red {
    background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(239,68,68,0.05));
    backdrop-filter: blur(12px);
    border-left: 6px solid #ef4444;
    border-radius: 20px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 25px -8px rgba(239,68,68,0.3);
    color: #f7fafc;
}

.alert-box-yellow {
    background: linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.05));
    backdrop-filter: blur(12px);
    border-left: 6px solid #f59e0b;
    border-radius: 20px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 25px -8px rgba(245,158,11,0.3);
    color: #f7fafc;
}

.alert-box-blue {
    background: linear-gradient(135deg, rgba(37,99,235,0.2), rgba(37,99,235,0.05));
    backdrop-filter: blur(12px);
    border-left: 6px solid #2563eb;
    border-radius: 20px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 25px -8px rgba(37,99,235,0.3);
    color: #f7fafc;
}

.alert-box-green {
    background: linear-gradient(135deg, rgba(16,185,129,0.2), rgba(16,185,129,0.05));
    backdrop-filter: blur(12px);
    border-left: 6px solid #10b981;
    border-radius: 20px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 25px -8px rgba(16,185,129,0.3);
    color: #f7fafc;
}

/* Step zone – animated */
.zone {
    background: rgba(20,25,45,0.5);
    backdrop-filter: blur(10px);
    padding: 20px;
    border-radius: 60px;
    border: 1px solid rgba(159,122,234,0.3);
    text-align: center;
    font-weight: 700;
    font-size: 1.2rem;
    letter-spacing: 1px;
    color: #e2e8f0;
    margin-bottom: 25px;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    animation: pulseGlow 3s infinite;
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(159,122,234,0.3); border-color: rgba(159,122,234,0.3); }
    50% { box-shadow: 0 0 20px 0 rgba(159,122,234,0.6); border-color: rgba(159,122,234,0.8); }
    100% { box-shadow: 0 0 0 0 rgba(159,122,234,0.3); border-color: rgba(159,122,234,0.3); }
}

/* Dataframe – sleek */
[data-testid="stDataFrame"] {
    background: transparent;
}

[data-testid="stDataFrame"] table {
    background: rgba(20,25,45,0.6);
    backdrop-filter: blur(5px);
    border-radius: 24px;
    overflow: hidden;
    border-collapse: separate;
    border-spacing: 0;
}

[data-testid="stDataFrame"] th {
    background: linear-gradient(135deg, #4c1d95, #6b21a5) !important;
    color: white !important;
    font-weight: 700;
    font-size: 0.95rem;
    padding: 12px !important;
}

[data-testid="stDataFrame"] td {
    color: #f7fafc;
    padding: 12px !important;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(20,25,45,0.6);
    backdrop-filter: blur(12px);
    border-radius: 28px;
    font-weight: 700;
    color: #e2e8f0;
    padding: 1rem 1.5rem;
    border: 1px solid rgba(159,122,234,0.3);
    transition: all 0.3s ease;
}

.streamlit-expanderHeader:hover {
    border-color: var(--accent-secondary);
    box-shadow: 0 0 15px rgba(159,122,234,0.3);
}

.streamlit-expanderContent {
    background: rgba(20,25,45,0.4);
    backdrop-filter: blur(10px);
    border-radius: 0 0 28px 28px;
    border: 1px solid rgba(159,122,234,0.2);
    border-top: none;
    padding: 1.5rem;
}

/* Sidebar */
.css-1d391kg, .css-12oz5g7 {
    background: rgba(10, 15, 30, 0.8) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(159,122,234,0.2);
}

/* Footer with signature */
.footer {
    text-align: center;
    margin-top: 60px;
    margin-bottom: 20px;
    color: var(--text-muted);
    font-size: 1rem;
    background: rgba(20,25,45,0.3);
    backdrop-filter: blur(5px);
    padding: 20px;
    border-radius: 60px;
    border: 1px solid rgba(255,255,255,0.05);
}

.footer a {
    color: var(--accent-primary);
    text-decoration: none;
    font-weight: 600;
    transition: color 0.3s ease;
}

.footer a:hover {
    color: var(--accent-secondary);
    text-decoration: underline;
}

/* Hide default Streamlit footer */
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Wrap the main content in a glass card
st.markdown('<div class="glass-card">', unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <div class="header-title">26AS Enterprise Reconciliation</div>
    <div class="header-sub">RapidFuzz AI | Smart Memory | TDS Rate Auditor</div>
    <div class="dev-credit">Developed by <b>Abhishek Jakkula</b></div>
</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    tolerance = st.number_input("Mismatch Tolerance (₹)", min_value=0, value=10, step=1)
    max_rows = st.number_input("Max Rows for Excel Formulas", min_value=1000, value=15000, step=1000)
    
    st.markdown("---")
    st.markdown("### 🧠 AI Smart Memory")
    st.info("Upload a previously saved Mapping Dictionary to auto-match custom vendor names.")
    mapping_file = st.file_uploader("Upload Dictionary (CSV)", type=['csv'])
    
    known_mappings = {}
    if mapping_file:
        try:
            map_df = pd.read_csv(mapping_file)
            if 'TAN of Deductor' in map_df.columns and 'Mapped Books Party' in map_df.columns:
                known_mappings = dict(zip(map_df['TAN of Deductor'].astype(str).str.strip().str.upper(), 
                                          map_df['Mapped Books Party'].astype(str).str.strip().str.upper()))
                st.success(f"Loaded {len(known_mappings)} custom mappings!")
        except Exception as e:
            st.error("Invalid dictionary format.")

# ---------------- SAMPLE TEMPLATES ----------------
st.markdown('<div class="zone">📄 Step 1: Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

sample_books = pd.DataFrame({"Party Name": ["ABC Pvt Ltd", "XYZ Corp"], "TAN": ["HYDA00000A", ""], "Books Amount": [100000, 50000], "Books TDS": [10000, 5000]})
books_buf = io.BytesIO()
sample_books.to_excel(books_buf, index=False)
books_buf.seek(0)

sample_dict = pd.DataFrame({"TAN of Deductor": ["HYDA00000A"], "Mapped Books Party": ["ABC Pvt Ltd"]})
dict_csv = sample_dict.to_csv(index=False).encode('utf-8')

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.download_button("⬇ Download Sample Books Excel", books_buf, "Sample_Books.xlsx", use_container_width=True)
with col_t2:
    st.download_button("⬇ Download Sample Mapping Dictionary", dict_csv, "Sample_Mapping.csv", mime="text/csv", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------- FILE UPLOAD & YEAR VALIDATION ----------------
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx", "xls"])

extracted_pan = "Unknown"
extracted_ay = "Unknown"
extracted_fy = "Unknown"

if txt_file:
    raw_text = txt_file.getvalue().decode("utf-8", errors="ignore")
    header_match = re.search(r'\d{2}-\d{2}-\d{4}\^([A-Z]{5}\d{4}[A-Z])\^[^\^]*\^(\d{4}-\d{4})\^(\d{4}-\d{4})\^', raw_text)
    
    if header_match:
        extracted_pan = header_match.group(1)
        extracted_fy = header_match.group(2)
        extracted_ay = header_match.group(3)
    else:
        pan_match = re.search(r'\^([A-Z]{5}\d{4}[A-Z])\^', raw_text)
        if pan_match: extracted_pan = pan_match.group(1)
    
    st.markdown(f"""
    <div class="alert-box-green" style="text-align:center;">
        <b>📌 Data Detected:</b> You are reconciling PAN <b>{extracted_pan}</b> for Financial Year <b>{extracted_fy}</b> (AY {extracted_ay}). Please ensure your Books match this period!
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------- BUTTON LOGIC ----------------
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    run_engine = st.button("🚀 RUN ENTERPRISE ENGINE", use_container_width=True)

# ---------------- CACHED AI ENGINE ----------------
@st.cache_data
def extract_26as_summary_and_section(file_bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    summary_data, section_map = [], {}
    in_part1, current_tan = False, ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]
        for p in parts:
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p): current_tan = p

        sec = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), None)
        if current_tan and sec and current_tan not in section_map: section_map[current_tan] = sec

        if "PART-I - Details of Tax Deducted at Source" in line:
            in_part1 = True; continue
        if in_part1 and line.startswith("^PART-"): break

        if in_part1 and len(parts) >= 6 and re.fullmatch(r"\d+", parts[0]):
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", parts[2]):
                try:
                    summary_data.append({
                        "Name of Deductor": parts[1], "TAN of Deductor": parts[2],
                        "Total Amount Paid / Credited": float(parts[-3].replace(",","")),
                        "Total Tax Deducted": float(parts[-2].replace(",","")),
                        "Total TDS Deposited": float(parts[-1].replace(",",""))
                    })
                except Exception: pass

    df = pd.DataFrame(summary_data)
    if not df.empty: df.insert(0, "Section", df["TAN of Deductor"].map(section_map).fillna(""))
    return df

@st.cache_data(show_spinner=False)
def process_data(txt_bytes, books_bytes):
    structured_26as = extract_26as_summary_and_section(txt_bytes)
    if structured_26as.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    books = pd.read_excel(io.BytesIO(books_bytes))
    required_cols = ["Party Name", "TAN", "Books Amount", "Books TDS"]
    for col in required_cols:
        if col not in books.columns: books[col] = "" if col in ["Party Name", "TAN"] else 0

    books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()
    books["Party Name"] = books["Party Name"].fillna("").astype(str).str.strip().str.upper()
    
    numeric_cols = ["Books Amount", "Books TDS"]
    for col in numeric_cols: books[col] = pd.to_numeric(books[col], errors="coerce").fillna(0)
    books = books.groupby(['Party Name', 'TAN'], as_index=False)[numeric_cols].sum()

    structured_26as["TAN of Deductor"] = structured_26as["TAN of Deductor"].astype(str).str.strip().str.upper()

    exact_match = pd.merge(structured_26as, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
    exact_match["Match Type"] = "Exact (TAN)"

    rem_26as = structured_26as[~structured_26as["TAN of Deductor"].isin(exact_match["TAN of Deductor"])]
    rem_books = books[~books["TAN"].isin(exact_match["TAN"])]

    fuzzy_records, matched_books_indices = [], set()
    book_choices = {idx: row["Party Name"] for idx, row in rem_books.iterrows()}

    for idx_26, row_26 in rem_26as.iterrows():
        name_26 = str(row_26["Name of Deductor"]).upper()
        if not book_choices:
            combined = row_26.to_dict(); combined["Match Type"] = "Missing in Books"; fuzzy_records.append(combined); continue
            
        result = process.extractOne(name_26, book_choices, scorer=fuzz.token_sort_ratio, score_cutoff=70)
        if result:
            best_match_str, best_score, best_book_idx = result
            combined = row_26.to_dict(); combined.update(rem_books.loc[best_book_idx].to_dict()); combined["Match Type"] = "Fuzzy Match"
            fuzzy_records.append(combined); matched_books_indices.add(best_book_idx); del book_choices[best_book_idx] 
        else:
            combined = row_26.to_dict(); combined["Match Type"] = "Missing in Books"; fuzzy_records.append(combined)

    for idx_bk, row_bk in rem_books.iterrows():
        if idx_bk not in matched_books_indices:
            combined = row_bk.to_dict(); combined["Match Type"] = "Missing in 26AS"; fuzzy_records.append(combined)

    fuzzy_df = pd.DataFrame(fuzzy_records) if fuzzy_records else pd.DataFrame()
    recon = pd.concat([exact_match, fuzzy_df], ignore_index=True)
    recon["Deductor / Party Name"] = np.where(recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""), recon["Name of Deductor"], recon["Party Name"])
    recon["Final TAN"] = np.where(recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""), recon["TAN of Deductor"], recon["TAN"])

    return recon, structured_26as, books

# ---------------- MAIN APPLICATION LOGIC ----------------
if run_engine:
    if not txt_file or not books_file:
        st.warning("⚠️ Please upload both the 26AS and Books files to proceed.")
    else:
        with st.spinner("Running High-Speed AI Engine & Rate Auditor..."):
            raw_recon, structured_26as, books = process_data(txt_file.getvalue(), books_file.getvalue())

        if raw_recon.empty:
            st.error("❌ No valid PART-I summary detected in the 26AS text file.")
            st.stop()

        recon = raw_recon.copy()

        # Apply known dictionary mappings automatically
        if known_mappings:
            for tan_26, target_bk_name in known_mappings.items():
                row_26_idx = recon[(recon['TAN of Deductor'] == tan_26) & (recon['Match Type'] == 'Missing in Books')].index
                row_bk_idx = recon[(recon['Party Name'] == target_bk_name) & (recon['Match Type'] == 'Missing in 26AS')].index
                
                if not row_26_idx.empty() and not row_bk_idx.empty():
                    i_26, i_bk = row_26_idx[0], row_bk_idx[0]
                    recon.at[i_26, 'Party Name'] = recon.at[i_bk, 'Party Name']
                    recon.at[i_26, 'TAN'] = recon.at[i_bk, 'TAN']
                    recon.at[i_26, 'Books Amount'] = recon.at[i_bk, 'Books Amount']
                    recon.at[i_26, 'Books TDS'] = recon.at[i_bk, 'Books TDS']
                    recon.at[i_26, 'Match Type'] = 'Dictionary Match'
                    recon.at[i_26, 'Deductor / Party Name'] = recon.at[i_26, 'Name of Deductor']
                    recon = recon.drop(index=i_bk)

        # Core Calculations
        num_cols = ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS"]
        for col in num_cols: recon[col] = pd.to_numeric(recon[col], errors="coerce").fillna(0)

        recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
        recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]
        recon['Effective Rate 26AS (%)'] = np.where(recon['Total Amount Paid / Credited'] > 0, (recon['Total TDS Deposited'] / recon['Total Amount Paid / Credited']) * 100, 0).round(2)

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

        final_recon = recon[[
            "Section", "Match Status", "Deductor / Party Name", "Final TAN",
            "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
            "Total TDS Deposited", "Books TDS", "Difference TDS", "Effective Rate 26AS (%)", "Reason for Difference"
        ]].rename(columns={"Final TAN": "TAN"})

        # ---------------- COMPLIANCE ALERTS (AT THE TOP) ----------------
        st.markdown("### 🚨 Compliance & Anomaly Alerts")
        
        anomalies = recon[(recon['Effective Rate 26AS (%)'] > 0) & (~recon['Effective Rate 26AS (%)'].isin([1.0, 2.0, 5.0, 10.0, 20.0]))]
        if not anomalies.empty:
            top_anomaly = anomalies.nlargest(1, 'Total TDS Deposited').iloc[0]
            st.markdown(f"""
            <div class="alert-box-blue">
                <b>🔎 TDS Rate Anomaly Detected:</b> Non-standard deduction rates identified.<br>
                <span style="color: #7dd3fc; font-size: 0.95rem;"><i>👉 <b>{top_anomaly['Deductor / Party Name']}</b> deducted TDS at an effective rate of <b>{top_anomaly['Effective Rate 26AS (%)']}%</b>.</i></span>
            </div>
            """, unsafe_allow_html=True)

        miss_in_books = recon[recon["Match Status"] == "Missing in Books"]
        if not miss_in_books.empty and miss_in_books["Total TDS Deposited"].sum() > 0:
            top_missed = miss_in_books.loc[miss_in_books["Total TDS Deposited"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-red">
                <b>URGENT: Unclaimed TDS Leakage!</b> ₹ {miss_in_books["Total TDS Deposited"].sum():,.2f} is in 26AS but completely <b>MISSING</b> in books.<br>
                <span style="color: #fca5a5; font-size: 0.95rem;"><i>👉 Top Missing Party: <b>{top_missed['Deductor / Party Name']}</b> (₹ {top_missed['Total TDS Deposited']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)

        miss_in_26as = recon[recon["Match Status"] == "Missing in 26AS"]
        if not miss_in_26as.empty and miss_in_26as["Books TDS"].sum() > 0:
            top_excess = miss_in_26as.loc[miss_in_26as["Books TDS"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-yellow">
                <b>COMPLIANCE RISK:</b> ₹ {miss_in_26as["Books TDS"].sum():,.2f} of TDS is claimed in Books but <b>NOT uploaded in 26AS</b>.<br>
                <span style="color: #fcd34d; font-size: 0.95rem;"><i>👉 Top Unreflected Party: <b>{top_excess['Deductor / Party Name']}</b> (₹ {top_excess['Books TDS']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)

        # ---------------- DASHBOARD & ANALYTICS ----------------
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
            # Match Status Pie Chart
            status_counts = final_recon["Match Status"].value_counts().reset_index()
            status_counts.columns = ["Match Status", "Count"]
            color_map = {
                "Exact Match": "#10b981", "Fuzzy Match": "#38bdf8", 
                "Value Mismatch": "#ef4444", "Missing in Books": "#f97316", "Missing in 26AS": "#8b5cf6"
            }
            fig_status = px.pie(status_counts, names="Match Status", values="Count", title="Match Status Distribution", hole=0.4, color="Match Status", color_discrete_map=color_map)
            fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc", family="Poppins"))
            st.plotly_chart(fig_status, use_container_width=True)

        with c2:
            # Section-Wise Bar Chart
            section_summary = recon.groupby('Section')[['Total TDS Deposited', 'Books TDS']].sum().reset_index()
            section_summary = section_summary[section_summary['Section'] != ""]
            fig_sec = px.bar(section_summary, x='Section', y=['Total TDS Deposited', 'Books TDS'], barmode='group', title="TDS Claimed vs Reflected by Section")
            fig_sec.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc", family="Poppins"), legend_title_text="")
            st.plotly_chart(fig_sec, use_container_width=True)

        # --- Excel Export ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            brand_format = workbook.add_format({"bold": True, "font_size": 18, "bg_color": "#0f172a", "font_color": "#38bdf8", "align": "center", "valign": "vcenter"})
            dev_format = workbook.add_format({"italic": True, "font_size": 10, "bg_color": "#0f172a", "font_color": "#94a3b8", "align": "center"})
            fmt_dark_blue_white = workbook.add_format({"bold": True, "bg_color": "#0052cc", "font_color": "white", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
            fmt_subtotal = workbook.add_format({"bold": True, "bg_color": "#f2f2f2", "border": 1, "num_format": "#,##0.00"})

            dash = workbook.add_worksheet("Dashboard")
            dash.hide_gridlines(2)
            
            fy_title = f"(FY: {extracted_fy})" if extracted_fy != "Unknown" else ""
            dash.merge_range("A1:M2", f"26AS ENTERPRISE RECON - EXECUTIVE SUMMARY {fy_title}", brand_format)
            dash.merge_range("A3:M3", "Developed by ABHISHEK JAKKULA | jakkulaabhishek5@gmail.com", dev_format)

            dash.write_row("B5", ["Match Status", "Record Count", "TDS Impact (26AS)", "TDS Impact (Books)"], fmt_dark_blue_white)
            dash.set_column('B:B', 25); dash.set_column('C:E', 18)

            dashboard_statuses = ["Exact Match", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
            for i, status in enumerate(dashboard_statuses):
                row = 5 + i
                dash.write(row, 1, status)
                dash.write_formula(row, 2, f'=COUNTIF(Reconciliation!$B$3:$B${max_rows}, "{status}")')
                dash.write_formula(row, 3, f'=SUMIF(Reconciliation!$B$3:$B${max_rows}, "{status}", Reconciliation!$H$3:$H${max_rows})')
                dash.write_formula(row, 4, f'=SUMIF(Reconciliation!$B$3:$B${max_rows}, "{status}", Reconciliation!$I$3:$I${max_rows})')

            top_26as = final_recon[final_recon["Total TDS Deposited"] > 0].nlargest(10, "Total TDS Deposited")
            top_books = final_recon[final_recon["Books TDS"] > 0].nlargest(10, "Books TDS")

            dash.write("G5", "Top 10 Suppliers (26AS)", fmt_dark_blue_white)
            dash.write_row("G6", ["Deductor / Party Name", "Total Amount (26AS)", "Total TDS (26AS)"], fmt_dark_blue_white)
            for i, (_, row) in enumerate(top_26as.iterrows()): 
                dash.write_row(i + 6, 6, [row["Deductor / Party Name"], row["Total Amount Paid / Credited"], row["Total TDS Deposited"]])
            dash.set_column('G:G', 35); dash.set_column('H:I', 18)

            dash.write("K5", "Top 10 Suppliers (Books)", fmt_dark_blue_white)
            dash.write_row("K6", ["Deductor / Party Name", "Books Amount", "Books TDS"], fmt_dark_blue_white)
            for i, (_, row) in enumerate(top_books.iterrows()): 
                dash.write_row(i + 6, 10, [row["Deductor / Party Name"], row["Books Amount"], row["Books TDS"]])
            dash.set_column('K:K', 35); dash.set_column('L:M', 18)

            pie_chart = workbook.add_chart({'type': 'pie'})
            pie_chart.add_series({'name': 'Status Distribution', 'categories': f'=Dashboard!$B$6:$B$10', 'values': f'=Dashboard!$C$6:$C$10', 'data_labels': {'percentage': True, 'show_leader_lines': True}})
            dash.insert_chart('B13', pie_chart)

            pie_26as = workbook.add_chart({'type': 'pie'})
            pie_26as.add_series({'name': 'Top 10 26AS', 'categories': f'=Dashboard!$G$7:$G${6 + len(top_26as)}', 'values': f'=Dashboard!$I$7:$I${6 + len(top_26as)}', 'data_labels': {'percentage': True}})
            pie_26as.set_title({'name': 'Top 10 Deductors (26AS)'})
            dash.insert_chart('G18', pie_26as)

            pie_books = workbook.add_chart({'type': 'pie'})
            pie_books.add_series({'name': 'Top 10 Books', 'categories': f'=Dashboard!$K$7:$K${6 + len(top_books)}', 'values': f'=Dashboard!$M$7:$M${6 + len(top_books)}', 'data_labels': {'percentage': True}})
            pie_books.set_title({'name': 'Top 10 Parties (Books)'})
            dash.insert_chart('K18', pie_books)

            # B. Reconciliation Sheet with Auto-Width
            sheet_recon = workbook.add_worksheet("Reconciliation")
            final_recon.to_excel(writer, sheet_name="Reconciliation", startrow=2, index=False, header=False)
            
            for col_num, col_name in enumerate(final_recon.columns):
                sheet_recon.write(1, col_num, col_name, fmt_dark_blue_white)
                if pd.api.types.is_numeric_dtype(final_recon[col_name]) and col_name != "Effective Rate 26AS (%)":
                    col_letter = chr(65 + col_num) 
                    formula = f"=SUBTOTAL(9,{col_letter}3:{col_letter}{max_rows})"
                    sheet_recon.write_formula(0, col_num, formula, fmt_subtotal)
                
                max_len = max(final_recon[col_name].astype(str).map(len).max(), len(str(col_name)))
                sheet_recon.set_column(col_num, col_num, min(max_len + 3, 45))

            sheet_recon.autofilter(1, 0, max_rows, len(final_recon.columns) - 1)

            # C. Raw Data Sheets with Auto-Width
            structured_26as.to_excel(writer, sheet_name="26AS Raw", index=False)
            sheet_26_raw = writer.sheets["26AS Raw"]
            for i, col in enumerate(structured_26as.columns):
                max_len = max(structured_26as[col].astype(str).map(len).max(), len(str(col)))
                sheet_26_raw.set_column(i, i, min(max_len + 3, 45))

            books.to_excel(writer, sheet_name="Books Raw", index=False)
            sheet_bk_raw = writer.sheets["Books Raw"]
            for i, col in enumerate(books.columns):
                max_len = max(books[col].astype(str).map(len).max(), len(str(col)))
                sheet_bk_raw.set_column(i, i, min(max_len + 3, 45))

        output.seek(0)
        st.success("✅ Enterprise Reconciliation completed successfully.")

        fy_safe = extracted_fy.replace('-', '_') if extracted_fy != 'Unknown' else 'Latest'
        
        col_dl1, col_dl2, col_dl3 = st.columns([1,2,1])
        with col_dl2: 
            st.download_button("⚡ Download Final Excel Report", output, f"26AS_Recon_FY_{fy_safe}.xlsx", use_container_width=True)

# Close the main glass card
st.markdown('</div>', unsafe_allow_html=True)

# Footer with signature
st.markdown("""
<div class="footer">
    <span style="font-weight:700;">Tool Developed by Abhishek Jakkula</span><br>
    <span>📧 <a href="mailto:jakkulaabhishek5@gmail.com">jakkulaabhishek5@gmail.com</a></span>
</div>
""", unsafe_allow_html=True)
