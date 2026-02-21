import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import difflib
import plotly.express as px

st.set_page_config(page_title="26AS Professional Reconciliation", layout="wide")

# ---------------- GOOGLE-LIKE PROFESSIONAL UI ----------------
st.markdown("""
<style>
.stApp {
    background:#ffffff;
    font-family: 'Segoe UI', sans-serif;
    color:#000000;
}
.block-container {
    background:#ffffff;
    padding:2.2rem;
}
/* HEADER */
.header-box {
    background: linear-gradient(90deg,#f8fafc,#eef2ff);
    padding:34px;
    border-radius:18px;
    margin-bottom:24px;
    border:1px solid #c7d2fe;
    box-shadow:0 10px 25px rgba(0,0,0,0.06);
}
.header-title {color:#1e3a8a; font-size:38px; font-weight:900;}
.header-sub {color:#0f172a; font-size:20px; font-weight:600;}

/* ZONE */
.zone {
    background:#ffffff;
    padding:18px;
    border-radius:14px;
    border:1px solid #e5e7eb;
    box-shadow:0 6px 16px rgba(0,0,0,0.06);
    margin-bottom:18px;
}
/* FILE UPLOADER */
[data-testid="stFileUploader"] {
    background: linear-gradient(135deg,#e0f2fe,#bae6fd) !important;
    border-radius:18px !important;
    padding:22px !important;
    border:2px dashed #0284c7 !important;
    box-shadow:0 8px 22px rgba(2,132,199,0.25);
}
[data-testid="stFileUploader"] * {
    color:darkred !important;
    font-weight:600 !important;
}
[data-testid="stFileUploader"] button {
    background: linear-gradient(90deg,#2563eb,#06b6d4) !important;
    color:white !important;
    border-radius:12px !important;
    padding:8px 18px !important;
    font-weight:700 !important;
    border:none !important;
    box-shadow:0 6px 14px rgba(37,99,235,0.4);
}
[data-testid="stFileUploader"] button:hover {
    background: linear-gradient(90deg,#1d4ed8,#0891b2) !important;
    transform:scale(1.04);
}
/* Main buttons */
.stButton button, .stDownloadButton button {
    background: linear-gradient(90deg,#2563eb,#06b6d4);
    color:white !important;
    border-radius:12px;
    padding:12px 26px;
    font-weight:800;
    border:none;
    box-shadow:0 8px 22px rgba(37,99,235,0.35);
}
.stButton button:hover, .stDownloadButton button:hover {
    transform:scale(1.05);
}
/* Alert Boxes */
.alert-box-red {
    background-color: #fef2f2; border-left: 5px solid #ef4444; 
    padding: 15px; border-radius: 8px; margin-bottom: 12px;
}
.alert-box-yellow {
    background-color: #fffbeb; border-left: 5px solid #f59e0b; 
    padding: 15px; border-radius: 8px; margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
    <div class="header-title">26AS PROFESSIONAL RECONCILIATION TOOL</div>
    <div class="header-sub">26AS VS BOOKS (AI-Powered Matching)</div>
    <p style="margin-top:8px; color:#475569; font-weight:600;">Developed by Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="zone">📄 Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

# ---------------- SAMPLE BOOKS TEMPLATE DOWNLOAD ----------------
sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd", "XYZ Corp"],
    "TAN": ["HYDA00000A", ""],
    "Books Amount": [100000, 50000],
    "Books TDS": [10000, 5000]
})

buf = io.BytesIO()
sample_books.to_excel(buf, index=False)
buf.seek(0)

col1, col2 = st.columns([1, 2])
with col1:
    st.download_button("⬇ Download Sample Books Excel", buf, "Sample_Books_Template.xlsx")

st.markdown("---")

# ---------------- FILE UPLOAD ----------------
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- EXACT SUMMARY + SECTION EXTRACTOR ----------------
@st.cache_data
def extract_26as_summary_and_section(file_bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    summary_data = []
    section_map = {}
    in_part1 = False
    current_tan = ""

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
                        "Total Amount Paid / Credited": float(parts[-3].replace(",","")),
                        "Total Tax Deducted": float(parts[-2].replace(",","")),
                        "Total TDS Deposited": float(parts[-1].replace(",",""))
                    })
                except Exception:
                    pass

    df = pd.DataFrame(summary_data)
    if not df.empty:
        df.insert(0, "Section", df["TAN of Deductor"].map(section_map).fillna(""))
    return df

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):
    if not txt_file or not books_file:
        st.warning("⚠️ Please upload both files.")
        st.stop()

    with st.spinner("Running AI Matching Engine..."):
        structured_26as = extract_26as_summary_and_section(txt_file.getvalue())

        if structured_26as.empty:
            st.error("❌ No valid PART-I summary detected in the text file.")
            st.stop()

        books = pd.read_excel(books_file)

        # File Validation
        required_cols = ["Party Name", "TAN", "Books Amount", "Books TDS"]
        for col in required_cols:
            if col not in books.columns:
                books[col] = "" if col in ["Party Name", "TAN"] else 0

        # Data Cleaning
        structured_26as["TAN of Deductor"] = structured_26as["TAN of Deductor"].astype(str).str.strip().str.upper()
        books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()

        # ================= FUZZY MATCHING LOGIC =================
        # 1. Exact Match on TAN
        exact_match = pd.merge(structured_26as, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
        exact_match["Match Status"] = "Exact (TAN)"

        # Get remaining unmatched
        rem_26as = structured_26as[~structured_26as["TAN of Deductor"].isin(exact_match["TAN of Deductor"])]
        rem_books = books[~books["TAN"].isin(exact_match["TAN"])]

        # 2. Fuzzy Match on Name
        fuzzy_records = []
        matched_books_indices = set()

        for idx_26, row_26 in rem_26as.iterrows():
            name_26 = str(row_26["Name of Deductor"]).upper()
            best_match = None
            best_score = 0
            best_book_idx = -1

            for idx_bk, row_bk in rem_books.iterrows():
                if idx_bk in matched_books_indices: continue
                name_bk = str(row_bk["Party Name"]).upper()
                
                # Calculate similarity ratio
                score = difflib.SequenceMatcher(None, name_26, name_bk).ratio()
                if score > best_score and score >= 0.70:  # 70% similarity threshold
                    best_score = score
                    best_match = row_bk
                    best_book_idx = idx_bk

            if best_match is not None:
                combined = row_26.to_dict()
                combined.update(best_match.to_dict())
                combined["Match Status"] = f"Fuzzy Name ({int(best_score*100)}%)"
                fuzzy_records.append(combined)
                matched_books_indices.add(best_book_idx)
            else:
                combined = row_26.to_dict()
                combined["Match Status"] = "Missing in Books"
                fuzzy_records.append(combined)

        # 3. Add remaining books (Not in 26AS)
        for idx_bk, row_bk in rem_books.iterrows():
            if idx_bk not in matched_books_indices:
                combined = row_bk.to_dict()
                combined["Match Status"] = "Missing in 26AS"
                fuzzy_records.append(combined)

        # Combine everything
        fuzzy_df = pd.DataFrame(fuzzy_records) if fuzzy_records else pd.DataFrame()
        recon = pd.concat([exact_match, fuzzy_df], ignore_index=True)

        # Fill NaNs for numeric calculations
        numeric_cols = ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS"]
        for col in numeric_cols:
            if col in recon.columns:
                recon[col] = recon[col].fillna(0)

        # Calculations
        recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
        recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

        # Cleanup display texts
        recon["Name of Deductor"] = recon["Name of Deductor"].fillna("Not in 26AS")
        recon["Party Name"] = recon.get("Party Name", pd.Series("Not in Books")).fillna("Not in Books")

        final_recon = recon[[
            "Section", "Match Status", "Name of Deductor", "Party Name", "TAN of Deductor", "TAN",
            "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
            "Total TDS Deposited", "Books TDS", "Difference TDS"
        ]]

        # --- Dashboard Metrics ---
        st.markdown("### 📊 Reconciliation Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total TDS in 26AS", f"₹ {recon['Total TDS Deposited'].sum():,.2f}")
        m2.metric("Total TDS in Books", f"₹ {recon['Books TDS'].sum():,.2f}")
        net_diff = recon['Total TDS Deposited'].sum() - recon['Books TDS'].sum()
        m3.metric("Net Variance", f"₹ {net_diff:,.2f}", delta=f"₹ {net_diff:,.2f}", delta_color="inverse")

        # --- High Caution / Analytics ---
        st.markdown("### 🚨 High Caution & Action Required")
        
        miss_in_books = recon[recon["Match Status"] == "Missing in Books"]
        if not miss_in_books.empty and miss_in_books["Total TDS Deposited"].sum() > 0:
            total_missed = miss_in_books["Total TDS Deposited"].sum()
            top_missed = miss_in_books.loc[miss_in_books["Total TDS Deposited"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-red">
                <b>URGENT: Unclaimed TDS!</b> ₹ {total_missed:,.2f} is reflecting in 26AS but is completely <b>MISSING</b> in your books.<br>
                <i>👉 Top Missing Party: <b>{top_missed['Name of Deductor']}</b> (₹ {top_missed['Total TDS Deposited']:,.2f}). Ensure you record this to claim the credit.</i>
            </div>
            """, unsafe_allow_html=True)

        miss_in_26as = recon[recon["Match Status"] == "Missing in 26AS"]
        if not miss_in_26as.empty and miss_in_26as["Books TDS"].sum() > 0:
            total_excess = miss_in_26as["Books TDS"].sum()
            top_excess = miss_in_26as.loc[miss_in_26as["Books TDS"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-yellow">
                <b>COMPLIANCE RISK:</b> ₹ {total_excess:,.2f} of TDS is claimed in your Books but <b>NOT in 26AS</b>.<br>
                <i>👉 Top Unreflected Party: <b>{top_excess['Party Name']}</b> (₹ {top_excess['Books TDS']:,.2f}). Follow up immediately to ensure they file their TDS returns.</i>
            </div>
            """, unsafe_allow_html=True)

        # --- Charts ---
        st.markdown("### 📈 Top 10 Analytics")
        c1, c2 = st.columns(2)
        
        with c1:
            top_26as = structured_26as.nlargest(10, "Total TDS Deposited")
            fig1 = px.pie(top_26as, names="Name of Deductor", values="Total TDS Deposited", title="Top 10 Deductors in 26AS (by TDS)", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            top_books = books.nlargest(10, "Books TDS")
            fig2 = px.pie(top_books, names="Party Name", values="Books TDS", title="Top 10 Parties in Books (by TDS)", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

        # --- Excel Export ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            structured_26as.to_excel(writer, sheet_name="26AS_Party_Wise", index=False)
            books.to_excel(writer, sheet_name="Books_Data", index=False)
            final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

            workbook = writer.book
            worksheet = writer.sheets["26AS_vs_Books"]
            header_format = workbook.add_format({'bold': True, 'bg_color': '#1e3a8a', 'font_color': 'white', 'border': 1})
            
            for col_num, value in enumerate(final_recon.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, min(25, max(14, len(str(value)) + 2)))

        output.seek(0)

        st.success("✅ Smart Reconciliation completed successfully.")

        col_dl, _ = st.columns([1,2])
        with col_dl:
            st.download_button("📥 Download Final Reconciliation Excel", output, "26AS_Reconciliation_Pro.xlsx")

        st.subheader("Preview – 26AS vs Books")
        st.dataframe(final_recon.head(100), use_container_width=True)
