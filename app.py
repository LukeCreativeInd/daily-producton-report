import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import copy

from bulk_section import draw_bulk_section
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

st.set_page_config(page_title="Production Report", layout="wide")
st.title("📦 Production Report with Bulk Recipe Toggles")

uploaded_file = st.file_uploader("Upload Production File (CSV or Excel)", type=["csv", "xlsx"])
if not uploaded_file:
    st.info("Upload your daily production order to begin.")
    st.stop()

if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)
df.columns = df.columns.str.strip()
if not {"Product name", "Quantity"}.issubset(df.columns):
    st.error("File must have 'Product name' and 'Quantity'")
    st.stop()
df["Product name"] = df["Product name"].str.strip()
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
meal_totals = dict(zip(df["Product name"].str.upper(), df["Quantity"]))

# ---- Bulk-Prepared Recipe Toggles ----
st.header("Bulk-Prepared Recipes")
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

# ---- Patch meal_recipes to zero out those toggled ----
custom_meal_recipes = copy.deepcopy(meal_recipes)
for r, checked in bulk_toggles.items():
    if checked and r in custom_meal_recipes:
        for ing in custom_meal_recipes[r].get("ingredients", {}).keys():
            custom_meal_recipes[r]["ingredients"][ing] = 0
        if "sub_section" in custom_meal_recipes[r]:
            for ing in custom_meal_recipes[r]["sub_section"]["ingredients"].keys():
                custom_meal_recipes[r]["sub_section"]["ingredients"][ing] = 0

# ---- PDF Generation ----
if st.button("Generate Production Report PDF"):
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    a4_w, a4_h = 210, 297
    left = 10
    page_w = a4_w - 2 * left
    col_w = page_w / 2 - 5
    ch, pad, bottom = 6, 4, a4_h - 17
    xpos = [left, left + col_w + 10]

    # Draw each section - all pass custom_meal_recipes so they use the zeroed-out ingredients if ticked
    last_y = draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom)
    pdf.set_y(last_y)
    last_y = draw_recipes_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_fridge_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)
    pdf.set_y(last_y)
    last_y = draw_meat_veg_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes=custom_meal_recipes)

    pdf_buffer = pdf.output(dest="S").encode("latin1")
    st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=f"daily_production_report_{datetime.today().strftime('%Y-%m-%d')}.pdf", mime="application/pdf")
