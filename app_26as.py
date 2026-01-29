import streamlit as st
import pandas as pd
import re
from io import BytesIO

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
.krishna {font-size:28px;}
.shloka {color:#065f46; font-style:italic; font-size:16px; margin-top:8px;}

/* ZONE */
.zone {
    background:#ffffff;
    padding:18px;
    border-radius:14px;
    border:1px solid #e5e7eb;
    box-shadow:0 6px 16px rgba(0,0,0,0.06);
    margin-bottom:18px;
}

/* 🌤 FILE UPLOADER – SKY BLUE CARD */
[data-testid="stFileUploader"] {
    background: linear-gradient(135deg,#e0f2fe,#bae6fd) !important;
    border-radius:18px !important;
    padding:22px !important;
    border:2px dashed #0284c7 !important;
    box-shadow:0 8px 22px rgba(2,132,199,0.25);
}

/* Uploader text */
[data-testid="stFileUploader"] * {
    color:darkredandblueandyellowmix !important;
    font-weight:600 !important;
}

/* 🌈 GOOGLE STYLE "BROWSE FILES" BUTTON */
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

/* Table */
[data-testid="stDataFrame"] {
    background:white;
    border-radius:12px;
    border:1px solid #e5e7eb;
    box-shadow:0 6px 18px rgba(0,0,0,0.06);
}

/* Force dark text */
h1,h2,h3,h4,h5,h6,p,span,div,label {
    color:#000000 !important;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("""
<div class="header-box">
    <div class="header-title">26AS PROFESSIONAL RECONCILIATION TOOL</div>
    <div class="header-sub">26AS VS BOOKS</div>
    <div class="krishna">🦚 श्री कृष्णाय नमः 🙏</div>
    <div class="shloka">
        कर्मण्येवाधिकारस्ते मा फलेषु कदाचन ।<br>
        मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ॥ (Bhagavad Gita 2.47)
    </div>
    <p style="margin-top:8px;">Developed by Abhishek Jakkula</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="zone">📄 Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

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

    recon["Status"] = recon.apply(
        lambda r: "Matched" if abs(r["Difference TDS"]) < 1 else
        ("Not in books" if r["Books Amount"] == 0 else
         "Under-recorded" if r["Difference TDS"] > 0 else "Excess in books"), axis=1)

    final_recon = recon[[
        "Section","Name of Deductor","TAN of Deductor",
        "Total Amount Paid / Credited","Books Amount","Difference Amount",
        "Total TDS Deposited","Books TDS","Difference TDS","Status"
    ]]

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, sheet_name="26AS_Party_Wise", index=False)
        books.to_excel(writer, sheet_name="Books_Data", index=False)
        final_recon.to_excel(writer, sheet_name="26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Reconciliation completed successfully with Lord Krishna’s blessings 🙏")

    st.download_button("📥 Download Final Reconciliation Excel", output, "26AS_Reconciliation.xlsx")

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
