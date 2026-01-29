import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="26AS Professional Reconciliation", layout="wide")

# ---------------- CLEAN WHITE PROFESSIONAL UI ----------------
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
    background:#f1f5f9;
    padding:28px;
    border-radius:14px;
    margin-bottom:22px;
    border-left:8px solid #2563eb;
}

.header-box h1 {color:#0f172a !important;}
.header-box h3 {color:#1e3a8a !important;}
.header-box p {color:#000000 !important;}

/* ZONES */
.zone {
    background:#ffffff;
    padding:16px;
    border-radius:12px;
    border:1px solid #e5e7eb;
    box-shadow:0 4px 12px rgba(0,0,0,0.05);
    margin-bottom:16px;
}

/* FILE UPLOAD */
[data-testid="stFileUploader"] {
    background:#ffffff;
    border-radius:10px;
    padding:16px;
    border:2px dashed #2563eb;
}

/* BUTTONS */
.stButton button, .stDownloadButton button {
    background:#2563eb;
    color:white;
    border-radius:8px;
    padding:10px 22px;
    font-weight:700;
    border:none;
}

.stButton button:hover, .stDownloadButton button:hover {
    background:#1e40af;
}

/* TABLE */
[data-testid="stDataFrame"] {
    background:white;
    border-radius:10px;
    border:1px solid #e5e7eb;
}

/* FORCE ALL TEXT BLACK */
h1,h2,h3,h4,h5,h6,p,span,div,label {
    color:#000000 !important;
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

# ---------------- EXACT SUMMARY + SECTION EXTRACTOR ----------------
def extract_26as_summary_and_section(file):
    text = file.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()

    summary_data = []
    section_map = {}
    in_part1 = False
    current_tan = ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]

        # ---------- TAN TRACKING ----------
        for p in parts:
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p):
                current_tan = p

        # ---------- SECTION FROM TRANSACTION TABLE ----------
        sec = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), None)
        if current_tan and sec and current_tan not in section_map:
            section_map[current_tan] = sec

        # ---------- PART-I SUMMARY ----------
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
                except:
                    pass

    df = pd.DataFrame(summary_data)
    if not df.empty:
        df.insert(0, "Section", df["TAN of Deductor"].map(section_map).fillna(""))

    return df

# ---------------- PROCESS ----------------
if st.button("🚀 RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    structured_26as = extract_26as_summary_and_section(txt_file)

    if structured_26as.empty:
        st.error("No valid PART-I summary detected.")
        st.stop()

    books = pd.read_excel(books_file)

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
        "Section","Name of Deductor","TAN of Deductor",
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

    st.success("✅ Exact 26AS reconciliation completed successfully")

    st.download_button("📥 Download Final Reconciliation Excel", output, "26AS_Reconciliation.xlsx")

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
