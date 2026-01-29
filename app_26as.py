import streamlit as st
import pandas as pd
import re
from io import BytesIO
import base64

# ---------- LOAD BACKGROUND IMAGE ----------
def set_bg(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background: url("data:image/jpg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .block-container {{
        background-color: rgba(0,0,0,0.78);
        padding: 2rem;
        border-radius: 15px;
    }}
    h1,h2,h3,h4,p {{ color: white; }}
    </style>
    """, unsafe_allow_html=True)

set_bg("krishna_bg.jpg")

st.set_page_config(page_title="AJ 26AS Tool", layout="wide")

# ---------- HEADER ----------
st.markdown("""
<div style="text-align:center;border:2px solid red;padding:20px;border-radius:18px;">
<h1 style="color:white;">26AS Reconciliation Automation Tool</h1>
<h2 style="color:red;">AJ</h2>
<h4>🦚 Lord Krishna Blessings</h4>
<p><i>कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</i></p>
<p style="color:lightgray;">Tool developed by - Abhishek Jakkula</p>
</div>
<hr>
""", unsafe_allow_html=True)

# ---------- SAMPLE BOOKS ----------
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

st.info("Upload TRACES Form 26AS TEXT file (.txt) and Books Excel")

txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
books_file = st.file_uploader("Upload Books Excel", type=["xlsx"])


# ---------- FIXED TRACES PARSER ----------
def extract_26as_from_text(file):
    text = file.read().decode("utf-8", errors="ignore")
    lines = text.splitlines()

    records = []
    current_name = ""
    current_tan = ""

    for line in lines:
        parts = [p.strip() for p in line.split("^") if p.strip()]

        # TAN detection
        for i,p in enumerate(parts):
            if re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", p):
                current_tan = p
                # Name usually before TAN
                if i > 0:
                    possible_name = parts[i-1]
                    if not re.search("TAN|DEDUCTOR|SECTION", possible_name.upper()):
                        current_name = possible_name

        # Transaction detection
        section = next((p for p in parts if re.fullmatch(r"\d+[A-Z]+", p)), "")
        numbers = [p.replace(",","") for p in parts if re.fullmatch(r"-?\d+(\.\d+)?", p.replace(",",""))]

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


# ---------- PROCESS ----------
if st.button("🚀 RUN RECONCILIATION"):

    if not txt_file or not books_file:
        st.error("Please upload both files.")
        st.stop()

    raw26 = extract_26as_from_text(txt_file)

    if raw26.empty:
        st.error("❌ No usable 26AS data detected. Please upload original TRACES .txt file.")
        st.stop()

    # Sheet 1: Structured
    structured_26as = raw26.groupby(
        ["Section","Name of Deductor","TAN of Deductor"], as_index=False
    ).agg({"Amount":"sum","TDS":"sum"})

    structured_26as.columns = [
        "Section","Name of Deductor","TAN of Deductor",
        "Total Amount Paid / Credited","Total TDS Deposited"
    ]

    # Sheet 2: Party pivot
    pivot_party = structured_26as.groupby(
        ["Name of Deductor","TAN of Deductor"], as_index=False
    )[["Total Amount Paid / Credited","Total TDS Deposited"]].sum()

    # Sheet 3: Books
    books = pd.read_excel(books_file)

    # Sheet 4: Reconciliation
    recon26 = structured_26as.groupby("TAN of Deductor", as_index=False)[
        ["Total Amount Paid / Credited","Total TDS Deposited"]
    ].sum()

    recon = recon26.merge(books, left_on="TAN of Deductor", right_on="TAN", how="outer").fillna(0)

    recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
    recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

    def status(r):
        if r["Books Amount"] == 0 and r["Total Amount Paid / Credited"] > 0:
            return "Not filed by vendor"
        elif r["Difference TDS"] > 0:
            return "Under-recorded in books"
        elif r["Difference TDS"] < 0:
            return "Excess in books"
        else:
            return "Matched"

    recon["Status"] = recon.apply(status, axis=1)

    final_recon = recon[[
        "TAN of Deductor","Total Amount Paid / Credited","Books Amount","Difference Amount",
        "Total TDS Deposited","Books TDS","Difference TDS","Status"
    ]]

    final_recon.columns = [
        "TAN","26AS Amount","Books Amount","Difference Amount",
        "26AS TDS","Books TDS","Difference TDS","Status"
    ]

    # ---------- EXPORT ----------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        structured_26as.to_excel(writer, "26AS_Structured", index=False)
        pivot_party.to_excel(writer, "26AS_Pivot_Party", index=False)
        books.to_excel(writer, "Books_Data", index=False)
        final_recon.to_excel(writer, "26AS_vs_Books", index=False)

    output.seek(0)

    st.success("✅ Reconciliation completed successfully")

    st.download_button("📥 Download Final Excel", output, "AJ_26AS_Reconciliation.xlsx")

    st.subheader("Preview – 26AS vs Books")
    st.dataframe(final_recon, use_container_width=True)
