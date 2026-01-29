import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="AJ 26AS Tool", layout="wide")

# ---------------- UI ----------------
st.markdown("""
<style>
body {background:black;color:white;}
.block-container {background:black;}
h1,h2,h3 {color:white;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align:center'>26AS Reconciliation Automation Tool</h1>
<h4 style='text-align:center;color:lightgray'>Tool developed by - Abhishek Jakkula</h4>
<hr>
""", unsafe_allow_html=True)

st.info("Upload TRACES Form 26AS TEXT file (.txt) and Books Excel")

txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])

# ---------------- TRACES TEXT PARSER ----------------
def extract_26as_from_text(file):
    text = file.read().decode("utf-8", errors="ignore")

    main_blocks = re.split(r"\n\d+\^", text)

    data = []

    for block in main_blocks:
        name = re.search(r"\^([A-Z0-9 &().,-]+)\^([A-Z]{4}\w{5}[A-Z])", block)
        if not name:
            continue

        party = name.group(1).strip()
        tan = name.group(2).strip()

        rows = re.findall(
            r"\^(\d+[A-Z]+)\^.*?\^([\d\-,.]+)\^([\d\-,.]+)\^([\d\-,.]+)\^",
            block
        )

        for r in rows:
            data.append({
                "Section": r[0],
                "Name of Deductor": party,
                "TAN of Deductor": tan,
                "Amount": float(r[1].replace(",","")),
                "TDS": float(r[3].replace(",",""))
            })

    df = pd.DataFrame(data)
    return df

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Upload both files.")
        st.stop()

    raw26 = extract_26as_from_text(txt_file)

    if raw26.empty:
        st.error("No usable 26AS data detected.")
        st.stop()

    # -------- Sheet 1: Structured 26AS --------
    structured_26as = raw26.groupby(
        ["Section","Name of Deductor","TAN of Deductor"], as_index=False
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

    # -------- Sheet 2: Party Pivot --------
    pivot_party = structured_26as.groupby(
        ["Name of Deductor","TAN of Deductor"], as_index=False
    )[["Total Amount Paid / Credited","Total TDS Deposited"]].sum()

    # -------- Sheet 3: Books --------
    books = pd.read_excel(books_file)

    # -------- Sheet 4: Reconciliation --------
    recon26 = structured_26as.groupby("TAN of Deductor", as_index=False)[
        ["Total Amount Paid / Credited","Total TDS Deposited"]
    ].sum()

    recon = recon26.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer")

    recon["Total Amount Paid / Credited"] = recon["Total Amount Paid / Credited"].fillna(0)
    recon["Total TDS Deposited"] = recon["Total TDS Deposited"].fillna(0)
    recon["Books Amount"] = recon["Books Amount"].fillna(0)
    recon["Books TDS"] = recon["Books TDS"].fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    def status(row):
        if row["Books Amount"] == 0 and row["Total Amount Paid / Credited"] > 0:
            return "Not filed by vendor"
        elif row["Difference TDS"] > 0:
            return "Under-recorded in books"
        elif row["Difference TDS"] < 0:
            return "Excess in books"
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

    # -------- Excel Export --------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Structured", index=False)
        pivot_party.to_excel(writer, sheet_name="26AS_Pivot_Party", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Processing completed successfully")

    st.download_button(
        "📥 Download Final Reconciliation Excel",
        data=output,
        file_name="AJ_26AS_Reconciliation.xlsx"
    )

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
