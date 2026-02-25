import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
from rapidfuzz import process, fuzz
from typing import Optional, Tuple, Dict, List
import time

# ---------------------------- CONFIGURATION ----------------------------
st.set_page_config(page_title="26AS Enterprise Reconciliation", layout="wide")

# Constants
DEFAULT_TOLERANCE = 10
DEFAULT_FUZZY_THRESHOLD = 70
STANDARD_TDS_RATES = [1.0, 2.0, 5.0, 10.0, 20.0]
MAX_EXCEL_ROWS = 15000  # default, but will be auto‑calculated later

# ---------------------------- CUSTOM CSS (theme‑safe) ----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: transparent;
}

.header-title {
    font-weight: 800;
    font-size: 2.8rem;
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
}

.header-sub {
    font-size: 1.1rem;
    font-weight: 600;
    opacity: 0.8;
    margin-top: 6px;
}

.dev-credit {
    font-size: 0.95rem;
    margin-top: 8px;
    opacity: 0.7;
}

.dev-credit b {
    color: #2563eb;
}

.stButton>button,
.stDownloadButton>button {
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    color: white !important;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
}

.stButton>button:hover,
.stDownloadButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(37, 99, 235, 0.4);
}

[data-testid="stMetric"] {
    background: rgba(0, 0, 0, 0.03);
    border-radius: 14px;
    padding: 20px;
    border: 1px solid rgba(0,0,0,0.06);
}

@media (prefers-color-scheme: dark) {
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
    }
}

[data-testid="stMetricValue"] {
    font-weight: 800;
    font-size: 1.6rem;
}

[data-testid="stFileUploader"] {
    border-radius: 12px !important;
    border: 1px dashed rgba(100,116,139,0.4) !important;
    padding: 1.2em !important;
}

.alert-box-red, .alert-box-yellow, .alert-box-blue, .alert-box-green {
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: opacity 0.2s;
}
.alert-box-red:hover, .alert-box-yellow:hover, .alert-box-blue:hover, .alert-box-green:hover {
    opacity: 0.9;
}
.alert-box-red {
    background: rgba(239, 68, 68, 0.08);
    border-left: 5px solid #ef4444;
}
.alert-box-yellow {
    background: rgba(245, 158, 11, 0.08);
    border-left: 5px solid #f59e0b;
}
.alert-box-blue {
    background: rgba(37, 99, 235, 0.08);
    border-left: 5px solid #2563eb;
}
.alert-box-green {
    background: rgba(16, 185, 129, 0.08);
    border-left: 5px solid #10b981;
}
@media (prefers-color-scheme: dark) {
    .alert-box-red { background: rgba(239,68,68,0.15); }
    .alert-box-yellow { background: rgba(245,158,11,0.15); }
    .alert-box-blue { background: rgba(37,99,235,0.15); }
    .alert-box-green { background: rgba(16,185,129,0.15); }
}

.zone {
    background: rgba(0,0,0,0.03);
    padding: 16px;
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.05);
    margin-bottom: 18px;
    text-align: center;
    font-weight: 600;
    opacity: 0.8;
}
@media (prefers-color-scheme: dark) {
    .zone {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
    }
}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------- SESSION STATE ----------------------------
if 'run_engine' not in st.session_state:
    st.session_state.run_engine = False
if 'filter_status' not in st.session_state:
    st.session_state.filter_status = None
if 'recon_df' not in st.session_state:
    st.session_state.recon_df = None
if 'extracted_info' not in st.session_state:
    st.session_state.extracted_info = {"pan": "Unknown", "fy": "Unknown", "ay": "Unknown"}

def reset_engine():
    st.session_state.run_engine = False
    st.session_state.filter_status = None
    st.session_state.recon_df = None

