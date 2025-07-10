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

# --- GitHub Repo Settings ---
GITHUB_REPO = "LukeCreativeInd/kitchen_planner_test"
GITHUB_FOLDER = "reports"

def push_pdf_to_github(pdf_bytes, filename):
    """Push PDF to GitHub using the API, saving to /reports/."""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{filename}"
    github_token = st.secrets["GITHUB_TOKEN"]
    b64_pdf = base64.b64encode(pdf_bytes).decode()
    headers = {'Authorization': f'token {github_token}'}
    # Check if file exists for update (gets SHA)
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
    return resp.status_code in (200, 201)

def list_reports_from_github():
    """List all PDFs in /reports/ on GitHub."""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    github_token = st.secrets["GITHUB_TOKEN"]
    headers = {'Authorization': f'token {github_token}'}
    r = requests.get(api_url, headers=headers)
    if r.status_code != 200:
        return []
    files = r.json()
    # Only show PDFs
    return [
        {"name": f["name"], "download_url": f["download_url"]}
        for f in files if f["name"].endswith(".pdf")
    ]

# --- Tabs Layout ---
tab1, tab2 = st.tabs(["📥 Upload & Generate", "📄 Document History"])

with tab1:
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

    # --- Editable merged summary table (without Total) ---
    all_products = sorted(set(p for df in dataframes for p in df["Product name"]))
    summary_data = []
    for p in all_products:
        row = {"Product name": p}
        for i, df in enumerate(dataframes):
            brand = brand_names[i]
            qty = int(df.loc[df["Product name"]==p, "Quantity"].sum()) if p in df["Product name"].values else 0
            row[brand] = qty
        summary_data.append(row)
    summary_df = pd.DataFrame(summary_data)
    if brand_names:
        summary_df = summary_df[["Product name"] + brand_names]
    else:
        summary_df = summary_df[["Product name"]]

    st.subheader("Step 4: Adjust Quantities (if needed)")

    # Show editable table for brand columns only (no Total column yet)
    edited_df = st.data_editor(
        summary_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={b: {"width": 70} for b in brand_names},
        key="editable_table"
    )

    # --- Calculate and display the live Total column right below ---
    if brand_names:
        edited_df["Total"] = edited_df[brand_names].sum(axis=1)
    else:
        edited_df["Total"] = 0

    st.dataframe(edited_df[["Product name"] + brand_names + ["Total"]], use_container_width=True)

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

    # --- PAGE 1: Draw Summary Table ---
    def draw_summary_section(pdf, edited_df, brand_names, report_date):
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Meal Production Summary - {report_date}", ln=1, align='C')
        pdf.ln(5)

        # Table Header
        pdf.set_font("Arial", "B", 10)
        headers = ["Meal"] + brand_names + ["Total"]
        col_widths = [70] + [25] * len(brand_names) + [30]
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 8, h, 1, 0, 'C')
        pdf.ln(8)

        # Table Rows
        pdf.set_font("Arial", "", 10)
        for idx, row in edited_df.iterrows():
            pdf.cell(col_widths[0], 8, str(row["Product name"]), 1)
            for i, brand in enumerate(brand_names):
                qty = row[brand] if brand in row else 0
                pdf.cell(col_widths[i+1], 8, str(qty), 1)
            pdf.cell(col_widths[-1], 8, str(row["Total"]), 1)
            pdf.ln(8)
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

        # PAGE 1: Summary Table
        draw_summary_section(pdf, edited_df, brand_names, selected_date_header)
        last_y = pdf.get_y()

        # Proceed with the rest as before
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

        # Save to GitHub
        pdf_buffer = pdf.output(dest="S").encode("latin1")
        pdf_filename = f"daily_production_report_{selected_date_str}.pdf"

        if push_pdf_to_github(pdf_buffer, pdf_filename):
            st.success(f"Production report for {selected_date_header} uploaded to GitHub!")
        else:
            st.warning("Could not upload report to GitHub.")

        st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=pdf_filename, mime="application/pdf")

with tab2:
    st.subheader("Previous Production Reports (from GitHub)")
    files = list_reports_from_github()
    search = st.text_input("Search reports by date (yyyy-mm-dd) or meal")
    filtered_files = [f for f in files if search.lower() in f["name"].lower()] if search else files
    for f in filtered_files:
        st.markdown(f"- [{f['name']}]({f['download_url']})")
