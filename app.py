
import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, date, timedelta
import os, copy, io
import requests
import base64
import math
import calendar
from zoneinfo import ZoneInfo

from bulk_section import draw_bulk_section, bulk_sections
from recipes_section import draw_recipes_section, meal_recipes
from sauces_section import draw_sauces_section
from fridge_section import draw_fridge_section
from chicken_mixing_section import draw_chicken_mixing_section
from meat_veg_section import draw_meat_veg_section

# ---------- Page ----------
st.set_page_config(page_title="Production Report", layout="wide")
st.title("📦 Production Report")

# ---------- Timezone ----------
LOCAL_TZ = ZoneInfo("Australia/Melbourne")

# ---------- Constants ----------
SUMMARY_MEAL_ORDER = [
    "Spaghetti Bolognese","Beef Chow Mein","Shepherd's Pie","Beef Burrito Bowl","Beef Meatballs",
    "Lebanese Beef Stew","Mongolian Beef","Chicken with Vegetables","Chicken with Sweet Potato and Beans",
    "Naked Chicken Parma","Chicken Pesto Pasta","Chicken and Broccoli Pasta","Butter Chicken",
    "Thai Green Chicken Curry","Moroccan Chicken","Steak with Mushroom Sauce",
    "Creamy Chicken & Mushroom Gnocchi","Roasted Lemon Chicken & Potatoes","Beef Lasagna",
    "Bean Nachos with Rice","Lamb Souvlaki","Chicken Fajita Bowl","Steak On Its Own","Chicken On Its Own",
    "Family Mac and 3 Cheese Pasta Bake","Baked Family Lasagna"
]

# 🔧 UPDATE THESE 2 TO MATCH YOUR REPO / TOKEN SECRET NAME
GITHUB_REPO = "LukeCreativeInd/kitchen_planner_test"
GITHUB_TOKEN_SECRET = "GITHUB_TOKEN"

# Folders
GITHUB_DAILY_PDF = "reports"
GITHUB_WEEKLY_PDF = "reports/weekly"
GITHUB_DAILY_CSV = "reports/data"          # hidden from History; paired with daily PDFs

# ---------- GitHub helpers ----------
def _gh_headers():
    return {"Authorization": f"token {st.secrets[GITHUB_TOKEN_SECRET]}"}

def _contents_url(path: str) -> str:
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"

