import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os, copy, glob
import requests
import base64

from bulk_section import draw_bulk_section, bulk_sections
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

st.set_page_config(page_title="Production Report", layout="wide")
st.title("📦 Production Report")

# --- Custom Summary Meal Order ---
SUMMARY_MEAL_ORDER = [
    "Spaghetti Bolognese",
    "Beef Chow Mein",
    "Shepherd's Pie",
    "Beef Burrito Bowl",
    "Beef Meatballs",
    "Lebanese Beef Stew",
    "Mongolian Beef",
    "Chicken with Vegetables",
    "Chicken with Sweet Potato and Beans",
    "Naked Chicken Parma",
    "Chicken Pesto Pasta",
    "Chicken and Broccoli Pasta",
    "Butter Chicken",
    "Thai Green Chicken Curry",
    "Moroccan Chicken",
    "Steak with Mushroom Sauce",
    "Creamy Chicken & Mushroom Gnocchi",
    "Roasted Lemon Chicken & Potatoes",
    "Beef Lasagna",
    "Bean Nachos with Rice",
    "Lamb Souvlaki",
    "Chicken Fajita Bowl",
    "Steak On Its Own",
    "Chicken On Its Own",
    "Family Mac and 3 Cheese Pasta Bake",
    "Baked Family Lasagna"
]

# --- GitHub Repo Settings ---
GITHUB_REPO = "LukeCreativeInd/kitchen_planner_test"
GITHUB_FOLDER = "reports"

