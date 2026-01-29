import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AJ 26AS Tool", layout="wide")

# ---------------- BRAND UI + LOGO ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #fceabb, #f8b500);
    background-attachment: fixed;
}

.logo-box {
    margin: auto;
    width: 240px;
    height: 110px;
    background: black;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0px 6px 20px rgba(0,0,0,0.4);
    border: 3px solid #d4af37;
}

.logo-text {
    font-size: 64px;
    font-weight: 900;
    color: #e10600;
    letter-spacing: 6px;
    font-family: 'Trebuchet MS', sans-serif;
}

.krishna {
    font-size: 26px;
    color: gold;
    position: absolute;
    margin-top: 70px;
    margin-left: 130px;
}

.title {
    text-align:center;
    font-size: 42px;
    font-weight: 900;
    color: #2c2c2c;
    margin-top: 15px;
    text-shadow: 2px 2px white;
}

.sub {
    text-align:center;
    font-size: 20px;
    font-weight: 700;
    color: #333;
}

.block-container {
    background-color: rgba(255,255,255,0.90);
    padding: 2rem;
    border-radius: 18px;
}
</style>

<div style="position:relative; width:100%; text-align:center;">
    <div class="logo-box">
        <div class="logo-text">AJ</div>
    </div>
    <div class="krishna">🦚 🎶</div>
</div>

<div class="title">26AS Reconciliation Automation Tool</div>
<div class="sub">Tool developed by - Abhishek Jakkula</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ---------------- SAMPLE BOOKS TEMPLATE ----------------
sample_df = pd.DataFrame({
    "Name": ["ABC Pvt Ltd", "XYZ Solutions"],
    "TAN": ["HYDA12345A", "MUMA67890B"],
    "Books Amount": [500000, 250000],
    "Books TDS": [50000, 25000]
})

buf = BytesIO()
sample_df.to_excel(buf, index=False)
buf.seek(0)

st.download_button("📥 Download Sample Books Excel Template", buf, "Sample_Books_Template.xlsx")
st.info("📌 Please upload **TRACES Form 26AS PDF only** (text-based, not scanned).")

st.markdown("---")

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
    blocks = re.split(r"Name of Deductor", full_text, flags=re.I)

    for block in blocks[1:]:
        name = re.search(r":\s*(.*?)\s*TAN", block, re.I)
        tan = re.search(r"TAN\s*:\s*([A-Z0-9]+)", block, re.I)
        section = re.search(r"Section\s*:\s*(\d+[A-Z]*)", block, re.I)

        deductor_name = clean(name.group(1)) if name else ""
        tan_no = tan.group(1) if tan else ""
        sec = section.group(1) if section else "NA"

        rows = re.findall(r"(\d{2}/\d{2}/\d{4})\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)", block)

        for r in rows:
            records.append({
                "Section": sec,
                "Deductor Name": deductor_name,
                "TAN": tan_no,
                "Transaction Date": r[0],
                "Amount Paid": float(r[1].replace(",", "")),
                "TDS Deposited": float(r[2].replace(",", ""))
            })

    return pd.DataFrame(records)

# ---------------- FILE UPLOAD ----------------
col1, col2 = st.columns(2)
with col1:
    pdf_file = st.file_uploader("Upload TRACES Form 26AS PDF", type=["pdf"])
with col2:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

if pdf_file and books_file and st.button("🚀 Run 26AS Reconciliation"):

    df_26as = extract_26as_data(pdf_file)
    if df_26as.empty:
        st.error("No TDS data detected.")
        st.stop()

    df_books = pd.read_excel(books_file)
    required = {"Name","TAN","Books Amount","Books TDS"}
    if not required.issubset(df_books.columns):
        st.error("Books file must contain: Name, TAN, Books Amount, Books TDS")
        st.stop()

    df_26as["TAN"] = df_26as["TAN"].str.upper().str.strip()
    df_books["TAN"] = df_books["TAN"].astype(str).str.upper().str.strip()

    party_summary = df_26as.groupby(["TAN","Deductor Name"]).agg({"Amount Paid":"sum","TDS Deposited":"sum"}).reset_index()
    section_pivot = df_26as.pivot_table(values="TDS Deposited", index="Section", aggfunc="sum").reset_index()

    g26 = df_26as.groupby("TAN").agg({"Amount Paid":"sum","TDS Deposited":"sum"}).reset_index()
    gb = df_books.groupby("TAN").agg({"Books Amount":"sum","Books TDS":"sum"}).reset_index()

    recon = pd.merge(g26, gb, on="TAN", how="outer").fillna(0)
    recon["Amount Difference"] = recon["Amount Paid"] - recon["Books Amount"]
    recon["TDS Difference"] = recon["TDS Deposited"] - recon["Books TDS"]

    recon["Risk Flag"] = recon.apply(lambda x:
        "High Risk 🔴" if abs(x["TDS Difference"]) > 10000 else
        "Medium Risk 🟠" if abs(x["TDS Difference"]) > 0 else
        "No Risk 🟢", axis=1)

    missing_in_books = recon[(recon["Books Amount"]==0) & (recon["Amount Paid"]>0)]

    st.success("✅ Reconciliation completed")
    st.subheader("🔍 TAN-wise Reconciliation")
    st.dataframe(recon, use_container_width=True)

    st.subheader("🏢 Party-wise Summary")
    st.dataframe(party_summary, use_container_width=True)

    st.subheader("📊 Section-wise TDS Pivot")
    st.dataframe(section_pivot, use_container_width=True)

    st.subheader("⚠️ Missing in Books")
    st.dataframe(missing_in_books, use_container_width=True)

    file_name = f"AJ_26AS_Reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df_26as.to_excel(writer, sheet_name="Raw_26AS", index=False)
        df_books.to_excel(writer, sheet_name="Books_Data", index=False)
        recon.to_excel(writer, sheet_name="TAN_Reconciliation", index=False)
        missing_in_books.to_excel(writer, sheet_name="Missing_in_Books", index=False)
        party_summary.to_excel(writer, sheet_name="Party_Summary", index=False)
        section_pivot.to_excel(writer, sheet_name="Section_Pivot", index=False)

    with open(file_name,"rb") as f:
        st.download_button("📥 Download Full Reconciliation Excel", f, file_name)
