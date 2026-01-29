import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

# ---------------- PAGE CONFIG ----------------

st.set_page_config(page_title="26AS Reconciliation Tool", layout="wide")

# ---------------- COMICAL UI + BRANDING ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #fceabb, #f8b500);
    background-attachment: fixed;
}

.main-title {
    font-size: 40px;
    font-weight: 800;
    color: #2c2c2c;
    text-align: center;
    text-shadow: 2px 2px #ffffff;
}

.sub-title {
    font-size: 20px;
    font-weight: 600;
    color: #444;
    text-align: center;
    margin-bottom: 30px;
}

.block-container {
    background-color: rgba(255,255,255,0.85);
    padding: 2rem;
    border-radius: 18px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 26AS Reconciliation Automation Tool</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Tool developed by - Abhishek Jakkula</div>', unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

def extract_26as_data(pdf_file):

    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += "\n" + t

    records = []

    deductor_blocks = re.split(r"Name of Deductor", full_text, flags=re.I)

    for block in deductor_blocks[1:]:

        name = re.search(r":\s*(.*?)\s*TAN", block, re.I)
        tan = re.search(r"TAN\s*:\s*([A-Z0-9]+)", block, re.I)

        deductor_name = clean(name.group(1)) if name else ""
        tan_no = tan.group(1) if tan else ""

        rows = re.findall(
            r"(\d{2}/\d{2}/\d{4})\s+([\d,]+\.\d{2}|\d+)\s+([\d,]+\.\d{2}|\d+)",
            block
        )

        for r in rows:
            records.append({
                "Deductor Name": deductor_name,
                "TAN": tan_no,
                "Transaction Date": r[0],
                "Amount Paid": float(r[1].replace(",", "")),
                "TDS Deposited": float(r[2].replace(",", ""))
            })

    return pd.DataFrame(records)

# ---------------- UI ----------------

st.markdown("### 📂 Upload files")

col1, col2 = st.columns(2)

with col1:
    pdf_file = st.file_uploader("Upload Form 26AS PDF", type=["pdf"])

with col2:
    books_file = st.file_uploader("Upload Books Excel (Name, TAN, Books Amount, Books TDS)", type=["xlsx"])

if pdf_file and books_file and st.button("🚀 Run 26AS Reconciliation"):

    with st.spinner("Reading 26AS and processing data..."):
        df_26as = extract_26as_data(pdf_file)

    if df_26as.empty:
        st.error("❌ No TDS data found in 26AS PDF.")
        st.stop()

    df_books = pd.read_excel(books_file)

    required_cols = {"Name","TAN","Books Amount","Books TDS"}
    if not required_cols.issubset(df_books.columns):
        st.error("❌ Books file must contain columns: Name, TAN, Books Amount, Books TDS")
        st.stop()

    # ---------------- CLEANING ----------------

    df_books["TAN"] = df_books["TAN"].astype(str).str.upper().str.strip()
    df_26as["TAN"] = df_26as["TAN"].astype(str).str.upper().str.strip()

    # ---------------- GROUPING ----------------

    g26 = df_26as.groupby("TAN").agg({
        "Amount Paid":"sum",
        "TDS Deposited":"sum"
    }).reset_index()

    gb = df_books.groupby("TAN").agg({
        "Books Amount":"sum",
        "Books TDS":"sum"
    }).reset_index()

    # ---------------- MERGE ----------------

    recon = pd.merge(g26, gb, on="TAN", how="outer").fillna(0)

    recon["Amount Difference"] = recon["Amount Paid"] - recon["Books Amount"]
    recon["TDS Difference"] = recon["TDS Deposited"] - recon["Books TDS"]

    recon["Status"] = recon.apply(
        lambda x: "Matched ✅" if x["Amount Difference"]==0 and x["TDS Difference"]==0 else "Mismatch ❌",
        axis=1
    )

    mismatches = recon[recon["Status"]=="Mismatch ❌"]

    # ---------------- DISPLAY ----------------

    st.success("✅ Reconciliation completed successfully")

    st.subheader("🔍 TAN-wise Reconciliation Report")
    st.dataframe(recon, use_container_width=True)

    st.subheader("⚠️ Mismatch Report")
    st.dataframe(mismatches, use_container_width=True)

    # ---------------- EXCEL OUTPUT ----------------

    file_name = f"26AS_Reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df_26as.to_excel(writer, sheet_name="Raw_26AS", index=False)
        df_books.to_excel(writer, sheet_name="Books_Data", index=False)
        recon.to_excel(writer, sheet_name="TAN_Reconciliation", index=False)
        mismatches.to_excel(writer, sheet_name="Mismatch_Report", index=False)

    with open(file_name,"rb") as f:
        st.download_button("📥 Download Reconciliation Excel", f, file_name=file_name)
