import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="26AS Automation Tool", layout="wide")

# ---------------- GOOGLE STYLE PROFESSIONAL THEME ----------------
st.markdown("""
<style>

/* ----------- GOOGLE-STYLE PROFESSIONAL THEME ----------- */

.stApp {
    background: linear-gradient(135deg, #f8fafc, #eef2f7);
    font-family: 'Segoe UI', sans-serif;
    color: #1f2937;
}

.block-container {
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(12px);
    padding: 2.5rem;
    border-radius: 20px;
    box-shadow: 0px 10px 30px rgba(0,0,0,0.08);
}

/* Headings */
h1 {
    color:#0f172a !important;
    font-weight:800;
    letter-spacing:0.3px;
}

h2,h3,h4,p,label {
    color:#1f2937 !important;
}

/* Header card */
.header-box {
    text-align:center;
    padding:35px 25px;
    border-radius:24px;
    background: linear-gradient(135deg, #ffffff, #f1f5f9);
    box-shadow: 0px 15px 35px rgba(0,0,0,0.08);
    margin-bottom:30px;
}

/* App logo */
.app-logo {
    font-size:52px;
    font-weight:900;
    background: linear-gradient(90deg, #2563eb, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing:3px;
}

/* Sub text */
.subtext {
    color:#475569;
    font-size:15px;
}

/* Shloka */
.shloka {
    color:#0f766e;
    font-style: italic;
    font-size:16px;
}

/* Buttons */
.stDownloadButton button, .stButton button {
    background: linear-gradient(90deg, #2563eb, #06b6d4);
    color:blue;
    border:none;
    padding:10px 22px;
    border-radius:12px;
    font-weight:600;
    transition:0.3s;
}

.stDownloadButton button:hover, .stButton button:hover {
    transform: scale(1.03);
    box-shadow:0px 8px 22px rgba(37,99,235,0.35);
}

/* File uploader */
[data-testid="stFileUploader"] {
    background:#f8fafc;
    padding:18px;
    border-radius:14px;
    border:1px dashed #cbd5e1;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
    <div class="app-logo">26AS AUTOMATION</div>
    <h1>Professional 26AS Reconciliation Tool</h1>
    <p class="subtext">Smart. Accurate. CA-Grade Automation ⚡</p>
    <p class="shloka">कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</p>
    <p class="subtext">Developed by Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.info("Upload TRACES Form 26AS TEXT file (.txt) and Books Excel")

# ---------------- SAMPLE BOOKS DOWNLOAD ----------------
sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd"],
    "TAN": ["HYDA00000A"],
    "Books Amount": [100000],
    "Books TDS": [10000]
})

buf = BytesIO()
sample_books.to_excel(buf, index=False)
buf.seek(0)

st.download_button("⬇ Download Sample Books Excel Template", buf, "Sample_Books_Template.xlsx")

# ---------------- FILE UPLOAD ----------------
txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- ROBUST TRACES PARSER ----------------
def extract_26as_from_text(file):
    text = file.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()

    records = []
    current_name = ""
    current_tan = ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]

        # TAN detection
        for i, p in enumerate(parts):
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p):
                current_tan = p
                if i > 0:
                    possible_name = parts[i-1]
                    if not re.search("TAN|DEDUCTOR|SECTION", possible_name.upper()):
                        current_name = possible_name

        # Transaction detection
        section = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), "")
        numbers = [p.replace(",", "") for p in parts if re.fullmatch(r"-?\d+(\.\d+)?", p.replace(",", ""))]

        if current_name and current_tan and section and len(numbers) >= 2:
            try:
                records.append({
                    "Section": section,
                    "Name of Deductor": current_name,
                    "TAN of Deductor": current_tan,
                    "Amount": float(numbers[-2]),
                    "TDS": float(numbers[-1])
                })
            except:
                pass

    return pd.DataFrame(records)

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    raw26 = extract_26as_from_text(txt_file)

    if raw26.empty:
        st.error("❌ No usable 26AS data detected. Please upload original TRACES .txt file.")
        st.stop()

    # ---------- SHEET 1 : STRUCTURED 26AS ----------
    structured_26as = raw26.groupby(
        ["Section", "Name of Deductor", "TAN of Deductor"], as_index=False
    ).agg({"Amount": "sum", "TDS": "sum"})

    structured_26as.columns = [
        "Section",
        "Name of Deductor",
        "TAN of Deductor",
        "Total Amount Paid / Credited",
        "Total TDS Deposited"
    ]

    # ---------- SHEET 2 : PARTY PIVOT ----------
    pivot_party = structured_26as.groupby(
        ["Name of Deductor", "TAN of Deductor"], as_index=False
    )[["Total Amount Paid / Credited", "Total TDS Deposited"]].sum()

    # ---------- SHEET 3 : BOOKS ----------
    books = pd.read_excel(books_file)

    # ---------- SHEET 4 : RECON ----------
    recon26 = structured_26as.groupby("TAN of Deductor", as_index=False)[
        ["Total Amount Paid / Credited", "Total TDS Deposited"]
    ].sum()

    recon = recon26.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer").fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    def status(r):
        if r["Books Amount"] == 0 and r["Total Amount Paid / Credited"] > 0:
            return "Not recorded at books"
        elif r["Difference TDS"] > 0:
            return "Excess-recorded in books"
        elif r["Difference TDS"] < 0:
            return "Less in books"
        else:
            return "Matched"

    recon["Status"] = recon.apply(status, axis=1)

    final_recon = recon[[
        "TAN of Deductor",
        "Total Amount Paid / Credited",
        "Books Amount",
        "Difference Amount",
        "Total TDS Deposited",
        "Books TDS",
        "Difference TDS",
        "Status"
    ]]

    final_recon.columns = [
        "TAN",
        "26AS Amount",
        "Books Amount",
        "Difference Amount",
        "26AS TDS",
        "Books TDS",
        "Difference TDS",
        "Status"
    ]

    # ---------- EXCEL EXPORT ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Structured", index=False)
        pivot_party.to_excel(writer, sheet_name="26AS_Pivot_Party", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Reconciliation completed successfully")

    st.download_button(
        "📥 Download Final Reconciliation Excel",
        data=output,
        file_name="26AS_Reconciliation.xlsx"
    )

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