# ---------------------------- SIDEBAR ----------------------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    tolerance = st.number_input("Mismatch Tolerance (₹)", min_value=0, value=DEFAULT_TOLERANCE, step=1, on_change=reset_engine)
    fuzzy_threshold = st.slider("Fuzzy Match Threshold (%)", min_value=50, max_value=100, value=DEFAULT_FUZZY_THRESHOLD, step=5, on_change=reset_engine)
    
    st.markdown("---")
    st.markdown("### 🧠 AI Smart Memory")
    st.info("Upload a previously saved Mapping Dictionary to auto-match custom vendor names.")
    mapping_file = st.file_uploader("Upload Dictionary (CSV)", type=['csv'], on_change=reset_engine)
    
    known_mappings = {}
    if mapping_file:
        try:
            map_df = pd.read_csv(mapping_file)
            if 'TAN of Deductor' in map_df.columns and 'Mapped Books Party' in map_df.columns:
                known_mappings = dict(zip(map_df['TAN of Deductor'].astype(str).str.strip().str.upper(), 
                                          map_df['Mapped Books Party'].astype(str).str.strip().str.upper()))
                st.success(f"Loaded {len(known_mappings)} custom mappings!")
        except Exception as e:
            st.error("Invalid dictionary format. Please ensure CSV has 'TAN of Deductor' and 'Mapped Books Party' columns.")

# ---------------------------- HEADER ----------------------------
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <div class="header-title">26AS Enterprise Reconciliation</div>
    <div class="header-sub">RapidFuzz AI | Smart Memory | TDS Rate Auditor</div>
    <div class="dev-credit">Developed by <b>Abhishek Jakkula</b></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------- SAMPLE TEMPLATES ----------------------------
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

# ---------------------------- FILE UPLOAD ----------------------------
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"], on_change=reset_engine)
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx", "xls"], on_change=reset_engine)