def push_pdf_to_github(pdf_bytes, filename):
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{filename}"
    github_token = st.secrets["GITHUB_TOKEN"]
    b64_pdf = base64.b64encode(pdf_bytes).decode()
    headers = {'Authorization': f'token {github_token}'}
    sha = None
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200 and 'sha' in r.json():
        sha = r.json()['sha']
    data = {
        "message": f"Add production report {filename}",
        "content": b64_pdf,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha
    resp = requests.put(api_url, headers=headers, json=data)
    if resp.status_code not in (200, 201):
        st.error(f"GitHub upload failed: {resp.status_code} - {resp.text}")
    return resp.status_code in (200, 201)

def list_reports_from_github():
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    github_token = st.secrets["GITHUB_TOKEN"]
    headers = {'Authorization': f'token {github_token}'}
    r = requests.get(api_url, headers=headers)
    if r.status_code != 200:
        return []
    files = r.json()
    return [
        {"name": f["name"], "download_url": f["download_url"]}
        for f in files if f["name"].endswith(".pdf")
    ]

# --- Tabs Layout ---
tab1, tab2 = st.tabs(["📥 Upload & Generate", "📄 Document History"])

with tab1:
    st.subheader("Step 1: Upload Production Files")
    uploaded_files = {}
    col1, col2, col3 = st.columns(3)
    with col1:
        uploaded_files['Clean Eats'] = st.file_uploader("Clean Eats File", type=["csv", "xlsx"], key="clean_eats")
    with col2:
        uploaded_files['Made Active'] = st.file_uploader("Made Active File", type=["csv", "xlsx"], key="made_active")
    with col3:
        uploaded_files['Elite Meals'] = st.file_uploader("Elite Meals File", type=["csv", "xlsx"], key="elite_meals")

    if not any(uploaded_files.values()):
        st.info("Upload at least one production file to begin.")
        st.stop()

    st.subheader("Step 2: Select Report Date")
    selected_date = st.date_input("Production Date", value=datetime.today())
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    now = datetime.now()
    now_str = now.strftime('%H-%M-%S')
    selected_date_header = selected_date.strftime('%d/%m/%Y')

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
            df = df.groupby("Product name", as_index=False).sum()
            dataframes.append(df)
            brand_names.append(brand)

    if not dataframes:
        st.warning("No valid data to process.")
        st.stop()

    # --- Editable merged summary table with Already Made column ---
    all_products = sorted(set(p for df in dataframes for p in df["Product name"]))
    summary_data = []
    for p in all_products:
        row = {"Product name": p}
        for i, df in enumerate(dataframes):
            brand = brand_names[i]
            qty = int(df.loc[df["Product name"]==p, "Quantity"].sum()) if p in df["Product name"].values else 0
            row[brand] = qty
        row["Already Made"] = 0
        summary_data.append(row)
    summary_df = pd.DataFrame(summary_data)
    if brand_names:
        summary_df = summary_df[["Product name"] + brand_names + ["Already Made"]]
    else:
        summary_df = summary_df[["Product name", "Already Made"]]

    st.subheader("Step 4: Adjust Quantities (if needed)")

    # Show editable table (user can enter Already Made)
    edited_df = st.data_editor(
        summary_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={b: {"width": 70} for b in brand_names + ["Already Made"]},
        key="editable_table"
    )

    # --- Calculate and display the live Total column right below ---
    if brand_names:
        edited_df["Total"] = (
            edited_df[brand_names].sum(axis=1) - edited_df["Already Made"]
        ).clip(lower=0)
    else:
        edited_df["Total"] = 0

    st.dataframe(edited_df[["Product name"] + brand_names + ["Already Made", "Total"]], use_container_width=True)

    # --- Use live totals for rest of the app ---
    meal_totals = dict(zip(edited_df["Product name"].str.upper(), edited_df["Total"]))

    # --- Patch meal_recipes for bulk-toggles ---
    custom_meal_recipes = copy.deepcopy(meal_recipes)
    for r, checked in bulk_toggles.items():
        if checked and r in custom_meal_recipes:
            for ing in custom_meal_recipes[r].get("ingredients", {}).keys():
                custom_meal_recipes[r]["ingredients"][ing] = 0
            if "sub_section" in custom_meal_recipes[r]:
                for ing in custom_meal_recipes[r]["sub_section"]["ingredients"].keys():
                    custom_meal_recipes[r]["sub_section"]["ingredients"][ing] = 0

    # --- PAGE 1: Draw Summary Table with TOTAL row and proper column widths ---
    def draw_summary_section(pdf, edited_df, brand_names, report_date):
        pdf.add_page()
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 9, f"Meal Production Summary - {report_date}", ln=1, align='C')
        pdf.ln(3)

        # Table Header
        pdf.set_font("Arial", "B", 8)
        n_brands = len(brand_names)
        # Dynamic column widths
        meal_col_w = 45  # main dish name
        brand_col_w = 19  # per brand
        already_made_col_w = 21
        total_col_w = 22
        col_widths = (
            [meal_col_w] +
            [brand_col_w] * n_brands +
            [already_made_col_w, total_col_w]
        )
        headers = ["Meal"] + brand_names + ["Already Made", "Total"]
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 7, h, 1, 0, 'C')
        pdf.ln(7)

        # Table Rows
        pdf.set_font("Arial", "", 8)
        for idx, row in edited_df.iterrows():
            pdf.cell(col_widths[0], 6, str(row["Product name"]), 1)
            for i, brand in enumerate(brand_names):
                qty = row[brand] if brand in row else 0
                pdf.cell(col_widths[i+1], 6, str(qty), 1)
            pdf.cell(col_widths[n_brands+1], 6, str(row["Already Made"]), 1)
            pdf.cell(col_widths[n_brands+2], 6, str(row["Total"]), 1)
            pdf.ln(6)

        # TOTAL row
        pdf.set_font("Arial", "B", 8)
        pdf.cell(col_widths[0], 6, "TOTAL", 1)
        for i, brand in enumerate(brand_names):
            pdf.cell(col_widths[i+1], 6, str(edited_df[brand].sum()), 1)
        pdf.cell(col_widths[n_brands+1], 6, str(edited_df["Already Made"].sum()), 1)
        pdf.cell(col_widths[n_brands+2], 6, str(edited_df["Total"].sum()), 1)
        pdf.ln(6)
        return pdf.get_y()

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

        # --- Sort summary table by custom meal order
        edited_df["meal_order"] = edited_df["Product name"].apply(
            lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999
        )
        sorted_edited_df = edited_df.sort_values("meal_order").drop(columns=["meal_order"])

        draw_summary_section(pdf, sorted_edited_df, brand_names, selected_date_header)
        last_y = pdf.get_y()
        last_y = draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, header_date=selected_date_header)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()
        pdf.set_y(last_y)
        last_y = draw_recipes_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes_override=custom_meal_recipes)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()
        pdf.set_y(last_y)
        last_y = draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()
        pdf.set_y(last_y)
        last_y = draw_fridge_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()
        pdf.set_y(last_y)
        last_y = draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()
        pdf.set_y(last_y)
        last_y = draw_meat_veg_section(pdf, meal_totals, custom_meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=last_y)
        if not isinstance(last_y, (int, float)):
            last_y = pdf.get_y()

        pdf_buffer = pdf.output(dest="S").encode("latin1")
        pdf_filename = f"daily_production_report_{selected_date_str}_{now_str}.pdf"

        if push_pdf_to_github(pdf_buffer, pdf_filename):
            st.success(f"Production report for {selected_date_header} ({now_str}) uploaded to GitHub!")
        else:
            st.warning("Could not upload report to GitHub.")

        st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=pdf_filename, mime="application/pdf")

with tab2:
    st.subheader("Previous Production Reports (from GitHub)")

    refresh = st.button("🔄 Refresh History from GitHub")
    if "history_files" not in st.session_state or refresh:
        files = list_reports_from_github()
        st.session_state["history_files"] = files
    else:
        files = st.session_state["history_files"]

    search = st.text_input("Search reports by date (yyyy-mm-dd) or meal")
    filtered_files = [f for f in files if search.lower() in f["name"].lower()] if search else files

    if not filtered_files:
        st.info("No reports found. Click 'Refresh History from GitHub' if you just uploaded new files.")
    else:
        for f in filtered_files:
            st.markdown(f"- [{f['name']}]({f['download_url']})")
