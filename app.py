import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date, timedelta
import os, copy
import requests
import base64
import math

from bulk_section import draw_bulk_section, bulk_sections
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

st.set_page_config(page_title="Production Report", layout="wide")
st.title("📦 Production Report")

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

GITHUB_REPO = "LukeCreativeInd/kitchen_planner_test"
GITHUB_DAILY_FOLDER = "reports"
GITHUB_WEEKLY_FOLDER = "reports/weekly"

# ---------- GitHub helpers ----------

def _push_bytes_to_github(file_bytes: bytes, filename: str, folder: str) -> bool:
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{folder}/{filename}"
    github_token = st.secrets["GITHUB_TOKEN"]
    b64_content = base64.b64encode(file_bytes).decode()
    headers = {"Authorization": f"token {github_token}"}

    sha = None
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200:
        try:
            sha = r.json().get("sha")
        except Exception:
            sha = None

    data = {
        "message": f"Add {filename}",
        "content": b64_content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=data)
    if resp.status_code not in (200, 201):
        st.error(f"GitHub upload failed: {resp.status_code} - {resp.text}")
    return resp.status_code in (200, 201)

def push_pdf_to_github(pdf_bytes: bytes, filename: str, weekly: bool = False) -> bool:
    folder = GITHUB_WEEKLY_FOLDER if weekly else GITHUB_DAILY_FOLDER
    return _push_bytes_to_github(pdf_bytes, filename, folder)

def list_reports_from_github(folder: str):
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{folder}"
    github_token = st.secrets["GITHUB_TOKEN"]
    headers = {"Authorization": f"token {github_token}"}
    r = requests.get(api_url, headers=headers)
    if r.status_code != 200:
        return []
    files = r.json()
    return [
        {"name": f["name"], "download_url": f["download_url"]}
        for f in files
        if isinstance(f, dict) and f.get("name", "").endswith(".pdf")
    ]

# ---------- Shared render: summary table to PDF ----------

def draw_summary_section(pdf, df, brand_names, report_title):
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, report_title, ln=1, align='C')
    pdf.ln(3)

    # Dynamic column widths for A4
    n_cols = 1 + len(brand_names) + 2  # Meal + brands + Already Made + Total
    a4_w = 210
    left_margin = 10
    right_margin = 10
    available_w = a4_w - left_margin - right_margin
    meal_col_w = 60 if n_cols <= 6 else 50
    other_col_w = (available_w - meal_col_w) / (n_cols - 1)
    col_widths = [meal_col_w] + [other_col_w] * (n_cols - 1)

    headers = ["Meal"] + brand_names + ["Already Made", "Total"]
    pdf.set_font("Arial", "B", 9)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 7, h, 1, 0, 'C')
    pdf.ln(7)

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 6, str(row["Product name"]), 1)
        for i, brand in enumerate(brand_names):
            qty = row[brand] if brand in row else 0
            pdf.cell(col_widths[i+1], 6, str(qty), 1)
        pdf.cell(col_widths[len(brand_names)+1], 6, str(row["Already Made"]), 1)
        pdf.cell(col_widths[len(brand_names)+2], 6, str(row["Total"]), 1)
        pdf.ln(6)

    # TOTAL row
    pdf.set_font("Arial", "B", 8)
    pdf.cell(col_widths[0], 6, "TOTAL", 1)
    for i, brand in enumerate(brand_names):
        pdf.cell(col_widths[i+1], 6, str(df[brand].sum() if brand in df else 0), 1)
    pdf.cell(col_widths[len(brand_names)+1], 6, str(df["Already Made"].sum()), 1)
    pdf.cell(col_widths[len(brand_names)+2], 6, str(df["Total"].sum()), 1)
    pdf.ln(6)
    return pdf.get_y()

# ---------- Tabs ----------

tab1, tab2, tab3 = st.tabs(["📥 Upload & Generate", "📄 Document History", "📆 Weekly Summary"])