def _push_bytes_to_github(file_bytes: bytes, path: str, message: str) -> bool:
    api_url = _contents_url(path)
    b64_content = base64.b64encode(file_bytes).decode()
    headers = _gh_headers()

    # get sha if file exists
    sha = None
    r = requests.get(api_url, headers=headers)
    if r.status_code == 200:
        try:
            sha = r.json().get("sha")
        except Exception:
            sha = None

    data = {"message": message, "content": b64_content, "branch": "main"}
    if sha:
        data["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=data)
    return resp.status_code in (200, 201)

def _get_sha(path: str) -> str | None:
    r = requests.get(_contents_url(path), headers=_gh_headers())
    if r.status_code != 200:
        return None
    try:
        return r.json().get("sha")
    except Exception:
        return None

def delete_file_from_github(path: str, message: str = "Delete file") -> bool:
    """DELETE /contents path if present; return True if deleted or already missing."""
    sha = _get_sha(path)
    if not sha:
        return True  # treat missing as success
    payload = {"message": message, "sha": sha, "branch": "main"}
    resp = requests.delete(_contents_url(path), headers=_gh_headers(), json=payload)
    return resp.status_code in (200, 204)

def push_pdf_to_github(pdf_bytes: bytes, filename: str, weekly: bool = False) -> bool:
    folder = GITHUB_WEEKLY_PDF if weekly else GITHUB_DAILY_PDF
    return _push_bytes_to_github(pdf_bytes, f"{folder}/{filename}", f"Add {filename}")

def push_csv_to_github(df: pd.DataFrame, filename: str) -> bool:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return _push_bytes_to_github(csv_bytes, f"{GITHUB_DAILY_CSV}/{filename}", f"Add {filename}")

def list_files_from_github(folder: str, endswith: str = ".pdf"):
    api_url = _contents_url(folder)
    r = requests.get(api_url, headers=_gh_headers())
    if r.status_code != 200:
        return []
    items = r.json()
    return [{"name": it["name"], "download_url": it["download_url"]}
            for it in items if isinstance(it, dict) and it.get("name", "").endswith(endswith)]

def fetch_csv_from_github(path: str) -> pd.DataFrame | None:
    api_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"
    r = requests.get(api_url)
    if r.status_code != 200:
        return None
    try:
        return pd.read_csv(io.StringIO(r.text))
    except Exception:
        return None

# ---------- Helpers ----------
def draw_summary_section(pdf, df, brand_names, report_title):
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, report_title, ln=1, align='C')
    pdf.ln(3)

    n_cols = 1 + len(brand_names) + 2
    a4_w = 210
    available_w = a4_w - 20
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

    pdf.set_font("Arial", "B", 8)
    pdf.cell(col_widths[0], 6, "TOTAL", 1)
    for i, brand in enumerate(brand_names):
        pdf.cell(col_widths[i+1], 6, str(df[brand].sum() if brand in df else 0), 1)
    pdf.cell(col_widths[len(brand_names)+1], 6, str(df["Already Made"].sum()), 1)
    pdf.cell(col_widths[len(brand_names)+2], 6, str(df["Total"].sum()), 1)
    pdf.ln(6)
    return pdf.get_y()

def parse_daily_filename(name: str):
    try:
        base = name.replace("daily_production_report_", "").replace(".pdf", "")
        d, t = base.split("_", 1)
        datetime.strptime(d, "%Y-%m-%d")
        datetime.strptime(t, "%H-%M-%S")
        return d, t
    except Exception:
        return None, None

def human_label_from_filename(name: str):
    # AU date, NO time
    d, _t = parse_daily_filename(name)
    if not d:
        return name
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return f"Daily Report — {dt.strftime('%d/%m/%Y')}"
    except Exception:
        return name

def month_group_key(name: str):
    d, _ = parse_daily_filename(name)
    if not d:
        return (-1, -1)
    try:
        y, m, _day = d.split("-")
        return (int(y), int(m))
    except Exception:
        return (-1, -1)

def month_label(year: int, month: int):
    if year == -1 and month == -1:
        return "Other"
    return f"{calendar.month_name[month]} {year}"

def weekly_pretty_label(name: str) -> str:
    n = name.replace("weekly_summary_", "").replace(".pdf", "")
    try:
        rng, _tm = n.rsplit("_", 1)
        start, _, end = rng.partition("_to_")
        d1 = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
        d2 = datetime.strptime(end,   "%Y-%m-%d").strftime("%d/%m/%Y")
        return f"Weekly Summary — {d1} to {d2}"
    except Exception:
        return name

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📥 Upload & Generate", "📄 Document History", "📆 Weekly Summary"])

