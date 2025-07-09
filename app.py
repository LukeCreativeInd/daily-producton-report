import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os, copy, glob

from bulk_section import draw_bulk_section
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

st.set_page_config(page_title="Production Report", layout="wide")

st.title("📦 Production Report")

# --- Upload Fields for 3 Brands ---
st.subheader("Step 1: Upload Production Files")
uploaded_files = {}
col1, col2, col3 = st.columns(3)
with col1:
    uploaded_files['Clean Eats'] = st.file_uploader("Clean Eats File", type=["csv", "xlsx"], key="clean_eats")
with col2:
    uploaded_files['Made Active'] = st.file_uploader("Made Active File", type=["csv", "xlsx"], key="made_active")
with col3:
    uploaded_files['Elite Meals'] = st.file_uploader("Elite Meals File", type=["csv", "xlsx"], key="elite_meals")

# Allow any (but at least one) to proceed
if not any(uploaded_files.values()):
    st.info("Upload at least one production file to begin.")
    st.stop()

# --- Date Selector ---
st.subheader("Step 2: Select Report Date")
selected_date = st.date_input("Production Date", value=datetime.today())
selected_date_str = selected_date.strftime('%Y-%m-%d')
selected_date_header = selected_date.strftime('%d/%m/%Y')

# --- Bulk-prepared toggles ---
st.subheader("Step 3: Bulk-Prepared Recipe Toggles")
BULK_RECIPES = [
    "Spaghetti Bolognese",
    "Beef Chow Mein",
    "Beef Burrito Bowl",
    "Shepherd's Pie",
]
bulk_toggles = {}
st.write("If any of these recipes are already pre-made in bulk, tick them below. The app will set all their ingredients to zero for this run (so only pasta/rice etc will appear on the bulk table, not sauce or meat prep):")
for r in BULK_RECIPES:
    bulk_toggles[r] = st.checkbox(f"{r} already prepared (set all recipe ingredients to zero)", key=f"bulk_{r}")

# --- Parse & Merge ---
dataframes = []
brand_names = []
for brand, f in uploaded_files.items():
    if f:
        if f.name.endswith(".csv"):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
        df.columns = df.columns.str.strip()
        if not {"Product name", "Quantity"}.issubset(df.columns):
            st.error(f"{brand} file must have 'Product name' and 'Quantity'")
            st.stop()
        df = df[["Product name", "Quantity"]]
        df["Product name"] = df["Product name"].astype(str).str.strip()
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
        df = df.groupby("Product name", as_index=False).sum()  # Remove accidental dups
        dataframes.append(df)
        brand_names.append(brand)

if not dataframes:
    st.warning("No valid data to process.")
    st.stop()

# --- Editable merged summary table ---
all_products = sorted(set(p for df in dataframes for p in df["Product name"]))
summary_data = []
for p in all_products:
    row = {"Product name": p}
    total = 0
    for i, df in enumerate(dataframes):
        brand = brand_names[i]
        qty = int(df.loc[df["Product name"]==p, "Quantity"].sum()) if p in df["Product name"].values else 0
        row[brand] = qty
        total += qty
    row["Total"] = total
    summary_data.append(row)
summary_df = pd.DataFrame(summary_data)
summary_df = summary_df[["Product name"] + brand_names + ["Total"]]

st.subheader("Step 4: Adjust Quantities (if needed)")
edited_df = st.data_editor(
    summary_df, num_rows="dynamic", use_container_width=True,
    column_config={b: {"width": 70} for b in brand_names + ["Total"]}
)
# Update the meal_totals for downstream
meal_totals = dict(zip(edited_df["Product name"].str.upper(), edited_df["Total"]))

# --- Previous Reports (history) ---
st.subheader("Previous Production Reports")
os.makedirs("previous_reports", exist_ok=True)
existing_reports = sorted(glob.glob("previous_reports/daily_production_report_*.pdf"), reverse=True)
search = st.text_input("Search reports by date (yyyy-mm-dd) or meal")
filtered_reports = [f for f in existing_reports if search.lower() in f.lower()] if search else existing_reports
for fname in filtered_reports:
    rname = os.path.basename(fname).replace("daily_production_report_", "").replace(".pdf", "")
    with open(fname, "rb") as f:
        st.download_button(f"Download {rname}", f, file_name=os.path.basename(fname), mime="application/pdf")

# --- Patch meal_recipes for bulk-toggles ---
import copy
custom_meal_recipes = copy.deepcopy(meal_recipes)
for r, checked in bulk_toggles.items():
    if checked and r in custom_meal_recipes:
        for ing in custom_meal_recipes[r].get("ingredients", {}).keys():
            custom_meal_recipes[r]["ingredients"][ing] = 0
        if "sub_section" in custom_meal_recipes[r]:
            for ing in custom_meal_recipes[r]["sub_section"]["ingredients"].keys():
                custom_meal_recipes[r]["sub_section"]["ingredients"][ing] = 0

# --- PDF Generation ---
if st.button("Generate & Save Production Report PDF"):
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    a4_w, a4_h = 210, 297
    left = 10
    page_w = a4_w - 2 * left
    col_w = page_w / 2 - 5
    ch, pad, bottom = 6, 4, a4_h - 17
    xpos = [left, left + col_w + 10]

    last_y = draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=selected_date_header)
    pdf.set_y(last_y)
    last_y = draw_recipes_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes_override=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_fridge_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_meat_veg_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)

    # Save to local history
    pdf_buffer = pdf.output(dest="S").encode("latin1")
    fname = f"previous_reports/daily_production_report_{selected_date_str}.pdf"
    with open(fname, "wb") as f:
        f.write(pdf_buffer)
    st.success(f"Production report for {selected_date_header} saved!")
    st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=f"daily_production_report_{selected_date_str}.pdf", mime="application/pdf")
