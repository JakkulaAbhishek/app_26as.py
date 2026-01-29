import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="AJ 26AS Tool", layout="wide")

# ---------------- BLACK UI ----------------
st.markdown("""
<style>
body {background-color:black;color:white;}
.block-container {background-color:black;}
h1,h2,h3 {color:white;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align:center'>26AS Reconciliation Automation Tool</h1>
<h4 style='text-align:center;color:lightgray'>Tool developed by - Abhishek Jakkula</h4>
<hr>
""", unsafe_allow_html=True)

st.info("Upload TRACES Form 26AS PDF (text-based) and Books Excel")

# ---------------- UPLOAD ----------------
pdf_file = st.file_uploader("Upload TRACES 26AS PDF", type=["pdf"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- CORE EXTRACTOR ----------------
def extract_26as(pdf):
    data = []
    current_name, current_tan = None, None

    with pdfplumber.open(pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            name = re.search(r"Name of Deductor\s*:\s*(.*)", text)
            tan = re.search(r"TAN of Deductor\s*:\s*([A-Z0-9]+)", text)

            if name: current_name = name.group(1).strip()
            if tan: current_tan = tan.group(1).strip()

            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if row and len(row) >= 8:
                        if row[1] and re.search(r"\d+[A-Z]", str(row[1])):
                            try:
                                data.append({
                                    "Section": row[1],
                                    "Name of Deductor": current_name,
                                    "TAN": current_tan,
                                    "Amount": float(str(row[6]).replace(",","")),
                                    "TDS": float(str(row[7]).replace(",",""))
                                })
                            except:
                                pass

    df = pd.DataFrame(data)
    return df

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):

    if not pdf_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    raw26 = extract_26as(pdf_file)

    if raw26.empty:
        st.error("No usable 26AS data detected.")
        st.stop()

    # ---------- SHEET 1 : STRUCTURED 26AS ----------
    structured_26as = raw26.groupby(
        ["Section","Name of Deductor","TAN"], as_index=False
    ).agg({
        "Amount":"sum",
        "TDS":"sum"
    })

    structured_26as.columns = [
        "Section",
        "Name of Deductor",
        "TAN of Deductor",
        "Total Amount Paid / Credited",
        "Total TDS Deposited"
    ]

    # ---------- SHEET 2 : PIVOT ----------
    pivot_26as = structured_26as.groupby("Section", as_index=False)[
        ["Total Amount Paid / Credited","Total TDS Deposited"]
    ].sum()

    # ---------- SHEET 3 : BOOKS ----------
    books = pd.read_excel(books_file)

    # ---------- SHEET 4 : RECONCILIATION ----------
    recon = structured_26as.groupby("TAN of Deductor", as_index=False)[
        ["Total Amount Paid / Credited","Total TDS Deposited"]
    ].sum()

    recon = recon.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer")

    recon["Books Amount"] = recon["Books Amount"].fillna(0)
    recon["Books TDS"] = recon["Books TDS"].fillna(0)

    recon["Amount Difference"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["TDS Difference"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    # ---------- EXCEL EXPORT ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Structured", index=False)
        pivot_26as.to_excel(writer, sheet_name="26AS_Pivot", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Processing completed successfully")

    st.download_button(
        "📥 Download Final Reconciliation Excel",
        data=output,
        file_name="AJ_26AS_Reconciliation.xlsx"
    )

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(recon)