# ----------------- TAB 1: Daily Flow -----------------
with tab1:
    st.subheader("Step 1: Upload Production Files")
    uploaded_files = {}
    col1, col2, col3 = st.columns(3)
    with col1: uploaded_files['Clean Eats'] = st.file_uploader("Clean Eats File", type=["csv", "xlsx"], key="clean_eats")
    with col2: uploaded_files['Made Active'] = st.file_uploader("Made Active File", type=["csv", "xlsx"], key="made_active")
    with col3: uploaded_files['Elite Meals'] = st.file_uploader("Elite Meals File", type=["csv", "xlsx"], key="elite_meals")

    st.subheader("Step 2: Select Report Date")
    selected_date = st.date_input("Production Date", value=datetime.now(LOCAL_TZ))
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    now = datetime.now(LOCAL_TZ)
    now_str = now.strftime('%H-%M-%S')

    st.subheader("Step 3: Bulk-Prepared Recipe Toggles")
    BULK_RECIPES = ["Spaghetti Bolognese","Beef Chow Mein","Beef Burrito Bowl","Shepherd's Pie"]
    bulk_toggles = {r: st.checkbox(f"{r} already prepared (set all recipe ingredients to zero)", key=f"bulk_{r}") for r in BULK_RECIPES}

    # --- Parse uploads (optional) ---
    dataframes, brand_names = [], []
    any_uploaded = any(uploaded_files.values())
    if any_uploaded:
        for brand, f in uploaded_files.items():
            if not f: continue
            try:
                df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            except Exception as e:
                st.error(f"{brand} failed to read: {e}")
                continue
            df.columns = df.columns.str.strip()
            if not {"Product name", "Quantity"}.issubset(df.columns):
                st.error(f"{brand} file must have 'Product name' and 'Quantity'")
                continue
            df = df[["Product name", "Quantity"]]
            df["Product name"] = df["Product name"].astype(str).str.strip()
            df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
            df = df.groupby("Product name", as_index=False).sum()
            dataframes.append(df); brand_names.append(brand)
    else:
        st.info("Upload at least one production file to generate a daily report.")

    # --- Editable merged summary ---
    if dataframes:
        all_products = sorted(set(p for df in dataframes for p in df["Product name"]))
        rows = []
        for p in all_products:
            row = {"Product name": p, "Already Made": 0}
            for i, df in enumerate(dataframes):
                row[brand_names[i]] = int(df.loc[df["Product name"]==p, "Quantity"].sum()) if p in df["Product name"].values else 0
            rows.append(row)
        summary_df = pd.DataFrame(rows)
        if brand_names: summary_df = summary_df[["Product name"]+brand_names+["Already Made"]]

        st.subheader("Step 4: Adjust Quantities (if needed)")
        edited_df = st.data_editor(summary_df, num_rows="dynamic", use_container_width=True,
                                   column_config={b: {"width":70} for b in (brand_names+["Already Made"])},
                                   key="editable_table_daily")
        if brand_names:
            edited_df["Total"] = (edited_df[brand_names].sum(axis=1)-edited_df["Already Made"]).clip(lower=0)
        else:
            edited_df["Total"]=0

        edited_df["meal_order"] = edited_df["Product name"].apply(lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999)
        edited_df = edited_df.sort_values("meal_order").drop(columns=["meal_order"])
        st.dataframe(edited_df[["Product name"]+brand_names+["Already Made","Total"]], use_container_width=True)

        meal_totals = dict(zip(edited_df["Product name"].str.upper(), edited_df["Total"]))
        custom_meal_recipes = copy.deepcopy(meal_recipes)
        for r,c in bulk_toggles.items():
            if c and r in custom_meal_recipes:
                for ing in custom_meal_recipes[r].get("ingredients",{}): custom_meal_recipes[r]["ingredients"][ing]=0
                if "sub_section" in custom_meal_recipes[r]:
                    for ing in custom_meal_recipes[r]["sub_section"].get("ingredients",{}): custom_meal_recipes[r]["sub_section"]["ingredients"][ing]=0

        if st.button("Generate & Save Production Report PDF"):
            pdf = FPDF(); pdf.set_auto_page_break(False)
            a4_w,a4_h=210,297; left=10; page_w=a4_w-20; col_w=page_w/2-5; ch,pad,bottom=6,4,a4_h-17; xpos=[left,left+col_w+10]
            draw_summary_section(pdf, edited_df[["Product name"]+brand_names+["Already Made","Total"]], brand_names,
                                 f"Meal Production Summary - {selected_date.strftime('%d/%m/%Y')}")
            pdf.add_page(); y=pdf.get_y()
            y=draw_bulk_section(pdf,meal_totals,xpos,col_w,ch,pad,bottom,start_y=y,header_date=selected_date.strftime('%d/%m/%Y'))
            y=draw_recipes_section(pdf,meal_totals,xpos,col_w,ch,pad,bottom,start_y=y,meal_recipes_override=custom_meal_recipes)
            y=draw_sauces_section(pdf,meal_totals,xpos,col_w,ch,pad,bottom,start_y=y)
            y=draw_fridge_section(pdf,meal_totals,xpos,col_w,ch,pad,bottom,start_y=y)
            y=draw_chicken_mixing_section(pdf,meal_totals,xpos,col_w,ch,pad,bottom,start_y=y)
            y=draw_meat_veg_section(pdf,meal_totals,custom_meal_recipes,bulk_sections,xpos,col_w,ch,pad,bottom,start_y=y)
            pdf_bytes=pdf.output(dest="S").encode("latin1")
            pdf_name=f"daily_production_report_{selected_date_str}_{now_str}.pdf"
            csv_name=f"daily_production_report_{selected_date_str}_{now_str}.csv"
            push_pdf_to_github(pdf_bytes,pdf_name,weekly=False)
            push_csv_to_github(edited_df[["Product name"]+brand_names+["Already Made","Total"]],csv_name)
            st.download_button("📄 Download Production Report PDF",pdf_bytes,file_name=pdf_name,mime="application/pdf")

