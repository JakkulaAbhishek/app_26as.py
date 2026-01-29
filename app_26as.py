import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="26AS Professional Reconciliation", layout="wide")

# ---------------- PROFESSIONAL COLORED UI ----------------
st.markdown("""
<style>

.stApp {
    background:#f4f6f9;
    font-family: 'Segoe UI', sans-serif;
    color:#000000;
}

.block-container {
    background:#ffffff;
    padding:2.2rem;
    border-radius:16px;
}

/* Header */
.header-box {
    background: linear-gradient(90deg, #0f172a, #1e3a8a);
    padding:28px;
    border-radius:16px;
    margin-bottom:25px;
    color:white;
}

.header-box h1, .header-box h3, .header-box p {
    color:white !important;
}

/* Section cards */
.card {
    background:#ffffff;
    border-radius:14px;
    padding:18px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:18px;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background:#f8fafc;
    border:2px dashed #2563eb;
    border-radius:12px;
    padding:18px;
}

/* Buttons */
.stButton button, .stDownloadButton button {
    background: linear-gradient(90deg,#2563eb,#06b6d4);
    color:white;
    border-radius:10px;
    padding:10px 20px;
    font-weight:600;
    border:none;
}

.stButton button:hover, .stDownloadButton button:hover {
    opacity:0.9;
}

/* Tables */
[data-testid="stDataFrame"] {
    background:white;
    border-radius:12px;
    border:1px solid #e5e7eb;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
    <h1>26AS PROFESSIONAL RECONCILIATION SYSTEM</h1>
    <h3>Exact TRACES Matching Engine</h3>
    <p>Developed by Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

# ---------------- INFO ----------------
st.markdown('<div class="card">Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

# ---------------- SAMPLE TEMPLATE ----------------
sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd"],
    "TAN": ["HYDA00000A"],
    "Books Amount": [100000],
    "Books TDS": [10000]
})

buf = BytesIO()
sample_books.to_excel(buf, index=False)
buf.seek(0)

st.download_button("⬇ Download Sample Books Excel", buf, "Sample_Books_Template.xlsx")

# ---------------- FILE UPLOAD ----------------
txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- EXACT TRACES PARSER ----------------
def extract_26as_from_text(file):
    text = file.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()

    records = []
    current_name = ""
    current_tan = ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]

        # TAN + Name
        for i, p in enumerate(parts):
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p):
                current_tan = p
                if i > 0:
                    current_name = parts[i-1]

        # Section
        section = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), "")

        # Numbers in order
        nums = []
        for p in parts:
            q = p.replace(",", "")
            if re.fullmatch(r"\d+(\.\d+)?", q):
                nums.append(float(q))

        # TRACES structure: amount appears before TDS
        if current_name and current_tan and section and len(nums) >= 4:
            try:
                amount = nums[-4]   # usually "Amount Paid/Credited"
                tds = nums[-3]      # usually "Tax Deducted"

                records.append({
                    "Section": section,
                    "Name of Deductor": current_name,
                    "TAN of Deductor": current_tan,
                    "Amount": amount,
                    "TDS": tds
                })
            except:
                pass

    return pd.DataFrame(records)

# ---------------- PROCESS ----------------
if st.button("RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    raw26 = extract_26as_from_text(txt_file)

    if raw26.empty:
        st.error("No usable 26AS data detected. Please upload original TRACES file.")
        st.stop()

    # ---------- STRUCTURED 26AS ----------
    structured_26as = raw26.groupby(
        ["Section", "Name of Deductor", "TAN of Deductor"], as_index=False
    ).agg({"Amount": "sum", "TDS": "sum"})

    structured_26as.columns = [
        "Section","Name of Deductor","TAN of Deductor",
        "Total Amount Paid / Credited","Total TDS Deposited"
    ]

    # ---------- PARTY PIVOT ----------
    pivot_party = structured_26as.groupby(
        ["Name of Deductor", "TAN of Deductor"], as_index=False
    )[["Total Amount Paid / Credited","Total TDS Deposited"]].sum()

    # ---------- BOOKS ----------
    books = pd.read_excel(books_file)

    # ---------- RECON ----------
    recon26 = structured_26as.groupby("TAN of Deductor", as_index=False)[
        ["Total Amount Paid / Credited","Total TDS Deposited"]
    ].sum()

    recon = recon26.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer").fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    def status(r):
        if r["Books Amount"] == 0 and r["Total Amount Paid / Credited"] > 0:
            return "Not in books"
        elif r["Difference TDS"] > 0:
            return "Under-recorded"
        elif r["Difference TDS"] < 0:
            return "Excess in books"
        else:
            return "Matched"

    recon["Status"] = recon.apply(status, axis=1)

    final_recon = recon[[
        "TAN of Deductor","Total Amount Paid / Credited","Books Amount",
        "Difference Amount","Total TDS Deposited","Books TDS",
        "Difference TDS","Status"
    ]]

    final_recon.columns = [
        "TAN","26AS Amount","Books Amount","Difference Amount",
        "26AS TDS","Books TDS","Difference TDS","Status"
    ]

    # ---------- EXPORT ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Structured", index=False)
        pivot_party.to_excel(writer, sheet_name="26AS_Party_Pivot", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("Reconciliation completed successfully")

    st.download_button("Download Final Excel", output, "26AS_Reconciliation.xlsx")

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
