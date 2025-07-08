import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime, date

from bulk_section import draw_bulk_section, bulk_sections
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

# --- FILE PERSISTENCE SETUP ---
REPORTS_DIR = "production_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def save_report(pdf_bytes, date_str):
    fname = f"{REPORTS_DIR}/daily_production_report_{date_str}.pdf"
    with open(fname, "wb") as f:
        f.write(pdf_bytes)
    return fname

def list_reports():
    files = []
    for fname in sorted(os.listdir(REPORTS_DIR)):
        if fname.endswith(".pdf"):
            path = os.path.join(REPORTS_DIR, fname)
            dts = fname.replace("daily_production_report_", "").replace(".pdf", "")
            files.append({"date": dts, "file": path})
    files.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'), reverse=True)
    return files

def get_selected_date():
    return st.date_input("Production Date", value=date.today(), max_value=date.today())

# --- UI ---
st.title("📦 Bulk Ingredient Summary Report (Multi-Brand)")
st.markdown("Upload your order summary files for each brand below. You can use either CSV or Excel.")

col1, col2, col3 = st.columns(3)
with col1:
    file_clean = st.file_uploader("Upload **Clean Eats** Orders", type=["csv", "xlsx"], key="clean")
with col2:
    file_made = st.file_uploader("Upload **Made Active** Orders", type=["csv", "xlsx"], key="made")
with col3:
    file_elite = st.file_uploader("Upload **Elite Meals** Orders", type=["csv", "xlsx"], key="elite")

uploaded_files = [file_clean, file_made, file_elite]
brand_names = ["Clean Eats", "Made Active", "Elite Meals"]

# --- DATAFRAME READING ---
dfs = []
for f in uploaded_files:
    if f is not None:
        if f.name.endswith(".csv"):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
        dfs.append(df)
    else:
        dfs.append(None)

if all(df is None for df in dfs):
    st.info("Please upload at least one orders file to proceed.")
    st.stop()


# --- MEAL SUMMARY TABLE ---
all_meals = set()
for df in dfs:
    if df is not None:
        all_meals.update(df["Product name"].astype(str).str.strip())

all_meals = sorted(all_meals)
table_rows = []
for meal in all_meals:
    row = [meal]
    for df in dfs:
        if df is not None:
            match = df[df["Product name"].astype(str).str.strip().str.upper() == meal.upper()]
            qty = int(match["Quantity"].values[0]) if not match.empty else 0
            row.append(qty)
        else:
            row.append(0)
    row.append(sum(row[1:]))
    table_rows.append(row)

summary_df = pd.DataFrame(
    table_rows,
    columns=["Meal", "Clean Eats", "Made Active", "Elite Meals", "Total"]
)

st.markdown("### 📝 Meal Quantity Summary")
edited_df = st.data_editor(
    summary_df,
    key="editable_summary",
    num_rows="dynamic",
    use_container_width=True,
)

# --- Pick Production Date ---
selected_date = get_selected_date()
selected_date_str = selected_date.strftime("%Y-%m-%d")
selected_date_header = selected_date.strftime("%d/%m/%Y")

# --- Generate Button ---
if st.button("Generate & Save Production Report PDF"):
    # --- BUILD MEAL TOTALS DICT FOR PDF ---
    meal_totals_clean = dict(zip(edited_df["Meal"].str.upper(), edited_df["Clean Eats"]))
    meal_totals_made = dict(zip(edited_df["Meal"].str.upper(), edited_df["Made Active"]))
    meal_totals_elite = dict(zip(edited_df["Meal"].str.upper(), edited_df["Elite Meals"]))
    meal_totals_total = dict(zip(edited_df["Meal"].str.upper(), edited_df["Total"]))

    # --- PDF SETUP ---
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    a4_w, a4_h = 210, 297
    left = 10
    page_w = a4_w - 2 * left
    col_w = page_w / 2 - 5
    ch, pad, bottom = 6, 4, a4_h - 17
    xpos = [left, left + col_w + 10]

    # --- PDF: Summary Table (Page 1) ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, f"Production Report: {selected_date_header}", ln=1, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(220, 220, 240)
    colw = [70, 30, 30, 30, 30]
    headers = ["Meal", "Clean Eats", "Made Active", "Elite Meals", "Total"]
    for i, h in enumerate(headers):
        pdf.cell(colw[i], ch+2, h, border=1, fill=True)
    pdf.ln(ch+2)
    pdf.set_font("Arial", "", 10)
    for _, row in edited_df.iterrows():
        for i, val in enumerate(row):
            pdf.cell(colw[i], ch+2, str(val), border=1)
        pdf.ln(ch+2)
    pdf.ln(5)
    last_y = pdf.get_y()

    # --- DRAW ALL SECTIONS (using Total as basis) ---
    last_y = draw_bulk_section(pdf, meal_totals_total, xpos, col_w, ch, pad, bottom, start_y=None, header_date=selected_date_header)
    pdf.set_y(last_y)
    last_y = draw_recipes_section(pdf, meal_totals_total, xpos, col_w, ch, pad, bottom, start_y=last_y)
    pdf.set_y(last_y)
    last_y = draw_sauces_section(pdf, meal_totals_total, xpos, col_w, ch, pad, bottom, start_y=last_y)
    pdf.set_y(last_y)
    last_y = draw_fridge_section(pdf, meal_totals_total, xpos, col_w, ch, pad, bottom, start_y=last_y)
    pdf.set_y(last_y)
    last_y = draw_chicken_mixing_section(pdf, meal_totals_total, xpos, col_w, ch, pad, bottom, start_y=last_y)
    pdf.set_y(last_y)
    last_y = draw_meat_veg_section(
        pdf, meal_totals_total, meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=last_y
    )

    # --- SAVE TO BYTES AND STORE ---
    pdf_buffer = pdf.output(dest='S').encode('latin1')
    report_fname = save_report(pdf_buffer, selected_date_str)
    st.success(f"Production report for {selected_date_header} saved!")
    st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=f"daily_production_report_{selected_date_str}.pdf", mime="application/pdf")

# --- Show Previous Reports & Search ---
st.markdown("---")
st.subheader("📚 Previous Reports")
all_reports = list_reports()
search_val = st.text_input("Search by date (YYYY-MM-DD)")
filtered_reports = [r for r in all_reports if (not search_val or search_val in r['date'])]
if filtered_reports:
    for r in filtered_reports:
        dt = datetime.strptime(r['date'], "%Y-%m-%d").strftime("%d/%m/%Y")
        with open(r['file'], "rb") as f:
            st.download_button(f"Download {dt}", f, file_name=f"daily_production_report_{r['date']}.pdf", mime="application/pdf")
else:
    st.write("No reports found.")