# ----------------- TAB 2: History -----------------
with tab2:
    st.subheader("Previous Production Reports")

    colh1, colh2 = st.columns(2)

    # ----- Daily -----
    with colh1:
        st.markdown("**Daily Reports**")
        refresh_daily = st.button("🔄 Refresh Daily History")
        if "history_daily" not in st.session_state or refresh_daily:
            st.session_state["history_daily"] = list_files_from_github(GITHUB_DAILY_PDF)

        daily_files = st.session_state.get("history_daily", []) or []
        daily_search = st.text_input("Search daily (yyyy-mm-dd or text)", key="daily_search")
        if daily_search:
            daily_files = [f for f in daily_files if daily_search.lower() in f["name"].lower()]

        # group by month
        groups = {}
        for f in daily_files:
            key = month_group_key(f["name"])
            groups.setdefault(key, []).append(f)

        # sort groups by (year, month) desc; (-1,-1) sinks to bottom
        sorted_groups = sorted(groups.items(), key=lambda kv: kv[0], reverse=True)

        # current month open by default
        today_dt = datetime.now(LOCAL_TZ)
        current_key = (today_dt.year, today_dt.month)

        if not sorted_groups:
            st.info("No daily reports found.")
        else:
            for (y, m), files in sorted_groups:
                label = f"{month_label(y, m)} ({len(files)})"
                expanded = ((y, m) == current_key)

                with st.expander(label, expanded=expanded):

                    # sort by date/time desc using parsed timestamp
                    def ts(f):
                        d, t = parse_daily_filename(f["name"])
                        try:
                            return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H-%M-%S") if d and t else datetime.min
                        except Exception:
                            return datetime.min
                    files_sorted = sorted(files, key=ts, reverse=True)

                    for f in files_sorted:
                        c1, c2 = st.columns([0.8, 0.2])
                        with c1:
                            st.link_button(human_label_from_filename(f["name"]), f["download_url"], use_container_width=True)
                        with c2:
                            confirm = st.checkbox("Confirm", key=f"confirm_daily_{f['name']}")
                            if st.button("🗑 Delete", key=f"del_daily_{f['name']}", type="secondary", disabled=not confirm, use_container_width=True):
                                pdf_path = f"{GITHUB_DAILY_PDF}/{f['name']}"
                                csv_name = f['name'].replace(".pdf", ".csv")
                                csv_path = f"{GITHUB_DAILY_CSV}/{csv_name}"
                                ok_pdf = delete_file_from_github(pdf_path, "Delete daily report PDF")
                                ok_csv = delete_file_from_github(csv_path, "Delete paired daily CSV")
                                if ok_pdf:
                                    st.success("Deleted.")
                                    st.session_state["history_daily"] = list_files_from_github(GITHUB_DAILY_PDF)
                                    st.rerun()
                                else:
                                    st.error("Failed to delete report. Check your GitHub token/permissions.")

    # ----- Weekly -----
    with colh2:
        st.markdown("**Weekly Reports**")
        refresh_weekly = st.button("🔄 Refresh Weekly History")
        if "history_weekly" not in st.session_state or refresh_weekly:
            st.session_state["history_weekly"] = list_files_from_github(GITHUB_WEEKLY_PDF)

        weekly_files = st.session_state.get("history_weekly", []) or []
        weekly_search = st.text_input("Search weekly (yyyy-mm-dd or text)", key="weekly_search")
        if weekly_search:
            weekly_files = [f for f in weekly_files if weekly_search.lower() in f["name"].lower()]

        if not weekly_files:
            st.info("No weekly reports found.")
        else:
            def wts(f):
                n = f["name"].replace("weekly_summary_", "").replace(".pdf", "")
                try:
                    rng, tm = n.rsplit("_", 1)
                    _start, _, end = rng.partition("_to_")
                    dt = datetime.strptime(end + " " + tm, "%Y-%m-%d %H-%M-%S")
                    return dt
                except Exception:
                    return datetime.min
            weekly_sorted = sorted(weekly_files, key=wts, reverse=True)

            for f in weekly_sorted:
                c1, c2 = st.columns([0.8, 0.2])
                with c1:
                    st.link_button(weekly_pretty_label(f["name"]), f["download_url"], use_container_width=True)
                with c2:
                    confirm = st.checkbox("Confirm", key=f"confirm_weekly_{f['name']}")
                    if st.button("🗑 Delete", key=f"del_weekly_{f['name']}", type="secondary", disabled=not confirm, use_container_width=True):
                        pdf_path = f"{GITHUB_WEEKLY_PDF}/{f['name']}"
                        ok_pdf = delete_file_from_github(pdf_path, "Delete weekly summary PDF")
                        if ok_pdf:
                            st.success("Deleted.")
                            st.session_state["history_weekly"] = list_files_from_github(GITHUB_WEEKLY_PDF)
                            st.rerun()
                        else:
                            st.error("Failed to delete weekly report. Check your GitHub token/permissions.")