# ----------------- TAB 1: Daily Flow -----------------
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

    # --- Parse & Merge only if something uploaded ---
    dataframes = []
    brand_names = []
    any_uploaded = any(uploaded_files.values())

    if any_uploaded:
        for brand, f in uploaded_files.items():
            if not f:
                continue
            if f.name.endswith(".csv"):
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
            df.columns = df.columns.str.strip()
            if not {"Product name", "Quantity"}.issubset(df.columns):
                st.error(f"{brand} file must have 'Product name' and 'Quantity'")
                continue
            df = df[["Product name", "Quantity"]]
            df["Product name"] = df["Product name"].astype(str).str.strip()
            df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
            df = df.groupby("Product name", as_index=False).sum()
            dataframes.append(df)
            brand_names.append(brand)

        if not dataframes:
            st.info("Upload at least one valid production file to generate a daily report.")
    else:
        st.info("Upload at least one production file to generate a daily report.")

    # --- Editable merged summary table with Already Made column ---
    if dataframes:
        all_products = sorted(set(p for df in dataframes for p in df["Product name"]))
        summary_data = []
        for p in all_products:
            row = {"Product name": p}
            for i, df in enumerate(dataframes):
                brand = brand_names[i]
                qty = int(df.loc[df["Product name"] == p, "Quantity"].sum()) if p in df["Product name"].values else 0
                row[brand] = qty
            row["Already Made"] = 0
            summary_data.append(row)
        summary_df = pd.DataFrame(summary_data)
        if brand_names:
            summary_df = summary_df[["Product name"] + brand_names + ["Already Made"]]
        else:
            summary_df = summary_df[["Product name", "Already Made"]]

        st.subheader("Step 4: Adjust Quantities (if needed)")
        edited_df = st.data_editor(
            summary_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={b: {"width": 70} for b in brand_names + ["Already Made"]},
            key="editable_table_daily"
        )

        # Live totals
        if brand_names:
            edited_df["Total"] = (edited_df[brand_names].sum(axis=1) - edited_df["Already Made"]).clip(lower=0)
        else:
            edited_df["Total"] = 0

        st.dataframe(edited_df[["Product name"] + brand_names + ["Already Made", "Total"]], use_container_width=True)

        # Use live totals for the rest of the app
        meal_totals = dict(zip(edited_df["Product name"].str.upper(), edited_df["Total"]))

        # Patch meal_recipes for bulk toggles
        custom_meal_recipes = copy.deepcopy(meal_recipes)
        for r, checked in bulk_toggles.items():
            if checked and r in custom_meal_recipes:
                for ing in custom_meal_recipes[r].get("ingredients", {}).keys():
                    custom_meal_recipes[r]["ingredients"][ing] = 0
                if "sub_section" in custom_meal_recipes[r]:
                    for ing in custom_meal_recipes[r]["sub_section"]["ingredients"].keys():
                        custom_meal_recipes[r]["sub_section"]["ingredients"][ing] = 0

        # PDF Generation
        if st.button("Generate & Save Production Report PDF"):
            pdf = FPDF()
            pdf.set_auto_page_break(False)
            a4_w, a4_h = 210, 297
            left = 10
            page_w = a4_w - 2 * left
            col_w = page_w / 2 - 5
            ch, pad, bottom = 6, 4, a4_h - 17
            xpos = [left, left + col_w + 10]

            # Sort summary table by your custom order
            edited_df["meal_order"] = edited_df["Product name"].apply(
                lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999
            )
            sorted_edited_df = edited_df.sort_values("meal_order").drop(columns=["meal_order"])

            draw_summary_section(pdf, sorted_edited_df, brand_names, f"Meal Production Summary - {selected_date.strftime('%d/%m/%Y')}")

            # -- Page break --
            pdf.add_page()

            last_y = pdf.get_y()
            last_y = draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, header_date=selected_date.strftime('%d/%m/%Y'))
            pdf.set_y(last_y)
            last_y = draw_recipes_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y, meal_recipes_override=custom_meal_recipes)
            pdf.set_y(last_y)
            last_y = draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
            pdf.set_y(last_y)
            last_y = draw_fridge_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
            pdf.set_y(last_y)
            last_y = draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=last_y)
            pdf.set_y(last_y)
            last_y = draw_meat_veg_section(pdf, meal_totals, custom_meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=last_y)

            pdf_buffer = pdf.output(dest="S").encode("latin1")
            pdf_filename = f"daily_production_report_{selected_date_str}_{now_str}.pdf"

            if push_pdf_to_github(pdf_buffer, pdf_filename, weekly=False):
                st.success(f"Production report for {selected_date.strftime('%d/%m/%Y')} ({now_str}) uploaded to GitHub!")
            else:
                st.warning("Could not upload report to GitHub.")

            st.download_button("📄 Download Production Report PDF", pdf_buffer, file_name=pdf_filename, mime="application/pdf")

