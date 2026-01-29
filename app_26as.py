import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="26AS Professional Tool", layout="wide")

# ---------------- CLEAR COLORED PROFESSIONAL UI ----------------
st.markdown("""
<style>

.stApp {
    background:#f2f5f9;
    font-family: 'Segoe UI', sans-serif;
    color:#000000;
}

.block-container {
    background:#ffffff;
    padding:2.2rem;
    border-radius:16px;
}

/* HEADER */
.header-box {
    background: linear-gradient(90deg,#1e3a8a,#2563eb);
    padding:30px;
    border-radius:16px;
    margin-bottom:25px;
}

.header-box h1, .header-box h3, .header-box p {
    color:white !important;
}

/* ZONES */
.zone {
    background:#ffffff;
    padding:18px;
    border-radius:14px;
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:18px;
}

/* FILE UPLOAD */
[data-testid="stFileUploader"] {
    background:#f8fafc;
    border:2px dashed #2563eb;
    border-radius:12px;
    padding:18px;
}

/* BUTTONS */
.stButton button, .stDownloadButton button {
    background: linear-gradient(90deg,#2563eb,#06b6d4);
    color:white;
    border-radius:10px;
    padding:10px 22px;
    font-weight:700;
    border:none;
}

.stButton button:hover, .stDownloadButton button:hover {
    transform:scale(1.02);
    box-shadow:0 6px 18px rgba(37,99,235,0.4);
}

/* TABLE */
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
    <h1>26AS PROFESSIONAL RECONCILIATION TOOL</h1>
    <h3>Exact TRACES Matching Engine</h3>
    <p>Developed by Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="zone">📄 Upload original TRACES 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

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

# ---------------- EXACT 26AS SUMMARY PARSER ----------------
def extract_26as_summary(file):
    text = file.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()

    data = []
    in_part1 = False

    for line in lines:
        if "PART-I - Details of Tax Deducted at Source" in line:
            in_part1 = True
            continue

        if in_part1 and line.startswith("^PART-"):
            break

        if in_part1:
            parts = [p.strip() for p in line.split("^") if p.strip()]

            if len(parts) >= 6 and re.fullmatch(r"\d+", parts[0]):

                if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", parts[2]):

                    try:
                        data.append({
                            "Name of Deductor": parts[1],
                            "TAN of Deductor": parts[2],
                            "Total Amount Paid / Credited": float(parts[-3].replace(",","")),
                            "Total Tax Deducted": float(parts[-2].replace(",","")),
                            "Total TDS Deposited": float(parts[-1].replace(",",""))
                        })
                    except:
                        pass

    return pd.DataFrame(data)

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    structured_26as = extract_26as_summary(txt_file)

    if structured_26as.empty:
        st.error("No valid PART-I summary detected. Please upload original TRACES file.")
        st.stop()

    books = pd.read_excel(books_file)

    # ---------- RECON ----------
    recon = structured_26as.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer").fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    def status(r):
        if r["Books Amount"] == 0 and r["Total Amount Paid / Credited"] > 0:
            return "Not in books"
        elif abs(r["Difference TDS"]) < 1:
            return "Matched"
        elif r["Difference TDS"] > 0:
            return "Under-recorded"
        else:
            return "Excess in books"

    recon["Status"] = recon.apply(status, axis=1)

    final_recon = recon[[
        "Name of Deductor","TAN of Deductor",
        "Total Amount Paid / Credited","Books Amount","Difference Amount",
        "Total TDS Deposited","Books TDS","Difference TDS","Status"
    ]]

    # ---------- EXPORT ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Part1_Summary", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Exact 26AS reconciliation completed")

    st.download_button("📥 Download Final Reconciliation Excel", output, "26AS_Reconciliation.xlsx")

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
