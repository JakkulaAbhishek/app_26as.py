import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# ---------------- UI THEME ----------------
st.set_page_config(page_title="AJ 26AS Tool", layout="wide")

st.markdown("""
<style>
body { background-color: black; color: white; }
.block-container { background-color: black; }
h1, h2, h3, h4 { color: white; }
</style>
""", unsafe_allow_html=True)

# ---------------- BRAND HEADER ----------------
st.markdown("""
<div style="background:black;padding:20px;border:2px solid red;border-radius:15px;text-align:center;">
<h1 style="color:white;">26AS RECONCILIATION AUTOMATION TOOL</h1>
<h3 style="color:red;">AJ</h3>
<h4>🦚🎶 Lord Krishna Blessings</h4>
<p style="color:lightgray;">Tool developed by - Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------- SAMPLE BOOKS ----------------
sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd"],
    "TAN": ["HYDA00000A"],
    "Books Amount": [100000],
    "Books TDS": [10000]
})

buf = BytesIO()
sample_books.to_excel(buf, index=False)
buf.seek(0)

st.download_button("⬇ Download Sample Books Excel Template",
                   data=buf,
                   file_name="Sample_Books_Template.xlsx")

st.info("Upload only TRACES Form 26AS PDF (text based) and Books Excel")

# ---------------- UPLOAD ----------------
pdf_file = st.file_uploader("Upload TRACES Form 26AS PDF", type=["pdf"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- 26AS PARSER ----------------
def extract_26as(pdf):
    records = []
    with pdfplumber.open(pdf) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 8:
                        if re.match(r"\d{2}-[A-Za-z]{3}-\d{4}", str(row[2])):
                            records.append({
                                "Section": row[1],
                                "Transaction Date": row[2],
                                "Amount Paid": row[6],
                                "TDS": row[7]
                            })

            text = page.extract_text()
            blocks = re.split(r"Name of Deductor", text)
            for b in blocks[1:]:
                name = re.search(r"\n([A-Z &().]+)", b)
                tan = re.search(r"\b[A-Z]{4}\d{5}[A-Z]\b", b)
                if name and tan:
                    for r in records[-5:]:
                        r["Party"] = name.group(1).strip()
                        r["TAN"] = tan.group()

    df = pd.DataFrame(records)
    df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce").fillna(0)
    df["TDS"] = pd.to_numeric(df["TDS"], errors="coerce").fillna(0)
    return df

# ---------------- PROCESS ----------------
if st.button("🚀 RUN 26AS RECONCILIATION"):

    if not pdf_file or not books_file:
        st.error("Upload both PDF and Books file.")
        st.stop()

    df26 = extract_26as(pdf_file)

    if df26.empty:
        st.error("❌ No TDS data detected from PDF.")
        st.stop()

    books = pd.read_excel(books_file)

    pivot_party = df26.groupby(["Party","TAN"], as_index=False)[["Amount Paid","TDS"]].sum()
    pivot_section = df26.groupby("Section", as_index=False)[["Amount Paid","TDS"]].sum()

    recon = pivot_party.merge(books, on="TAN", how="outer")

    recon["Books Amount"] = recon["Books Amount"].fillna(0)
    recon["Books TDS"] = recon["Books TDS"].fillna(0)

    recon["Amount Diff"] = recon["Amount Paid"] - recon["Books Amount"]
    recon["TDS Diff"] = recon["TDS"] - recon["Books TDS"]

    missing_books = recon[recon["Books Amount"] == 0]

    recon["Risk Flag"] = recon.apply(lambda x:
        "⚠ High Risk" if abs(x["TDS Diff"]) > 1000 else "OK", axis=1)

    # ---------------- EXCEL EXPORT ----------------
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df26.to_excel(writer, "Raw_26AS", index=False)
        pivot_party.to_excel(writer, "Party_Summary", index=False)
        pivot_section.to_excel(writer, "Section_Pivot", index=False)
        recon.to_excel(writer, "Reconciliation", index=False)
        missing_books.to_excel(writer, "Missing_in_Books", index=False)

    out.seek(0)

    st.success("✅ Reconciliation completed successfully!")

    st.download_button("⬇ Download Final Reconciliation Excel",
                       data=out,
                       file_name="AJ_26AS_Reconciliation.xlsx")

    st.dataframe(recon)
