import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from bulk_section import draw_bulk_section
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

st.set_page_config(page_title="Production Report - Ingredient Exclusion Beta", layout="wide")

st.title("📦 Production Report (with Ingredient Exclusion UI)")

# --- File upload
uploaded_file = st.file_uploader("Upload Production File (CSV or Excel)", type=["csv", "xlsx"])
if not uploaded_file:
    st.info("Upload a production order file to begin.")
    st.stop()

# --- Data Loading
if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)
df.columns = df.columns.str.strip()
if not {"Product name", "Quantity"}.issubset(df.columns):
    st.error("CSV must contain 'Product name' and 'Quantity'")
    st.stop()
df["Product name"] = df["Product name"].str.strip()
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)

# --- Meal Totals
meal_totals = dict(zip(df["Product name"].str.upper(), df["Quantity"]))

# --- Ingredient Inclusion/Exclusion UI
st.header("Ingredient Inclusion/Exclusion per Recipe")
# Hold which ingredients are included per recipe (default: all)
ingredient_exclusion = {}
for meal in meal_recipes.keys():
    ingredients = list(meal_recipes[meal].get("ingredients", {}).keys())
    # By default, all ingredients are included
    default_include = ingredients
    # UI: User can exclude any ingredient from this meal
    selected = st.multiselect(
        f"Ingredients to INCLUDE for {meal} (unselect to EXCLUDE from all calculations):",
        ingredients,
        default=ingredients,
        key=f"{meal}_ingredients"
    )
    # Record the excluded ones
    ingredient_exclusion[meal] = set(ingredients) - set(selected)

st.success("You can now generate a report. Any ingredients you EXCLUDED will be ignored in all calculations for their recipe.")

# --- PDF Generation ---
if st.button("Generate Production Report PDF"):
    # Patch: Rebuild meal_recipes with excluded ingredients zeroed out
    import copy
    custom_meal_recipes = copy.deepcopy(meal_recipes)
    for meal, excluded in ingredient_exclusion.items():
        for ingredient in excluded:
            if ingredient in custom_meal_recipes[meal]["ingredients"]:
                custom_meal_recipes[meal]["ingredients"][ingredient] = 0
        # Also handle sub_section if present
        if "sub_section" in custom_meal_recipes[meal]:
            for ingr in custom_meal_recipes[meal]["sub_section"]["ingredients"].keys():
                if ingr in excluded:
                    custom_meal_recipes[meal]["sub_section"]["ingredients"][ingr] = 0

    # Start building the PDF
    pdf = FPDF()
    pdf.set_auto_page_break(False)
    a4_w, a4_h = 210, 297
    left = 10
    page_w = a4_w - 2 * left
    col_w = page_w / 2 - 5
    ch, pad, bottom = 6, 4, a4_h - 17
    xpos = [left, left + col_w + 10]

    # All draw_* sections must accept custom_meal_recipes (update those functions as needed)
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