# ----------------- TAB 3: Weekly Summary -----------------
with tab3:
    st.subheader("Build a Weekly Summary")

    tabs_week = st.tabs(["From existing reports (recommended)", "From file uploads"])

    # ---- From existing reports ----
    with tabs_week[0]:
        st.caption("Pick a week, then choose daily reports in that range — I’ll fetch their paired CSVs automatically.")

        # Week selector first (also used as filter)
        today = date.today()
        default_start = today - timedelta(days=today.weekday())   # Monday
        default_end = default_start + timedelta(days=6)           # Sunday

        c1, c2 = st.columns(2)
        with c1:
            week_start = st.date_input("Week start", value=default_start, key="week_start_existing")
        with c2:
            week_end = st.date_input("Week end", value=default_end, key="week_end_existing")

        # Get list of daily PDFs (cached in session)
        if "history_daily" not in st.session_state:
            st.session_state["history_daily"] = list_files_from_github(GITHUB_DAILY_PDF)
        all_daily = st.session_state["history_daily"] or []

        # Helper to parse datetime from file name
        def _daily_dt(name: str) -> datetime | None:
            d, t = parse_daily_filename(name)
            if not d or not t:
                return None
            try:
                return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H-%M-%S")
            except Exception:
                return None

        # Filter to selected week range (inclusive)
        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end, datetime.max.time())
        in_range = [f for f in all_daily if (dt := _daily_dt(f["name"])) and start_dt <= dt <= end_dt]

        # Pretty labels for multiselect
        in_range_sorted = sorted(in_range, key=lambda f: _daily_dt(f["name"]) or datetime.min, reverse=True)
        options = [f["name"] for f in in_range_sorted]
        label_map = {f["name"]: human_label_from_filename(f["name"]) for f in in_range_sorted}

        st.write(f"**Reports found in range:** {len(options)}")
        selected_reports = st.multiselect(
            "Choose daily reports to include",
            options=options,
            format_func=lambda n: label_map.get(n, n),
            key="weekly_existing_choice"
        )

        # Build weekly table from paired CSVs
        if selected_reports:
            dfs, missing = [], []
            for n in selected_reports:
                base = n.replace(".pdf", ".csv")
                csv_path = f"{GITHUB_DAILY_CSV}/{base}"
                df = fetch_csv_from_github(csv_path)
                if df is None:
                    missing.append(base)
                    continue
                need = {"Product name", "Total"}
                if not need.issubset(df.columns):
                    brand_cols = [c for c in df.columns if c not in ("Product name","Already Made","Total") ]
                    if brand_cols:
                        df["Total"] = (df[brand_cols].sum(axis=1) - df.get("Already Made", 0)).clip(lower=0)
                    else:
                        continue
                dfs.append(df[["Product name","Total"]])

            if missing:
                st.warning("Missing CSV for:\n\n- " + "\n- ".join(missing))

            if dfs:
                merged = pd.concat(dfs, ignore_index=True)
                weekly_df = merged.groupby("Product name", as_index=False)["Total"].sum()
                weekly_df["Adjustments"] = 0
                weekly_df["meal_order"] = weekly_df["Product name"].apply(
                    lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999
                )
                weekly_df = weekly_df.sort_values("meal_order").drop(columns=["meal_order"])

                edited_weekly = st.data_editor(
                    weekly_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="weekly_editor_existing",
                    column_config={"Total": {"width": 90}, "Adjustments": {"width": 110}}
                )
                edited_weekly["Final Total"] = (edited_weekly["Total"] + edited_weekly["Adjustments"]).clip(lower=0)

                st.dataframe(edited_weekly[["Product name","Total","Adjustments","Final Total"]], use_container_width=True)

                if st.button("Generate & Save Weekly Summary PDF (from selected reports)"):
                    pdf = FPDF()
                    pdf.set_auto_page_break(False)

                    # Build a clean dataframe with NO duplicate 'Total' column
                    out_df = edited_weekly[["Product name", "Adjustments", "Final Total"]].copy()
                    out_df = out_df.rename(columns={"Adjustments": "Already Made", "Final Total": "Total"})
                    out_df["Already Made"] = pd.to_numeric(out_df["Already Made"], errors="coerce").fillna(0).astype(int)
                    out_df["Total"] = pd.to_numeric(out_df["Total"], errors="coerce").fillna(0).astype(int)

                    title = f"Weekly Meal Summary - {week_start.strftime('%d/%m/%Y')} to {week_end.strftime('%d/%m/%Y')}"
                    draw_summary_section(pdf, out_df[["Product name","Already Made","Total"]], [], title)

                    buf = pdf.output(dest="S").encode("latin1")
                    now_local = datetime.now(LOCAL_TZ)
                    fname = f"weekly_summary_{week_start.strftime('%Y-%m-%d')}_to_{week_end.strftime('%Y-%m-%d')}_{now_local.strftime('%H-%M-%S')}.pdf"
                    if push_pdf_to_github(buf, fname, weekly=True):
                        st.success("Weekly summary uploaded to GitHub!")
                    else:
                        st.warning("Could not upload weekly summary.")
                    st.download_button("📄 Download Weekly Summary PDF", buf, file_name=fname, mime="application/pdf")
        else:
            st.info("Pick your week above — reports in that range will appear here to select.")

    # ---- From file uploads (kept for flexibility) ----
    with tabs_week[1]:
        st.caption("Optional: upload raw CSV/XLSX files from the week (any brand/day).")
        week_files = st.file_uploader("Weekly files", type=["csv","xlsx"], accept_multiple_files=True, key="weekly_files_upload")

        today2 = date.today()
        default_start2 = today2 - timedelta(days=today2.weekday())
        default_end2 = default_start2 + timedelta(days=6)

        c1, c2 = st.columns(2)
        with c1:
            week_start2 = st.date_input("Week start", value=default_start2, key="week_start_upload")
        with c2:
            week_end2 = st.date_input("Week end", value=default_end2, key="week_end_upload")

        if week_files:
            dfs = []
            for f in week_files:
                try:
                    df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
                except Exception as e:
                    st.error(f"Failed to read {f.name}: {e}")
                    continue
                df.columns = df.columns.str.strip()
                if not {"Product name","Quantity"}.issubset(df.columns):
                    st.warning(f"{f.name}: missing 'Product name' or 'Quantity' — skipped.")
                    continue
                df = df[["Product name","Quantity"]]
                df["Product name"] = df["Product name"].astype(str).str.strip()
                df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
                dfs.append(df)

            if dfs:
                merged = pd.concat(dfs, ignore_index=True)
                weekly_df = merged.groupby("Product name", as_index=False)["Quantity"].sum().rename(columns={"Quantity":"Total"})
                weekly_df["Adjustments"] = 0
                weekly_df["meal_order"] = weekly_df["Product name"].apply(
                    lambda x: SUMMARY_MEAL_ORDER.index(x) if x in SUMMARY_MEAL_ORDER else 9999
                )
                weekly_df = weekly_df.sort_values("meal_order").drop(columns=["meal_order"])

                edited_weekly = st.data_editor(
                    weekly_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="weekly_editor_upload",
                    column_config={"Total": {"width": 90}, "Adjustments": {"width": 110}}
                )
                edited_weekly["Final Total"] = (edited_weekly["Total"] + edited_weekly["Adjustments"]).clip(lower=0)

                st.dataframe(edited_weekly[["Product name","Total","Adjustments","Final Total"]], use_container_width=True)

                if st.button("Generate & Save Weekly Summary PDF (from uploads)"):
                    pdf = FPDF()
                    pdf.set_auto_page_break(False)

                    out_df = edited_weekly[["Product name", "Adjustments", "Final Total"]].copy()
                    out_df = out_df.rename(columns={"Adjustments": "Already Made", "Final Total": "Total"})
                    out_df["Already Made"] = pd.to_numeric(out_df["Already Made"], errors="coerce").fillna(0).astype(int)
                    out_df["Total"] = pd.to_numeric(out_df["Total"], errors="coerce").fillna(0).astype(int)

                    title = f"Weekly Meal Summary - {week_start2.strftime('%d/%m/%Y')} to {week_end2.strftime('%d/%m/%Y')}"
                    draw_summary_section(pdf, out_df[["Product name","Already Made","Total"]], [], title)

                    buf = pdf.output(dest="S").encode("latin1")
                    now_local = datetime.now(LOCAL_TZ)
                    fname = f"weekly_summary_{week_start2.strftime('%Y-%m-%d')}_to_{week_end2.strftime('%Y-%m-%d')}_{now_local.strftime('%H-%M-%S')}.pdf"
                    if push_pdf_to_github(buf, fname, weekly=True):
                        st.success("Weekly summary uploaded to GitHub!")
                    else:
                        st.warning("Could not upload weekly summary.")
                    st.download_button("📄 Download Weekly Summary PDF", buf, file_name=fname, mime="application/pdf")
        else:
            st.info("Add weekly CSV/XLSX files above, or switch to the 'From existing reports' tab.")
