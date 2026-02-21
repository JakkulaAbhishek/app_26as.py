import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import difflib
import plotly.express as px

st.set_page_config(page_title="26AS Professional Reconciliation", layout="wide")

# ---------------- ULTRA STYLISH CSS ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: #0f172a; color: #f8fafc; }

    .header-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; margin-bottom: 0px; line-height: 1.2;
    }
    
    .header-sub { color: #94a3b8; font-size: 1.2rem; font-weight: 600; margin-top: 5px; margin-bottom: 15px; }
    .krishna { font-size: 1.4rem; margin-top: 10px; color: #f8fafc; }
    .shloka { color: #34d399; font-style: italic; font-size: 1rem; margin-top: 5px; opacity: 0.9; }
    .dev-credit { color: #64748b; font-weight: 600; margin-top: 20px; font-size: 0.95rem; }
    .dev-credit b { color: #38bdf8; }

    .stButton>button, .stDownloadButton>button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white !important; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; transition: all 0.3s ease; width: 100%;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(139, 92, 246, 0.5);
    }

    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px); padding: 20px; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stMetricValue"] { color: #38bdf8; font-weight: 800; }

    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.4) !important; border-radius: 16px !important;
        padding: 1.5em !important; border: 1px dashed #64748b !important; transition: border 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover { border-color: #38bdf8 !important; }

    .alert-box-red {
        background: rgba(239, 68, 68, 0.1); border-left: 5px solid #ef4444; 
        padding: 18px; border-radius: 8px; margin-bottom: 12px; font-size: 1.05rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .alert-box-yellow {
        background: rgba(245, 158, 11, 0.1); border-left: 5px solid #f59e0b; 
        padding: 18px; border-radius: 8px; margin-bottom: 12px; font-size: 1.05rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .zone {
        background: rgba(30, 41, 59, 0.4); padding: 18px; border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 18px; text-align: center; color: #cbd5e1; font-weight: 600;
    }
    [data-testid="stDataFrame"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    tolerance = st.number_input("Mismatch Tolerance (₹)", min_value=0, value=10, step=1)
    max_rows = st.number_input("Max Rows for Excel Formulas", min_value=1000, value=15000, step=1000)

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <div class="header-title">26AS Professional Reconciliation</div>
    <div class="header-sub">AI-Powered Matching Engine: 26AS vs Books</div>
    <div class="krishna">🦚 श्री कृष्णाय नमः 🙏</div>
    <div class="shloka">
        कर्मण्येवाधिकारस्ते मा फलेषु कदाचन ।<br>
        मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ॥
    </div>
    <div class="dev-credit">Developed by <b>Abhishek Jakkula</b></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="zone">📄 Step 1: Upload original TRACES Form 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

# ---------------- SAMPLE BOOKS TEMPLATE ----------------
sample_books = pd.DataFrame({
    "Party Name": ["ABC Pvt Ltd", "XYZ Corp"],
    "TAN": ["HYDA00000A", ""],
    "Books Amount": [100000, 50000],
    "Books TDS": [10000, 5000]
})
buf = io.BytesIO()
sample_books.to_excel(buf, index=False)
buf.seek(0)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.download_button("⬇ Download Sample Books Excel Template", buf, "Sample_Books_Template.xlsx")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------- FILE UPLOAD ----------------
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload TRACES 26AS TEXT file", type=["txt"])
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx", "xls"])

st.markdown("<br>", unsafe_allow_html=True)

# ---------------- EXACT SUMMARY + SECTION EXTRACTOR ----------------
@st.cache_data
def extract_26as_summary_and_section(file_bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
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
                except Exception:
                    pass

    df = pd.DataFrame(summary_data)
    if not df.empty:
        df.insert(0, "Section", df["TAN of Deductor"].map(section_map).fillna(""))
    return df

# ---------------- PROCESS ----------------
col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    run_btn = st.button("🚀 RUN RECONCILIATION ENGINE")

if run_btn:
    if not txt_file or not books_file:
        st.warning("⚠️ Please upload both files to proceed.")
        st.stop()

    with st.spinner("Running AI Matching Engine..."):
        structured_26as = extract_26as_summary_and_section(txt_file.getvalue())

        if structured_26as.empty:
            st.error("❌ No valid PART-I summary detected in the text file.")
            st.stop()

        books = pd.read_excel(books_file)

        # File Validation
        required_cols = ["Party Name", "TAN", "Books Amount", "Books TDS"]
        for col in required_cols:
            if col not in books.columns:
                books[col] = "" if col in ["Party Name", "TAN"] else 0

        # Data Cleaning
        structured_26as["TAN of Deductor"] = structured_26as["TAN of Deductor"].astype(str).str.strip().str.upper()
        books["TAN"] = books["TAN"].fillna("").astype(str).str.strip().str.upper()

        # ================= FUZZY MATCHING LOGIC =================
        exact_match = pd.merge(structured_26as, books, left_on="TAN of Deductor", right_on="TAN", how="inner")
        exact_match["Match Type"] = "Exact (TAN)"

        rem_26as = structured_26as[~structured_26as["TAN of Deductor"].isin(exact_match["TAN of Deductor"])]
        rem_books = books[~books["TAN"].isin(exact_match["TAN"])]

        fuzzy_records = []
        matched_books_indices = set()

        for idx_26, row_26 in rem_26as.iterrows():
            name_26 = str(row_26["Name of Deductor"]).upper()
            best_match = None
            best_score = 0
            best_book_idx = -1

            for idx_bk, row_bk in rem_books.iterrows():
                if idx_bk in matched_books_indices: continue
                name_bk = str(row_bk["Party Name"]).upper()
                
                score = difflib.SequenceMatcher(None, name_26, name_bk).ratio()
                if score > best_score and score >= 0.70:
                    best_score = score
                    best_match = row_bk
                    best_book_idx = idx_bk

            if best_match is not None:
                combined = row_26.to_dict()
                combined.update(best_match.to_dict())
                combined["Match Type"] = "Fuzzy Match"
                fuzzy_records.append(combined)
                matched_books_indices.add(best_book_idx)
            else:
                combined = row_26.to_dict()
                combined["Match Type"] = "Missing in Books"
                fuzzy_records.append(combined)

        for idx_bk, row_bk in rem_books.iterrows():
            if idx_bk not in matched_books_indices:
                combined = row_bk.to_dict()
                combined["Match Type"] = "Missing in 26AS"
                fuzzy_records.append(combined)

        fuzzy_df = pd.DataFrame(fuzzy_records) if fuzzy_records else pd.DataFrame()
        recon = pd.concat([exact_match, fuzzy_df], ignore_index=True)

        # Unified Name and TAN columns
        recon["Deductor / Party Name"] = np.where(recon["Name of Deductor"].notna() & (recon["Name of Deductor"] != ""), recon["Name of Deductor"], recon["Party Name"])
        recon["Final TAN"] = np.where(recon["TAN of Deductor"].notna() & (recon["TAN of Deductor"] != ""), recon["TAN of Deductor"], recon["TAN"])

        # Fill NaNs for numeric calculations
        numeric_cols = ["Total Amount Paid / Credited", "Total TDS Deposited", "Books Amount", "Books TDS"]
        for col in numeric_cols:
            if col in recon.columns:
                recon[col] = pd.to_numeric(recon[col], errors="coerce").fillna(0)

        recon["Difference Amount"] = recon["Total Amount Paid / Credited"] - recon["Books Amount"]
        recon["Difference TDS"] = recon["Total TDS Deposited"] - recon["Books TDS"]

        # ================= ASSIGN STATUS AND REASON =================
        diff_tds = recon["Difference TDS"].abs()
        
        conditions_status = [
            (recon["Match Type"] == "Exact (TAN)") & (diff_tds <= tolerance),
            (recon["Match Type"] == "Exact (TAN)") & (diff_tds > tolerance),
            (recon["Match Type"] == "Fuzzy Match") & (diff_tds <= tolerance),
            (recon["Match Type"] == "Fuzzy Match") & (diff_tds > tolerance),
            (recon["Match Type"] == "Missing in Books"),
            (recon["Match Type"] == "Missing in 26AS")
        ]
        
        statuses = ["Exact Match", "Value Mismatch", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
        reasons = [
            "Matched perfectly", 
            "TDS value mismatch", 
            "Matched ignoring name formatting", 
            "TDS value mismatch", 
            "Not recorded in Books", 
            "Not reflected in 26AS"
        ]
        
        recon["Match Status"] = np.select(conditions_status, statuses, default="Unknown")
        recon["Reason for Difference"] = np.select(conditions_status, reasons, default="Unknown")

        final_recon = recon[[
            "Section", "Match Status", "Deductor / Party Name", "Final TAN",
            "Total Amount Paid / Credited", "Books Amount", "Difference Amount",
            "Total TDS Deposited", "Books TDS", "Difference TDS", "Reason for Difference"
        ]].rename(columns={"Final TAN": "TAN"})

        # --- Dashboard Metrics ---
        st.markdown("### 📊 Live Summary Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total TDS in 26AS", f"₹ {recon['Total TDS Deposited'].sum():,.2f}")
        m2.metric("Total TDS in Books", f"₹ {recon['Books TDS'].sum():,.2f}")
        net_diff = recon['Total TDS Deposited'].sum() - recon['Books TDS'].sum()
        m3.metric("Net Variance", f"₹ {net_diff:,.2f}", delta=f"₹ {net_diff:,.2f}", delta_color="inverse")

        # --- High Caution / Analytics ---
        st.markdown("### 🚨 AI Financial Alerts")
        
        miss_in_books = recon[recon["Match Status"] == "Missing in Books"]
        if not miss_in_books.empty and miss_in_books["Total TDS Deposited"].sum() > 0:
            total_missed = miss_in_books["Total TDS Deposited"].sum()
            top_missed = miss_in_books.loc[miss_in_books["Total TDS Deposited"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-red">
                <b>URGENT: Unclaimed TDS Leakage!</b> ₹ {total_missed:,.2f} is reflecting in 26AS but is completely <b>MISSING</b> in your books.<br>
                <span style="color: #fca5a5; font-size: 0.95rem;"><i>👉 Top Missing Party: <b>{top_missed['Deductor / Party Name']}</b> (₹ {top_missed['Total TDS Deposited']:,.2f}).</i></span>
            </div>
            """, unsafe_allow_html=True)

        miss_in_26as = recon[recon["Match Status"] == "Missing in 26AS"]
        if not miss_in_26as.empty and miss_in_26as["Books TDS"].sum() > 0:
            total_excess = miss_in_26as["Books TDS"].sum()
            top_excess = miss_in_26as.loc[miss_in_26as["Books TDS"].idxmax()]
            st.markdown(f"""
            <div class="alert-box-yellow">
                <b>COMPLIANCE RISK:</b> ₹ {total_excess:,.2f} of TDS is claimed in your Books but <b>NOT uploaded in 26AS</b>.<br>
                <span style="color: #fcd34d; font-size: 0.95rem;"><i>👉 Top Unreflected Party: <b>{top_excess['Deductor / Party Name']}</b> (₹ {top_excess['Books TDS']:,.2f}). Follow up immediately!</i></span>
            </div>
            """, unsafe_allow_html=True)

        # --- Charts ---
        st.markdown("### 📈 Top 10 Analytics")
        c1, c2 = st.columns(2)
        
        with c1:
            top_26as = final_recon.nlargest(10, "Total TDS Deposited")
            fig1 = px.pie(top_26as, names="Deductor / Party Name", values="Total TDS Deposited", title="Top 10 Deductors in 26AS (by TDS)", hole=0.4)
            fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc", family="Poppins"))
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            top_books = final_recon.nlargest(10, "Books TDS")
            fig2 = px.pie(top_books, names="Deductor / Party Name", values="Books TDS", title="Top 10 Parties in Books (by TDS)", hole=0.4)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc", family="Poppins"))
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)

        # --- Excel Export ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book
            
            brand_format = workbook.add_format({"bold": True, "font_size": 18, "bg_color": "#0f172a", "font_color": "#38bdf8", "align": "center", "valign": "vcenter"})
            dev_format = workbook.add_format({"italic": True, "font_size": 10, "bg_color": "#0f172a", "font_color": "#94a3b8", "align": "center"})
            
            # Formats for Dashboard and Headers
            fmt_dark_blue_white = workbook.add_format({
                "bold": True, "bg_color": "#0052cc", "font_color": "white", 
                "border": 1, "text_wrap": True, "align": "center", "valign": "vcenter"
            })
            fmt_subtotal = workbook.add_format({"bold": True, "bg_color": "#f2f2f2", "border": 1, "num_format": "#,##0.00"})

            # A. Dashboard
            dash = workbook.add_worksheet("Dashboard")
            dash.hide_gridlines(2)
            
            dash.merge_range("A1:K2", "26AS RECON PRO - EXECUTIVE SUMMARY", brand_format)
            dash.merge_range("A3:K3", "Developed by ABHISHEK JAKKULA | jakkulaabhishek5@gmail.com", dev_format)

            dash.write_row("B5", ["Match Status", "Record Count", "TDS Impact (26AS)", "TDS Impact (Books)"], fmt_dark_blue_white)
            dash.set_column('B:B', 25)
            dash.set_column('C:E', 18)

            dashboard_statuses = ["Exact Match", "Fuzzy Match", "Value Mismatch", "Missing in Books", "Missing in 26AS"]
            for i, status in enumerate(dashboard_statuses):
                row = 5 + i
                dash.write(row, 1, status)
                dash.write_formula(row, 2, f'=COUNTIF(Reconciliation!$B$3:$B${max_rows}, "{status}")')
                # 26AS TDS is column H, Books TDS is column I in the recon sheet
                dash.write_formula(row, 3, f'=SUMIF(Reconciliation!$B$3:$B${max_rows}, "{status}", Reconciliation!$H$3:$H${max_rows})')
                dash.write_formula(row, 4, f'=SUMIF(Reconciliation!$B$3:$B${max_rows}, "{status}", Reconciliation!$I$3:$I${max_rows})')

            dash.write("G5", "Top 10 Suppliers (26AS)", fmt_dark_blue_white)
            dash.write_row("G6", ["Deductor / Party Name", "Total Amount (26AS)", "Total TDS (26AS)"], fmt_dark_blue_white)
            for r_idx, row in top_26as.iterrows():
                dash.write_row(r_idx + 6, 6, [row["Deductor / Party Name"], row["Total Amount Paid / Credited"], row["Total TDS Deposited"]])
            dash.set_column('G:G', 35)
            dash.set_column('H:I', 18)

            dash.write("K5", "Top 10 Suppliers (Books)", fmt_dark_blue_white)
            dash.write_row("K6", ["Deductor / Party Name", "Books Amount", "Books TDS"], fmt_dark_blue_white)
            for r_idx, row in top_books.iterrows():
                dash.write_row(r_idx + 6, 10, [row["Deductor / Party Name"], row["Books Amount"], row["Books TDS"]])
            dash.set_column('K:K', 35)
            dash.set_column('L:M', 18)

            pie_chart = workbook.add_chart({'type': 'doughnut'})
            pie_chart.add_series({
                'name': 'Status Distribution',
                'categories': f'=Dashboard!$B$6:$B$10',
                'values': f'=Dashboard!$C$6:$C$10',
                'data_labels': {'percentage': True}
            })
            dash.insert_chart('B13', pie_chart)

            bar_26 = workbook.add_chart({'type': 'column'})
            bar_26.add_series({
                'name': 'TDS (26AS)',
                'categories': f'=Dashboard!$G$7:$G${6 + len(top_26as)}',
                'values': f'=Dashboard!$I$7:$I${6 + len(top_26as)}',
                'data_labels': {'value': True}
            })
            bar_26.set_title({'name': 'Top 10 Deductors (26AS)'})
            dash.insert_chart('G18', bar_26, {'x_scale': 1.2, 'y_scale': 1.2})

            bar_pr = workbook.add_chart({'type': 'column'})
            bar_pr.add_series({
                'name': 'TDS (Books)',
                'categories': f'=Dashboard!$K$7:$K${6 + len(top_books)}',
                'values': f'=Dashboard!$M$7:$M${6 + len(top_books)}',
                'data_labels': {'value': True}
            })
            bar_pr.set_title({'name': 'Top 10 Parties (Books)'})
            dash.insert_chart('K18', bar_pr, {'x_scale': 1.2, 'y_scale': 1.2})

            # B. Reconciliation Sheet
            sheet_recon = workbook.add_worksheet("Reconciliation")
            final_recon.to_excel(writer, sheet_name="Reconciliation", startrow=2, index=False, header=False)
            
            for col_num, col_name in enumerate(final_recon.columns):
                sheet_recon.write(1, col_num, col_name, fmt_dark_blue_white)
                
                if pd.api.types.is_numeric_dtype(final_recon[col_name]):
                    col_letter = chr(65 + col_num) 
                    formula = f"=SUBTOTAL(9,{col_letter}3:{col_letter}{max_rows})"
                    sheet_recon.write_formula(0, col_num, formula, fmt_subtotal)

            sheet_recon.set_column('A:B', 20)
            sheet_recon.set_column('C:C', 45)
            sheet_recon.set_column('D:D', 18)
            sheet_recon.set_column('E:J', 16)
            sheet_recon.set_column('K:K', 25)
            sheet_recon.autofilter(1, 0, max_rows, len(final_recon.columns) - 1)

            # C. Raw Data Sheets
            structured_26as.to_excel(writer, sheet_name="26AS Raw", index=False)
            books.to_excel(writer, sheet_name="Books Raw", index=False)

        output.seek(0)

        col_dl1, col_dl2, col_dl3 = st.columns([1,2,1])
        with col_dl2:
            st.download_button("⚡ Download Final Ultimate Excel Report", output, "26AS_Recon_Pro.xlsx")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("👁️ Preview Engine Output")
        
        # Filter Dropdown
        selected_status = st.multiselect("Filter by Match Status:", options=dashboard_statuses, default=dashboard_statuses)
        filtered_df = final_recon[final_recon["Match Status"].isin(selected_status)]
        st.dataframe(filtered_df.head(100), use_container_width=True)
