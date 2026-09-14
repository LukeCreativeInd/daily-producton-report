import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
import requests
import base64
import calendar
from zoneinfo import ZoneInfo


# ---------- Page ----------
st.set_page_config(page_title="Production Report", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1280px; padding-top: 2.2rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22); border-radius: 10px; padding: .8rem 1rem;}
[data-testid="stMetricValue"] {font-size: 1.8rem;}
[data-testid="stTabs"] [role="tab"] {padding: .6rem 1rem; font-weight: 600;}
</style>""", unsafe_allow_html=True)
st.title("Production Report")
st.caption("Plan meal quantities, prepare kitchen sheets and revisit saved production runs.")

# ---------- Timezone ----------
LOCAL_TZ = ZoneInfo("Australia/Melbourne")

# ---------- Constants ----------
from meal_catalog import SUMMARY_MEAL_ORDER, ACTIVE_BRANDS, PENDING_RECIPE_MEALS
from quantities import normalize_upload, daily_summary, weekly_summary, historical_summary
from report_pdf import build_daily_report, build_weekly_report, pending_recipe_names
from rerun_support import BULK_RECIPES, parse_run_name, restore_run, saved_run, latest_selected_runs


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
    sha = _get_sha(path)
    if not sha:
        return True  # missing = success
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
    # Authenticated API reads also support private repositories and avoid raw-file caching.
    try:
        response = requests.get(_contents_url(path), headers=_gh_headers(), timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        contents = base64.b64decode(payload['content'], validate=False).decode('utf-8-sig')
        return pd.read_csv(io.StringIO(contents))
    except (requests.RequestException, KeyError, ValueError, UnicodeError) as error:
        raise ValueError('Could not load the saved report data. Refresh and try again.') from error

# ---------- Helpers ----------

def parse_daily_filename(name: str):
    try:
        return parse_run_name(name)
    except Exception:
        return None, None

def human_label_from_filename(name: str):
    # AU date + time from filename (UI only)
    d, t = parse_daily_filename(name)
    if not d or not t:
        return name
    try:
        dt = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H-%M-%S")
        return dt.strftime('%d/%m/%Y at %I:%M:%S %p').replace(' 0', ' ')
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
    # UI only
    n = name.replace("weekly_summary_", "").replace(".pdf", "")
    try:
        rng, tm = n.rsplit("_", 1)
        start, _, end = rng.partition("_to_")
        d1 = datetime.strptime(start, "%Y-%m-%d").strftime("%d/%m/%Y")
        d2 = datetime.strptime(end,   "%Y-%m-%d").strftime("%d/%m/%Y")
        tlabel = datetime.strptime(tm, "%H-%M-%S").strftime("%I:%M %p").lstrip("0")
        return f"Weekly Summary — {d1} to {d2} — {tlabel}"
    except Exception:
        return name

def totals_overview(frame, brands):
    columns = st.columns(len(brands) + 2)
    for column, brand in zip(columns, brands):
        column.metric(brand + ' demand', f"{int(frame[brand].sum()):,}")
    columns[-2].metric('Already Made', f"{int(frame['Already Made'].sum()):,}")
    columns[-1].metric('Meals to produce', f"{int(frame['Total'].sum()):,}")


def generate_and_save(frame, brands, production_date, toggles, result_key, root=None):
    try:
        pdf = build_daily_report(frame, brands, production_date, toggles)
        name, data = saved_run(frame, brands, production_date, toggles, datetime.now(LOCAL_TZ), root)
        st.session_state[result_key] = (name, pdf)
        # Data first: a report is only added to History once its rerun data exists.
        saved_csv = push_csv_to_github(data, name.replace('.pdf', '.csv'))
        saved_pdf = saved_csv and push_pdf_to_github(pdf, name)
    except (ValueError, requests.RequestException) as error:
        st.error(f'Could not complete the report: {error}. If a PDF was generated, it is available below.')
        return
    if saved_csv and saved_pdf:
        st.success('Report saved. Its quantities and preparation settings are ready for future reruns.')
        st.session_state.pop('history_daily', None)
    else:
        st.warning('The report could not be fully saved to History. Download it below, then try again.')


def report_download(result_key):
    if result_key in st.session_state:
        name, pdf = st.session_state[result_key]
        st.caption('Generated file: '+name)
        st.download_button('Download generated PDF', pdf, file_name=name, mime='application/pdf', key=result_key+'_download')


def load_rerun(filename):
    """Load before rendering widgets, then take the user to the report workspace."""
    try:
        frame = fetch_csv_from_github(f"{GITHUB_DAILY_CSV}/{filename.replace('.pdf', '.csv')}")
        if frame is None:
            raise ValueError('The PDF is available, but its saved quantities are missing. This report cannot be rerun automatically.')
        restored = restore_run(frame, filename)
    except ValueError as error:
        st.session_state['history_error'] = str(error)
        return
    for state_key in list(st.session_state):
        if state_key.startswith('rerun_'):
            del st.session_state[state_key]
    st.session_state.pop('history_error', None)
    st.session_state['rerun_loaded'] = (filename, restored)
    st.session_state['main_tab'] = 'Production Report'


def start_new_report():
    for state_key in list(st.session_state):
        if state_key.startswith('rerun_') or state_key in ('daily_result', 'editable_table_daily', 'clean_eats', 'made_active'):
            del st.session_state[state_key]
    for recipe in BULK_RECIPES:
        st.session_state['bulk_'+recipe] = False
    st.session_state['main_tab'] = 'Production Report'


def history_list(files, prefix, daily=True):
    search = st.text_input('Find a report', placeholder='Search by date or report name', key=prefix+'_search')
    formatter = human_label_from_filename if daily else weekly_pretty_label
    files = [f for f in sorted(files, key=lambda f: f['name'], reverse=True)
             if search.casefold() in (f['name']+' '+formatter(f['name'])).casefold()]
    if not files:
        st.info('No reports match this search.' if search else 'No reports saved yet.')
        return
    groups = {}
    for f in files:
        if daily:
            group = month_group_key(f['name'])
        else:
            try:
                dt = datetime.strptime(f['name'].removeprefix('weekly_summary_')[:10], '%Y-%m-%d')
                group = (dt.year, dt.month)
            except ValueError:
                group = (-1, -1)
        groups.setdefault(group, []).append(f)
    for index, group in enumerate(sorted(groups, reverse=True)):
        with st.expander(f"{month_label(*group)} · {len(groups[group])} {'report' if len(groups[group]) == 1 else 'reports'}", expanded=index == 0 or bool(search)):
            for f in groups[group]:
                filename = f['name']
                columns = st.columns([7, 1.5, 1] if daily else [8.5, 1], vertical_alignment='center')
                with columns[0]:
                    st.link_button(formatter(filename), f['download_url'], width='stretch')
                if daily:
                    with columns[1]:
                        st.button('Rerun', key='load_'+filename, on_click=load_rerun, args=(filename,), width='stretch',
                                  help='Load these quantities into the Production Report tab using the current recipes.')
                with columns[-1]:
                    with st.popover('•••', help='Report actions'):
                        st.caption(formatter(filename))
                        confirmed = st.checkbox('Delete this report and its saved data', key='confirm_'+filename)
                        if st.button('Delete report', disabled=not confirmed, key='delete_'+filename):
                            folder = GITHUB_DAILY_PDF if daily else GITHUB_WEEKLY_PDF
                            ok = delete_file_from_github(f'{folder}/{filename}', 'Delete selected report')
                            if ok and daily:
                                ok = delete_file_from_github(f"{GITHUB_DAILY_CSV}/{filename.replace('.pdf', '.csv')}", 'Delete paired report data')
                            if ok:
                                st.session_state.pop('history_daily' if daily else 'history_weekly', None)
                                st.rerun()
                            else:
                                st.error('Could not fully delete the report. Refresh history and try again.')


def rerun_editor(filename):
    key = 'rerun_'+filename
    loaded = st.session_state.get('rerun_loaded')
    if not loaded or loaded[0] != filename:
        return
    frame, brands, settings, issues = loaded[1]
    production_date = date.fromisoformat(parse_run_name(filename)[0])
    st.subheader('Review meal quantities')
    st.caption(f"Production date: {production_date:%d/%m/%Y}. Uses today's recipes and layout. The original report stays available.")
    reviewed = True
    if issues:
        for issue in issues:
            st.warning(issue)
        reviewed = st.checkbox('I have reviewed the omitted meals and brands', key=key+'_omitted')
    old_settings = settings['bulk_prepared'] if settings else dict.fromkeys(BULK_RECIPES, False)
    with st.expander('Already-prepared recipes', expanded=settings is None):
        st.caption('Tick only recipes already prepared in bulk. Their recipe ingredients will be set to zero.')
        toggles = {}
        recipe_columns = st.columns(2)
        for index, name in enumerate(BULK_RECIPES):
            with recipe_columns[index % 2]:
                toggles[name] = st.checkbox(name, value=old_settings[name], key=key+'_bulk_'+name)
        if settings is None:
            st.warning('This older report did not save these four settings. Check them before generating.')
            reviewed = st.checkbox('I have checked the preparation settings', key=key+'_settings_checked') and reviewed
    edited = st.data_editor(frame, disabled=['Product name'], num_rows='fixed', width='stretch', hide_index=True, height=520,
        column_config={b: st.column_config.NumberColumn(min_value=0, step=1, default=0) for b in [*brands, 'Already Made']}, key=key+'_editor')
    try:
        edited = daily_summary(edited, brands)
    except ValueError as error:
        st.error(str(error))
        return
    st.caption('Already Made applies to Clean Eats only. Made Active demand is not reduced.')
    totals_overview(edited, brands)
    pending = pending_recipe_names(dict(zip(edited['Product name'].str.upper(), edited['Total'])))
    if pending:
        st.warning('Recipes are pending for: '+', '.join(pending)+'. Their meal counts are included, but ingredients are not.')
    if st.button('Generate & save rerun', key=key+'_generate', type='primary', disabled=not reviewed):
        generate_and_save(edited, brands, production_date, toggles, key+'_result', settings['root'] if settings else filename)
    report_download(key+'_result')


# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["Production Report", "Document History", "Weekly Summary"], key="main_tab", on_change="rerun")

# ----------------- TAB 1: Daily Flow -----------------
with tab1:
    loaded = st.session_state.get('rerun_loaded')
    if loaded:
        with st.container(border=True):
            heading, action = st.columns([4, 1], vertical_alignment='center')
            with heading:
                st.markdown('**Rerun a saved production report**')
                st.caption(human_label_from_filename(loaded[0]) + ' · Current recipes · Saved quantities')
            with action:
                st.button('Start a new report', on_click=start_new_report, width='stretch')
        rerun_editor(loaded[0])
    else:
        st.subheader("1. Upload meal quantities")
        st.caption("Use the cleaned Clean Eats and/or Made Active files. To reuse saved quantities, open Document History.")
        uploaded_files = {}
        col1, col2 = st.columns(2)
        with col1: uploaded_files['Clean Eats'] = st.file_uploader("Clean Eats File", type=["csv", "xlsx"], key="clean_eats")
        with col2: uploaded_files['Made Active'] = st.file_uploader("Made Active File", type=["csv", "xlsx"], key="made_active")

        st.subheader("2. Production date")
        selected_date = st.date_input("Production Date", value=datetime.now(LOCAL_TZ))
        selected_date_str = selected_date.strftime('%Y-%m-%d')

        with st.expander('Already-prepared recipes (optional)'):
            st.caption('Tick only recipes already prepared in bulk. Their recipe ingredients will be set to zero.')
            bulk_toggles = {r: st.checkbox(r, key=f"bulk_{r}") for r in BULK_RECIPES}

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
                    st.stop()
                try:
                    df = normalize_upload(df)
                except ValueError as error:
                    st.error(f"{brand}: {error}")
                    st.stop()
                dataframes.append(df); brand_names.append(brand)
        else:
            st.info("Upload at least one production file to generate a daily report.")

        # --- Editable merged summary ---
        if dataframes:
            # Only include the current production meal options in the summary table.
            # This prevents POS materials, packs, memberships, or other non-meal products
            # from appearing in the production report.
            all_products = SUMMARY_MEAL_ORDER
            rows = []
            for p in all_products:
                row = {"Product name": p, "Already Made": 0}
                for i, df in enumerate(dataframes):
                    row[brand_names[i]] = int(df.loc[df["Product name"]==p,"Quantity"].sum()) if p in df["Product name"].values else 0
                rows.append(row)
            summary_df = pd.DataFrame(rows)
            if brand_names: summary_df = summary_df[["Product name"]+brand_names+["Already Made"]]

            st.subheader("3. Review meal quantities")
            edited_df = st.data_editor(
                summary_df,
                num_rows="fixed",
                width='stretch', hide_index=True, height=520,
                disabled=["Product name"],
                column_config={b: st.column_config.NumberColumn(width=100, min_value=0, step=1, default=0)
                               for b in (brand_names+["Already Made"])},
                key="editable_table_daily"
            )
            try:
                edited_df = daily_summary(edited_df, brand_names)
            except ValueError as error:
                st.error(str(error))
                st.stop()
            st.caption("Blank quantity cells are treated as 0. Already Made applies to Clean Eats only; Made Active demand is not reduced.")

            totals_overview(edited_df, brand_names)
            with st.expander('View final meal totals'):
                st.dataframe(edited_df[['Product name']+brand_names+['Already Made','Total']], width='stretch')

            meal_totals = dict(zip(edited_df["Product name"].str.upper(), edited_df["Total"]))
            pending = pending_recipe_names(meal_totals)
            if pending:
                st.warning(
                    "You can generate this report. Meal counts are included for "
                    + ", ".join(pending)
                    + ", but their ingredient and preparation quantities are not included until their recipes are added."
                )
            if st.button("Generate & Save Production Report PDF", type='primary'):
                generate_and_save(edited_df, brand_names, selected_date, bulk_toggles, 'daily_result')
            report_download('daily_result')

# ----------------- TAB 2: History -----------------
with tab2:
    title_column, refresh_column = st.columns([5, 1], vertical_alignment='center')
    with title_column:
        st.subheader('Saved reports')
    with refresh_column:
        if st.button('Refresh history', width='stretch'):
            st.session_state.pop('history_daily', None)
            st.session_state.pop('history_weekly', None)
    st.caption('Click a report to open its PDF. Rerun loads its quantities into the Production Report tab.')
    if 'history_daily' not in st.session_state:
        st.session_state['history_daily'] = list_files_from_github(GITHUB_DAILY_PDF)
    if 'history_weekly' not in st.session_state:
        st.session_state['history_weekly'] = list_files_from_github(GITHUB_WEEKLY_PDF)
    if st.session_state.get('history_error'):
        st.error(st.session_state['history_error'])
    history_type = st.radio('Report type', ['Daily reports', 'Weekly summaries'], horizontal=True, label_visibility='collapsed')
    is_daily = history_type == 'Daily reports'
    history_list(st.session_state['history_daily' if is_daily else 'history_weekly'],
                 'daily_history' if is_daily else 'weekly_history', is_daily)

# ----------------- TAB 3: Weekly Summary -----------------
with tab3:
    st.subheader("Build a Weekly Summary")

    tabs_week = st.tabs(["From existing reports (recommended)", "From file uploads"])

    # ---- From existing reports ----
    with tabs_week[0]:
        st.caption("Choose the production runs to include. If you select an original and its reruns, only the latest selected version counts. Older test reports saved separately must be deselected manually.")

        today = date.today()
        default_start = today - timedelta(days=today.weekday())   # Monday
        default_end = default_start + timedelta(days=6)           # Sunday

        c1, c2 = st.columns(2)
        with c1:
            week_start = st.date_input("Week start", value=default_start, key="week_start_existing")
        with c2:
            week_end = st.date_input("Week end", value=default_end, key="week_end_existing")

        if "history_daily" not in st.session_state:
            st.session_state["history_daily"] = list_files_from_github(GITHUB_DAILY_PDF)
        all_daily = st.session_state["history_daily"] or []

        def _daily_dt(name: str) -> datetime | None:
            d, t = parse_daily_filename(name)
            if not d or not t:
                return None
            try:
                return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H-%M-%S")
            except Exception:
                return None

        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt = datetime.combine(week_end, datetime.max.time())
        in_range = [f for f in all_daily if (dt := _daily_dt(f["name"])) and start_dt <= dt <= end_dt]

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

        if selected_reports:
            records, missing = [], []
            for n in selected_reports:
                base = n.replace(".pdf", ".csv")
                csv_path = f"{GITHUB_DAILY_CSV}/{base}"
                try:
                    df = fetch_csv_from_github(csv_path)
                except ValueError as error:
                    st.error(str(error))
                    st.stop()
                if df is None:
                    missing.append(base)
                    continue
                records.append((n, df))

            if missing:
                st.error("Missing CSV for:\n\n- " + "\n- ".join(missing))
                st.stop()

            try:
                chosen, skipped = latest_selected_runs(records)
                dfs = [historical_summary(frame) for _, frame in chosen]
            except ValueError as error:
                st.error(str(error))
                st.stop()
            if skipped:
                st.info('Selected versions of the same run were counted once, using the latest selected version. Omitted: '
                        + ', '.join(human_label_from_filename(n) for n in skipped))
            if dfs:
                merged = pd.concat(dfs, ignore_index=True)
                weekly_df = merged.groupby("Product name", as_index=False).sum(numeric_only=True)

                keep_cols = [c for c in ["Product name","Already Made","Total"] if c in weekly_df.columns]
                weekly_df = weekly_df[keep_cols]
                if "Already Made" not in weekly_df.columns:
                    weekly_df["Already Made"] = 0
                if "Total" not in weekly_df.columns:
                    weekly_df["Total"] = 0

                weekly_df["Adjustments"] = 0
                weekly_df = weekly_df[weekly_df["Product name"].isin(SUMMARY_MEAL_ORDER)].copy()
                weekly_df["meal_order"] = weekly_df["Product name"].apply(
                    lambda x: SUMMARY_MEAL_ORDER.index(x)
                )
                weekly_df = weekly_df.sort_values("meal_order").drop(columns=["meal_order"])

                edited_weekly = st.data_editor(
                    weekly_df,
                    num_rows="fixed",
                    width='stretch',
                    key="weekly_editor_existing",
                    disabled=["Product name"],
                    column_config={
                        "Total": st.column_config.NumberColumn(min_value=0, step=1, default=0),
                        "Already Made": st.column_config.NumberColumn(min_value=0, step=1, default=0),
                        "Adjustments": st.column_config.NumberColumn(step=1, default=0),
                    }
                )
                try:
                    edited_weekly = weekly_summary(edited_weekly)
                except ValueError as error:
                    st.error(str(error))
                    st.stop()

                st.dataframe(edited_weekly[["Product name","Already Made","Total","Adjustments","Final Total"]], width='stretch')

                if st.button("Generate & Save Weekly Summary PDF (from selected reports)"):
                    out_df = edited_weekly[["Product name", "Already Made", "Final Total"]].rename(columns={"Final Total": "Total"})
                    try:
                        pdf_bytes = build_weekly_report(out_df, week_start, week_end)
                    except ValueError as error:
                        st.error(str(error))
                        st.stop()
                    now_local = datetime.now(LOCAL_TZ)
                    fname = f"weekly_summary_{week_start.strftime('%Y-%m-%d')}_to_{week_end.strftime('%Y-%m-%d')}_{now_local.strftime('%H-%M-%S')}.pdf"
                    if push_pdf_to_github(pdf_bytes, fname, weekly=True):
                        st.success("Weekly summary uploaded to GitHub!")
                    else:
                        st.warning("Could not upload weekly summary.")
                    st.download_button("📄 Download Weekly Summary PDF", pdf_bytes, file_name=fname, mime="application/pdf")
        else:
            st.info("Pick your week above — reports in that range will appear here to select.")

    # ---- From file uploads ----
    with tabs_week[1]:
        st.caption("Optional: upload Clean Eats or Made Active CSV/XLSX files from the week.")
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
                    st.stop()
                try:
                    df = normalize_upload(df)
                except ValueError as error:
                    st.error(f"{f.name}: {error}")
                    st.stop()
                dfs.append(df)

            if dfs:
                merged = pd.concat(dfs, ignore_index=True)
                weekly_df = merged.groupby("Product name", as_index=False)["Quantity"].sum().rename(columns={"Quantity":"Total"})
                weekly_df["Already Made"] = 0
                weekly_df["Adjustments"] = 0
                weekly_df = weekly_df[weekly_df["Product name"].isin(SUMMARY_MEAL_ORDER)].copy()
                weekly_df["meal_order"] = weekly_df["Product name"].apply(
                    lambda x: SUMMARY_MEAL_ORDER.index(x)
                )
                weekly_df = weekly_df.sort_values("meal_order").drop(columns=["meal_order"])

                edited_weekly = st.data_editor(
                    weekly_df,
                    num_rows="fixed",
                    width='stretch',
                    key="weekly_editor_upload",
                    disabled=["Product name"],
                    column_config={
                        "Total": st.column_config.NumberColumn(min_value=0, step=1, default=0),
                        "Already Made": st.column_config.NumberColumn(min_value=0, step=1, default=0),
                        "Adjustments": st.column_config.NumberColumn(step=1, default=0),
                    }
                )
                try:
                    edited_weekly = weekly_summary(edited_weekly)
                except ValueError as error:
                    st.error(str(error))
                    st.stop()

                st.dataframe(edited_weekly[["Product name","Already Made","Total","Adjustments","Final Total"]], width='stretch')

                if st.button("Generate & Save Weekly Summary PDF (from uploads)"):
                    out_df = edited_weekly[["Product name", "Already Made", "Final Total"]].rename(columns={"Final Total": "Total"})
                    try:
                        pdf_bytes = build_weekly_report(out_df, week_start2, week_end2)
                    except ValueError as error:
                        st.error(str(error))
                        st.stop()
                    now_local = datetime.now(LOCAL_TZ)
                    fname = f"weekly_summary_{week_start2.strftime('%Y-%m-%d')}_to_{week_end2.strftime('%Y-%m-%d')}_{now_local.strftime('%H-%M-%S')}.pdf"
                    if push_pdf_to_github(pdf_bytes, fname, weekly=True):
                        st.success("Weekly summary uploaded to GitHub!")
                    else:
                        st.warning("Could not upload weekly summary.")
                    st.download_button("📄 Download Weekly Summary PDF", pdf_bytes, file_name=fname, mime="application/pdf")
        else:
            st.info("Add weekly CSV/XLSX files above, or switch to the 'From existing reports' tab.")