# Extract PAN/FY from 26AS
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
    
    st.session_state.extracted_info = {"pan": extracted_pan, "fy": extracted_fy, "ay": extracted_ay}
    
    st.markdown(f"""
    <div class="alert-box-green" style="text-align:center;">
        <b>📌 Data Detected:</b> You are reconciling PAN <b>{extracted_pan}</b> for Financial Year <b>{extracted_fy}</b> (AY {extracted_ay}). Please ensure your Books match this period!
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------- COLUMN MAPPING (if books uploaded) ----------------------------
books_column_map = {}
if books_file and not st.session_state.run_engine:
    st.markdown("### 🔍 Map Your Books Columns")
    st.info("Tell us which columns in your Excel correspond to the required fields.")
    try:
        books_raw = pd.read_excel(io.BytesIO(books_file.getvalue()), nrows=5)  # preview
        cols = books_raw.columns.tolist()
        if cols:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                party_col = st.selectbox("Party Name column", cols, index=cols.index("Party Name") if "Party Name" in cols else 0, key="party_map")
            with col2:
                tan_col = st.selectbox("TAN column", ["None"] + cols, index=cols.index("TAN")+1 if "TAN" in cols else 0, key="tan_map")
            with col3:
                amt_col = st.selectbox("Books Amount column", cols, index=cols.index("Books Amount") if "Books Amount" in cols else 0, key="amt_map")
            with col4:
                tds_col = st.selectbox("Books TDS column", cols, index=cols.index("Books TDS") if "Books TDS" in cols else 0, key="tds_map")
            books_column_map = {
                "party": party_col,
                "tan": None if tan_col == "None" else tan_col,
                "amount": amt_col,
                "tds": tds_col
            }
    except Exception as e:
        st.warning("Could not preview books file. Please ensure it's a valid Excel.")

# ---------------------------- RUN BUTTON ----------------------------
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    if st.button("🚀 RUN ENTERPRISE ENGINE", use_container_width=True):
        if not txt_file or not books_file:
            st.warning("⚠️ Please upload both the 26AS and Books files to proceed.")
        elif not books_column_map:
            st.warning("⚠️ Please complete the column mapping above.")
        else:
            st.session_state.run_engine = True

# ---------------------------- CORE FUNCTIONS (cached) ----------------------------
@st.cache_data
def extract_26as_summary_and_section(file_bytes: bytes) -> pd.DataFrame:
    """Parse 26AS text file and return Part-I summary with section mapping."""
    text = file_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    summary_data, section_map = [], {}
    in_part1, current_tan = False, ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]
        for p in parts:
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p):
                current_tan = p

        sec = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), None)
        if current_tan and sec and current_tan not in section_map:
            section_map[current_tan] = sec

        if "PART-I - Details of Tax Deducted at Source" in line:
            in_part1 = True
            continue
        if in_part1 and line.startswith("^PART-"):
            break

        if in_part1 and len(parts) >= 6 and re.fullmatch(r"\d+", parts[0]):
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", parts[2]):
                try:
                    summary_data.append({
                        "Name of Deductor": parts[1],
                        "TAN of Deductor": parts[2],
                        "Total Amount Paid / Credited": float(parts[-3].replace(",", "")),
                        "Total Tax Deducted": float(parts[-2].replace(",", "")),
                        "Total TDS Deposited": float(parts[-1].replace(",", ""))
                    })
                except Exception:
                    pass

    df = pd.DataFrame(summary_data)
    if not df.empty:
        df.insert(0, "Section", df["TAN of Deductor"].map(section_map).fillna(""))
    return df

@st.cache_data(show_spinner=False)
def process_data(
    txt_bytes: bytes,
    books_bytes: bytes,
    column_map: Dict[str, Optional[str]],
    fuzzy_threshold: int,
    known_mappings: Dict[str, str]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Main reconciliation engine with batch fuzzy matching."""
    # Parse 26AS
    structured_26as = extract_26as_summary_and_section(txt_bytes)
    if structured_26as.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Load books with user mapping
    books_raw = pd.read_excel(io.BytesIO(books_bytes))
    # Map columns
    books = pd.DataFrame()
    books["Party Name"] = books_raw[column_map["party"]].fillna("").astype(str).str.strip().str.upper()
    if column_map["tan"]:
        books["TAN"] = books_raw[column_map["tan"]].fillna("").astype(str).str.strip().str.upper()
    else:
        books["TAN"] = ""
    books["Books Amount"] = pd.to_numeric(books_raw[column_map["amount"]], errors="coerce").fillna(0)
    books["Books TDS"] = pd.to_numeric(books_raw[column_map["tds"]], errors="coerce").fillna(0)

    # Aggregate duplicate (Party Name, TAN) combinations
    books = books.groupby(['Party Name', 'TAN'], as_index=False)[["Books Amount", "Books TDS"]].sum()

    # Prepare 26AS
    structured_26as["TAN of Deductor"] = structured_26as["TAN of Deductor"].astype(str).str.strip().str.upper()

    # ---- Exact matching on TAN ----
    exact_match = pd.merge(
        structured_26as, books,
        left_on="TAN of Deductor", right_on="TAN", how="inner"
    )
    exact_match["Match Type"] = "Exact (TAN)"

    # Remaining
    rem_26as = structured_26as[~structured_26as["TAN of Deductor"].isin(exact_match["TAN of Deductor"])].copy()
    rem_books = books[~books["TAN"].isin(exact_match["TAN"])].copy()

    # ---- Batch fuzzy matching ----
    fuzzy_records = []
    matched_book_indices = set()

    if not rem_26as.empty and not rem_books.empty:
        names_26 = rem_26as["Name of Deductor"].str.upper().tolist()
        names_book = rem_books["Party Name"].tolist()
        book_indices = rem_books.index.tolist()

        # Process.extract iterates over each query, but we can use cdist for many-to-many
        # However, process.cdist is efficient for comparing all pairs. We'll get best match per 26AS.
        matches = process.cdist(
            names_26, names_book,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=fuzzy_threshold,
            workers=-1  # use all cores
        )
        # matches is a list of lists; each sublist contains (score, index) pairs sorted descending.
        # We'll take the best match (first) if any.
        for idx_26, match_list in enumerate(matches):
            if match_list:
                best_score, best_book_idx_in_list = match_list[0]  # (score, index_in_names_book)
                best_book_idx = book_indices[best_book_idx_in_list]
                # Combine rows
                row_26 = rem_26as.iloc[idx_26]
                row_bk = rem_books.loc[best_book_idx]
                combined = row_26.to_dict()
                combined.update(row_bk.to_dict())
                combined["Match Type"] = "Fuzzy Match"
                fuzzy_records.append(combined)
                matched_book_indices.add(best_book_idx)
            else:
                # No match
                row_26 = rem_26as.iloc[idx_26]
                combined = row_26.to_dict()
                combined["Match Type"] = "Missing in Books"
                fuzzy_records.append(combined)

        # Books left unmatched
        for idx_bk, row_bk in rem_books.iterrows():
            if idx_bk not in matched_book_indices:
                combined = row_bk.to_dict()
                combined["Match Type"] = "Missing in 26AS"
                fuzzy_records.append(combined)
    else:
        # Handle cases where one side is empty
        for _, row_26 in rem_26as.iterrows():
            combined = row_26.to_dict()
            combined["Match Type"] = "Missing in Books"
            fuzzy_records.append(combined)
        for _, row_bk in rem_books.iterrows():
            combined = row_bk.to_dict()
            combined["Match Type"] = "Missing in 26AS"
            fuzzy_records.append(combined)

    fuzzy_df = pd.DataFrame(fuzzy_records) if fuzzy_records else pd.DataFrame()
    recon = pd.concat([exact_match, fuzzy_df], ignore_index=True)

    # Create deductor/party name column
    recon["Deductor / Party Name"] = np.where(
        recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""),
        recon["Name of Deductor"],
        recon["Party Name"]
    )

    # ---- Apply known mappings (dictionary override) ----
    if known_mappings:
        for tan_26, target_bk_name in known_mappings.items():
            # Find rows where this TAN is missing in books
            row_26_idx = recon[(recon['TAN of Deductor'] == tan_26) & (recon['Match Type'] == 'Missing in Books')].index
            # Find a book row with that party name that is missing in 26AS
            row_bk_idx = recon[(recon['Party Name'] == target_bk_name) & (recon['Match Type'] == 'Missing in 26AS')].index
            if not row_26_idx.empty and not row_bk_idx.empty:
                i_26, i_bk = row_26_idx[0], row_bk_idx[0]
                # Transfer book data to 26AS row
                recon.at[i_26, 'Party Name'] = recon.at[i_bk, 'Party Name']
                recon.at[i_26, 'TAN'] = recon.at[i_bk, 'TAN']
                recon.at[i_26, 'Books Amount'] = recon.at[i_bk, 'Books Amount']
                recon.at[i_26, 'Books TDS'] = recon.at[i_bk, 'Books TDS']
                recon.at[i_26, 'Match Type'] = 'Dictionary Match'
                # Drop the book row
                recon = recon.drop(index=i_bk)

    # ---- Recompute final TAN after all changes ----
    recon["Final TAN"] = np.where(
        recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""),
        recon["TAN of Deductor"],
        recon["TAN"]
    )

    return recon, structured_26as, books