# ----------------- TAB 2: History -----------------
with tab2:
    st.subheader("Previous Production Reports (from GitHub)")

    colh1, colh2 = st.columns(2)
    with colh1:
        st.markdown("**Daily Reports**")
        refresh_daily = st.button("🔄 Refresh Daily History")
        if "history_daily" not in st.session_state or refresh_daily:
            st.session_state["history_daily"] = list_reports_from_github(GITHUB_DAILY_FOLDER)
        daily_files = st.session_state.get("history_daily", [])
        daily_search = st.text_input("Search daily (yyyy-mm-dd or text)", key="daily_search")
        if daily_search:
            daily_files = [f for f in daily_files if daily_search.lower() in f["name"].lower()]
        if not daily_files:
            st.info("No daily reports found.")
        else:
            for f in daily_files:
                st.markdown(f"- [{f['name']}]({f['download_url']})")

    with colh2:
        st.markdown("**Weekly Reports**")
        refresh_weekly = st.button("🔄 Refresh Weekly History")
        if "history_weekly" not in st.session_state or refresh_weekly:
            st.session_state["history_weekly"] = list_reports_from_github(GITHUB_WEEKLY_FOLDER)
        weekly_files = st.session_state.get("history_weekly", [])
        weekly_search = st.text_input("Search weekly (yyyy-mm-dd or text)", key="weekly_search")
        if weekly_search:
            weekly_files = [f for f in weekly_files if weekly_search.lower() in f["name"].lower()]
        if not weekly_files:
            st.info("No weekly reports found.")
        else:
            for f in weekly_files:
                st.markdown(f"- [{f['name']}]({f['download_url']})")

# ----------------- TAB 3: Weekly Summary -----------------
with tab3:
    st.subheader("Upload all CSV/XLSX files for the week (all brands/days)")
    week_files = st.file_uploader("Weekly files", type=["csv", "xlsx"], accept_multiple_files=True, key="weekly_files")

    # Date range inputs for naming/headers
    today = date.today()
    # Default to the current week (Mon-Sun)
    default_start = today - timedelta(days=today.weekday())
    default_end = default_start + timedelta(days=6)

    c1, c2 = st.columns(2)
    with c1:
        week_start = st.date_input("Week start", value=default_start, key="week_start")
    with c2:
        week_end = st.date_input("Week end", value=default_end, key="week_end")

    if week_files:
        dfs = []
        for f in week_files:
            try:
                if f.name.endswith(".csv"):
                    df = pd.read_csv(f)
                else:
                    df = pd.read_excel(f)
            except Exception as e:
                st.error(f"Failed to read {f.name}: {e}")
                continue
            df.columns = df.columns.str.strip()
            if not {"Product name", "Quantity"}.issubset(df.columns):
                st.warning(f"{f.name}: missing 'Product name' or 'Quantity' — skipped.")
                continue
            df = df[["Product name", "Quantity"]]
            df["Product name"] = df["Product name"].astype(str).str.strip()
            df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
            dfs.append(df)

        if not dfs:
            st.info("No valid files this week yet.")
        else:
            merged = pd.concat(dfs, ignore_index=True)
            weekly_df = merged.groupby("Product name", as_index=False)["Quantity"].sum().rename(columns={"Quantity": "Total"})
            # Give editor with an “Adjustments” column if needed
            weekly_df["Adjustments"] = 0
            edited_weekly = st.data_editor(
                weekly_df,
                num_rows="dynamic",
                use_container_width=True,
                key="weekly_editor",
                column_config={"Total": {"width": 90}, "Adjustments": {"width": 110}}
            )
            edited_weekly["Final Total"] = (edited_weekly["Total"] + edited_weekly["Adjustments"]).clip(lower=0)

            # Order by your SUMMARY_MEAL_ORDER
            edited_weekly["meal_order"] = edited_weekly["Product name"].apply(
                lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999
            )
            edited_weekly = edited_weekly.sort_values("meal_order").drop(columns=["meal_order"])

            st.dataframe(edited_weekly[["Product name", "Total", "Adjustments", "Final Total"]], use_container_width=True)

            # Generate PDF for weekly summary
            if st.button("Generate & Save Weekly Summary PDF"):
                pdf = FPDF()
                pdf.set_auto_page_break(False)

                # Reuse the daily summary renderer but with weekly columns
                # Build a pseudo daily table with Already Made=Adjustments and Total=Final Total
                out_df = edited_weekly.rename(columns={"Final Total": "Total"})
                out_df.insert(1, "Already Made", out_df["Adjustments"])
                # No brand columns for weekly summary
                brand_cols = []

                pdf_title = f"Weekly Meal Summary - {week_start.strftime('%d/%m/%Y')} to {week_end.strftime('%d/%m/%Y')}"
                draw_summary_section(pdf, out_df[["Product name", "Already Made", "Total"]], brand_cols, pdf_title)

                buf = pdf.output(dest="S").encode("latin1")
                fname = f"weekly_summary_{week_start.strftime('%Y-%m-%d')}_to_{week_end.strftime('%Y-%m-%d')}_{datetime.now().strftime('%H-%M-%S')}.pdf"
                if push_pdf_to_github(buf, fname, weekly=True):
                    st.success("Weekly summary uploaded to GitHub!")
                else:
                    st.warning("Could not upload weekly summary to GitHub.")
                st.download_button("📄 Download Weekly Summary PDF", buf, file_name=fname, mime="application/pdf")
    else:
        st.info("Add all of the week’s CSV/XLSX files above, then generate the weekly summary.")