# ---------------------------- MAIN EXECUTION ----------------------------
if st.session_state.run_engine:
    # Progress indicators
    progress_bar = st.progress(0, text="Initializing...")
    status_text = st.empty()

    # Step 1: Parse 26AS
    status_text.text("📄 Parsing 26AS file...")
    progress_bar.progress(10)
    time.sleep(0.5)  # small delay for visual feedback

    # Step 2: Process data
    status_text.text("🔄 Running reconciliation engine...")
    progress_bar.progress(30)
    recon, structured_26as, books = process_data(
        txt_file.getvalue(),
        books_file.getvalue(),
        books_column_map,
        fuzzy_threshold,
        known_mappings
    )

    if recon.empty:
        st.error("❌ No valid PART-I summary detected in the 26AS text file.")
        st.stop()

    progress_bar.progress(70)
    status_text.text("📊 Calculating metrics and building alerts...")

    # ---- Calculations ----
    num_cols = ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS"]
    for col in num_cols:
        recon[col] = pd.to_numeric(recon[col], errors="coerce").fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]
    recon['Effective Rate 26AS (%)'] = np.where(
        recon['Total Amount Paid / Credited'] > 0,
        (recon['Total TDS Deposited'] / recon['Total Amount Paid / Credited']) * 100,
        0
    ).round(2)

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
    reasons = [
        "Matched perfectly", "TDS value mismatch", "Matched ignoring name formatting",
        "TDS value mismatch", "Not recorded in Books", "Not reflected in 26AS"
    ]

    recon["Match Status"] = np.select(conditions_status, statuses, default="Unknown")
    recon["Reason for Difference"] = np.select(conditions_status, reasons, default="Unknown")

    final_recon = recon[[
        "Section", "Match Status", "Deductor / Party Name", "Final TAN",
        "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
        "Total TDS Deposited", "Books TDS", "Difference TDS", "Effective Rate 26AS (%)", "Reason for Difference"
    ]].rename(columns={"Final TAN": "TAN"})

    # Store in session state for filtering
    st.session_state.recon_df = final_recon

    progress_bar.progress(90)
    status_text.text("✅ Finalizing...")
    time.sleep(0.5)
    progress_bar.progress(100)
    status_text.text("Done!")
    progress_bar.empty()

    # ---------------------------- ALERTS (clickable) ----------------------------
    st.markdown("### 🚨 Compliance & Anomaly Alerts")
    col_alert1, col_alert2, col_alert3 = st.columns(3)

    # Alert 1: TDS rate anomalies
    anomalies = recon[(recon['Effective Rate 26AS (%)'] > 0) & (~recon['Effective Rate 26AS (%)'].isin(STANDARD_TDS_RATES))]
    if not anomalies.empty:
        top_anomaly = anomalies.nlargest(1, 'Total TDS Deposited').iloc[0]
        with col_alert1:
            clicked = st.markdown(f"""
            <div class="alert-box-blue" onclick="alert('Filtering to show anomalies...')" id="alert_anomaly">
                <b>🔎 TDS Rate Anomaly Detected:</b> Non-standard deduction rates identified.<br>
                <span style="font-size: 0.95rem;"><i>👉 <b>{top_anomaly['Deductor / Party Name']}</b> deducted TDS at <b>{top_anomaly['Effective Rate 26AS (%)']}%</b>.</i></span>
            </div>
            """, unsafe_allow_html=True)
            # Use a button-like behavior with session state
            if st.button("View Anomalies", key="btn_anomaly"):
                st.session_state.filter_status = "Anomaly"

    # Alert 2: Missing in books
    miss_in_books = recon[recon["Match Status"] == "Missing in Books"]
    if not miss_in_books.empty and miss_in_books["Total TDS Deposited"].sum() > 0:
        top_missed = miss_in_books.loc[miss_in_books["Total TDS Deposited"].idxmax()]
        with col_alert2:
            st.markdown(f"""
            <div class="alert-box-red">
                <b>URGENT: Unclaimed TDS Leakage!</b> ₹ {miss_in_books["Total TDS Deposited"].sum():,.2f} is in 26AS but <b>MISSING</b> in books.<br>
                <span style="font-size: 0.95rem;"><i>👉 Top Missing Party: <b>{top_missed['Deductor / Party Name']}</b> (₹ {top_missed['Total TDS Deposited']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View Missing in Books", key="btn_miss_books"):
                st.session_state.filter_status = "Missing in Books"

    # Alert 3: Missing in 26AS
    miss_in_26as = recon[recon["Match Status"] == "Missing in 26AS"]
    if not miss_in_26as.empty and miss_in_26as["Books TDS"].sum() > 0:
        top_excess = miss_in_26as.loc[miss_in_26as["Books TDS"].idxmax()]
        with col_alert3:
            st.markdown(f"""
            <div class="alert-box-yellow">
                <b>COMPLIANCE RISK:</b> ₹ {miss_in_26as["Books TDS"].sum():,.2f} of TDS is claimed in Books but <b>NOT uploaded in 26AS</b>.<br>
                <span style="font-size: 0.95rem;"><i>👉 Top Unreflected Party: <b>{top_excess['Deductor / Party Name']}</b> (₹ {top_excess['Books TDS']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View Missing in 26AS", key="btn_miss_26as"):
                st.session_state.filter_status = "Missing in 26AS"

    # ---------------------------- FILTERED TABLE (if alert clicked) ----------------------------
    if st.session_state.filter_status:
        st.markdown(f"#### 🔍 Filtered: {st.session_state.filter_status}")
        if st.session_state.filter_status == "Anomaly":
            filtered_df = final_recon[final_recon["Effective Rate 26AS (%)"].apply(lambda x: x not in STANDARD_TDS_RATES and x > 0)]
        else:
            filtered_df = final_recon[final_recon["Match Status"] == st.session_state.filter_status]
        st.dataframe(filtered_df, use_container_width=True, height=300)
        if st.button("Clear Filter"):
            st.session_state.filter_status = None
            st.rerun()

    # ---------------------------- DASHBOARD ----------------------------
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
            font=dict(family="Inter")
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with c2:
        section_summary = recon.groupby('Section')[['Total TDS Deposited', 'Books TDS']].sum().reset_index()
        section_summary = section_summary[section_summary['Section'] != ""]
        if not section_summary.empty:
            fig_sec = px.bar(
                section_summary, x='Section', y=['Total TDS Deposited', 'Books TDS'],
                barmode='group', title="TDS Claimed vs Reflected by Section"
            )
            fig_sec.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter"),
                legend_title_text=""
            )
            st.plotly_chart(fig_sec, use_container_width=True)
        else:
            st.info("No section data available.")

    # ---------------------------- EXPORT LEARNED MAPPINGS ----------------------------
    learned = recon[recon["Match Type"].isin(["Fuzzy Match", "Dictionary Match"])][["TAN of Deductor", "Party Name"]].drop_duplicates()
    if not learned.empty:
        st.markdown("### 🧠 Learned Mappings (download to build your dictionary)")
        st.dataframe(learned, use_container_width=True)
        csv_learned = learned.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Learned Mappings", csv_learned, "learned_mappings.csv", mime="text/csv")

    # ---------------------------- EXCEL EXPORT (with tables) ----------------------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Formats
        brand_format = workbook.add_format({"bold": True, "font_size": 18, "bg_color": "#0f172a", "font_color": "#38bdf8", "align": "center", "valign": "vcenter"})
        dev_format = workbook.add_format({"italic": True, "font_size": 10, "bg_color": "#0f172a", "font_color": "#94a3b8", "align": "center"})
        header_format = workbook.add_format({"bold": True, "bg_color": "#0052cc", "font_color": "white", "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"})
        total_format = workbook.add_format({"bold": True, "bg_color": "#f2f2f2", "border": 1, "num_format": "#,##0.00"})

        # --- Dashboard sheet ---
        dash = workbook.add_worksheet("Dashboard")
        dash.hide_gridlines(2)

        fy_title = f"(FY: {st.session_state.extracted_info['fy']})" if st.session_state.extracted_info['fy'] != "Unknown" else ""
        dash.merge_range("A1:M2", f"26AS ENTERPRISE RECON - EXECUTIVE SUMMARY {fy_title}", brand_format)
        dash.merge_range("A3:M3", "Developed by ABHISHEK JAKKULA | jakkulaabhishek5@gmail.com", dev_format)

        # Status summary table
        dash.write_row("B5", ["Match Status", "Record Count", "TDS Impact (26AS)", "TDS Impact (Books)"], header_format)
        dash.set_column('B:B', 25)
        dash.set_column('C:E', 18)

        status_list = ["Exact Match", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
        for i, status in enumerate(status_list):
            row = 5 + i
            dash.write(row, 1, status)
            # Use table references later; for now we write formulas assuming Reconciliation sheet has data from row 3 onward
            # We'll use dynamic range: Reconciliation!$B$3:$B$1048576
            dash.write_formula(row, 2, f'=COUNTIF(Reconciliation!$B:$B, "{status}")')
            dash.write_formula(row, 3, f'=SUMIF(Reconciliation!$B:$B, "{status}", Reconciliation!$H:$H)')
            dash.write_formula(row, 4, f'=SUMIF(Reconciliation!$B:$B, "{status}", Reconciliation!$I:$I)')

        # Top 10 suppliers
        top_26as = final_recon.nlargest(10, "Total TDS Deposited")[["Deductor / Party Name", "Total Amount Paid / Credited", "Total TDS Deposited"]]
        top_books = final_recon.nlargest(10, "Books TDS")[["Deductor / Party Name", "Books Amount", "Books TDS"]]

        dash.write("G5", "Top 10 Suppliers (26AS)", header_format)
        dash.write_row("G6", ["Deductor / Party Name", "Total Amount (26AS)", "Total TDS (26AS)"], header_format)
        for i, (_, row) in enumerate(top_26as.iterrows()):
            dash.write_row(i + 6, 6, [row["Deductor / Party Name"], row["Total Amount Paid / Credited"], row["Total TDS Deposited"]])
        dash.set_column('G:G', 35)
        dash.set_column('H:I', 18)

        dash.write("K5", "Top 10 Suppliers (Books)", header_format)
        dash.write_row("K6", ["Deductor / Party Name", "Books Amount", "Books TDS"], header_format)
        for i, (_, row) in enumerate(top_books.iterrows()):
            dash.write_row(i + 6, 10, [row["Deductor / Party Name"], row["Books Amount"], row["Books TDS"]])
        dash.set_column('K:K', 35)
        dash.set_column('L:M', 18)

        # Pie charts
        pie_chart = workbook.add_chart({'type': 'pie'})
        pie_chart.add_series({
            'name': 'Status Distribution',
            'categories': '=Dashboard!$B$6:$B$10',
            'values': '=Dashboard!$C$6:$C$10',
            'data_labels': {'percentage': True, 'show_leader_lines': True}
        })
        dash.insert_chart('B13', pie_chart)

        pie_26as = workbook.add_chart({'type': 'pie'})
        pie_26as.add_series({
            'name': 'Top 10 26AS',
            'categories': f'=Dashboard!$G$7:$G${6 + len(top_26as)}',
            'values': f'=Dashboard!$I$7:$I${6 + len(top_26as)}',
            'data_labels': {'percentage': True}
        })
        pie_26as.set_title({'name': 'Top 10 Deductors (26AS)'})
        dash.insert_chart('G18', pie_26as)

        pie_books = workbook.add_chart({'type': 'pie'})
        pie_books.add_series({
            'name': 'Top 10 Books',
            'categories': f'=Dashboard!$K$7:$K${6 + len(top_books)}',
            'values': f'=Dashboard!$M$7:$M${6 + len(top_books)}',
            'data_labels': {'percentage': True}
        })
        pie_books.set_title({'name': 'Top 10 Parties (Books)'})
        dash.insert_chart('K18', pie_books)

        # --- Reconciliation sheet as a table ---
        sheet_recon = workbook.add_worksheet("Reconciliation")
        # Write headers
        for col_num, col_name in enumerate(final_recon.columns):
            sheet_recon.write(1, col_num, col_name, header_format)
        # Write data starting from row 2 (0-indexed row 2 = third row)
        for r, row in enumerate(final_recon.itertuples(), start=2):
            for c, value in enumerate(row[1:]):  # skip index
                sheet_recon.write(r, c, value)

        # Create a table
        table_range = f"A2:{chr(65 + len(final_recon.columns)-1)}{len(final_recon)+1}"  # +1 for header row offset
        sheet_recon.add_table(table_range, {
            'columns': [{'header': col} for col in final_recon.columns],
            'style': 'Table Style Medium 2',
            'total_row': False,
            'autofilter': True
        })
        # Add subtotal formulas above the table (row 0)
        for col_num, col_name in enumerate(final_recon.columns):
            if pd.api.types.is_numeric_dtype(final_recon[col_name]) and col_name != "Effective Rate 26AS (%)":
                sheet_recon.write_formula(0, col_num, f'=SUBTOTAL(9,{chr(65+col_num)}3:{chr(65+col_num)}{len(final_recon)+1})', total_format)

        # Auto-width columns
        for col_num, col_name in enumerate(final_recon.columns):
            max_len = max(final_recon[col_name].astype(str).map(len).max(), len(str(col_name))) + 2
            sheet_recon.set_column(col_num, col_num, min(max_len, 45))

        # --- Raw data sheets ---
        structured_26as.to_excel(writer, sheet_name="26AS Raw", index=False)
        sheet_26_raw = writer.sheets["26AS Raw"]
        for i, col in enumerate(structured_26as.columns):
            max_len = max(structured_26as[col].astype(str).map(len).max(), len(str(col))) + 2
            sheet_26_raw.set_column(i, i, min(max_len, 45))

        books.to_excel(writer, sheet_name="Books Raw", index=False)
        sheet_bk_raw = writer.sheets["Books Raw"]
        for i, col in enumerate(books.columns):
            max_len = max(books[col].astype(str).map(len).max(), len(str(col))) + 2
            sheet_bk_raw.set_column(i, i, min(max_len, 45))

    output.seek(0)
    st.success("✅ Enterprise Reconciliation completed successfully.")

    fy_safe = st.session_state.extracted_info['fy'].replace('-', '_') if st.session_state.extracted_info['fy'] != 'Unknown' else 'Latest'

    col_dl1, col_dl2, col_dl3 = st.columns([1,2,1])
    with col_dl2:
        st.download_button(
            "⚡ Download Final Excel Report",
            output,
            f"26AS_Recon_FY_{fy_safe}.xlsx",
            use_container_width=True
        )
