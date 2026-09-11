"""PDF rendering shared by the app and offline verification."""
from fpdf import FPDF
from datetime import timedelta
import copy
from meal_catalog import meal_label, check_recipe_readiness
from quantities import daily_summary, normalize_columns, normalize_meal_totals, sorted_meals
from bulk_section import draw_bulk_section, bulk_sections
from recipes_section import draw_recipes_section, meal_recipes
from prepack_room_section import draw_prepack_room_section
from meat_veg_section import draw_meat_veg_section

# ---------- PDF Header (HACCP) ----------
# These are intentionally static and only change when HACCP docs are reviewed.
HACCP_LATEST_ISSUE_DATE = "13/01/24"
HACCP_PREVIOUS_ISSUE_DATE = "28/10/23"
HACCP_APPROVED_BY = "T. Fadlallah"
HACCP_PREPARED_BY = "C. Guzzardi"

class ProductionPDF(FPDF):
    """
    FPDF with a fixed HACCP header rendered on every page.

    Important:
    - Core PDF fonts use latin-1. Any unicode (e.g. “–”, “—”, smart quotes) will crash output().
    - We defensively coerce ALL text going into cell/multi_cell into latin-1 (with replacement)
      so a single bad character can’t break the whole report.
    """

    def __init__(self, *args, header_date_str: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_date_str = header_date_str

        # Header layout constants (mm)
        self._hdr_x = 10
        self._hdr_y = 10
        self._hdr_w = 210 - 20
        # Row heights: main title, date/page, HACCP title, issue row, approved/prepared row
        self._hdr_rows = [12, 10, 8, 6, 6]
        self._hdr_h = sum(self._hdr_rows)
        self._hdr_gap = 6  # space below header before page content starts

        # Copy label (set by app.py while rendering sections)
        self.copy_no = 1
        self.copy_total = 1

    def set_font(self, family=None, style="", size=0):
        return super().set_font("Helvetica" if family == "Arial" else family, style, size)

    # --- latin-1 safety ---
    @staticmethod
    def _latin1(txt) -> str:
        if txt is None:
            return ""
        s = str(txt)
        # Replace unsupported characters rather than throwing UnicodeEncodeError
        return s.encode("latin-1", "replace").decode("latin-1")

    # Override core text writers so all downstream sections are protected
    def cell(self, w, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        text = self._latin1(txt)
        original_size = self.font_size_pt
        available = (w if w else self.w - self.r_margin - self.x) - 2 * self.c_margin
        text_width = self.get_string_width(text) if text else 0
        if text_width > available > 0:
            self.set_font_size(original_size * available / text_width)
        result = super().cell(w=w, h=h, text=text, border=border, align=align or "L",
                              fill=fill, link=link,
                              new_x="LMARGIN" if ln == 1 else ("LEFT" if ln == 2 else "RIGHT"),
                              new_y="NEXT" if ln else "TOP")
        self.set_font_size(original_size)
        return result

    def multi_cell(self, w, h, txt="", border=0, align="J", fill=False):
        return super().multi_cell(w=w, h=h, text=self._latin1(txt), border=border,
                                  align=align, fill=fill, new_x="LMARGIN", new_y="NEXT")

    def header(self):
        # Outer box
        x0, y0, w = self._hdr_x, self._hdr_y, self._hdr_w
        r1, r2, r3, r4, r5 = self._hdr_rows
        self.set_line_width(0.4)
        self.rect(x0, y0, w, self._hdr_h)

        # Row 1: main title
        self.set_xy(x0, y0)
        self.set_font("Arial", "B", 18)
        self.cell(w, r1, "Production Schedule Report", border=0, ln=1, align="C")

        # Row 2: date and page  (IMPORTANT: use ASCII hyphen, not unicode en dash)
        self.set_xy(x0, y0 + r1)
        self.set_font("Arial", "B", 14)
        self.cell(
            w,
            r2,
            f"{self.header_date_str} - Page {self.page_no()}   Copy {self.copy_no}/{self.copy_total}",
            border=0,
            ln=1,
            align="C",
        )

        # Horizontal lines between rows
        y = y0 + r1
        self.line(x0, y, x0 + w, y)
        y = y0 + r1 + r2
        self.line(x0, y, x0 + w, y)
        y = y0 + r1 + r2 + r3
        self.line(x0, y, x0 + w, y)
        y = y0 + r1 + r2 + r3 + r4
        self.line(x0, y, x0 + w, y)

        # Row 3: HACCP title
        self.set_xy(x0, y0 + r1 + r2)
        self.set_font("Arial", "B", 13)
        self.cell(w, r3, "Clean Health Group PTY LTD - HACCP FSP Section F - Form 1", border=0, ln=1, align="C")

        # Row 4: issue dates (2 columns)
        half = w / 2
        self.set_font("Arial", "", 9)
        self.set_xy(x0, y0 + r1 + r2 + r3)
        self.cell(half, r4, f"Latest Issue Date: {HACCP_LATEST_ISSUE_DATE}", border=0, align="C")
        self.cell(half, r4, f"Previous Issue Date: {HACCP_PREVIOUS_ISSUE_DATE}", border=0, ln=1, align="C")
        # vertical split line
        self.line(x0 + half, y0 + r1 + r2 + r3, x0 + half, y0 + r1 + r2 + r3 + r4)

        # Row 5: approved / prepared (2 columns)
        self.set_xy(x0, y0 + r1 + r2 + r3 + r4)
        self.cell(half, r5, f"Approved by: {HACCP_APPROVED_BY}", border=0, align="C")
        self.cell(half, r5, f"Prepared by: {HACCP_PREPARED_BY}", border=0, ln=1, align="C")
        self.line(x0 + half, y0 + r1 + r2 + r3 + r4, x0 + half, y0 + self._hdr_h)

        # Move cursor below header so subsequent content starts in the right place
        self.set_y(y0 + self._hdr_h + self._hdr_gap)


def draw_summary_section(pdf, df, brand_names, production_date):
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, "Meal Production Summary", ln=1, align='C')
    pdf.ln(2)

    # ---- Table ----
    n_cols = 1 + len(brand_names) + 2
    a4_w = 210
    a4_h = 297
    available_w = a4_w - 20
    meal_col_w = 80
    other_col_w = (available_w - meal_col_w) / (n_cols - 1) if n_cols > 1 else available_w
    col_widths = [meal_col_w] + [other_col_w] * (n_cols - 1)

    headers = ["Meal"] + brand_names + ["Already Made", "Total"]
    pdf.set_font("Arial", "B", 9)
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 7, h, 1, 0, 'C')
    pdf.ln(7)

    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 6, meal_label(row["Product name"]), 1)
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

    # ---- Use By Dates block (below meal summary table) ----
    # Dates are inclusive of production date (e.g. 28 days incl today => today + 27)
    use_by = [
        ("Family Lasagna", production_date + timedelta(days=27)),
        ("Beef Lasagna", production_date + timedelta(days=20)),
        ("Individual Meals", production_date + timedelta(days=13)),
    ]
    pdf.ln(3)
    pdf.set_x(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(190, 6, "Use By Dates", 1, ln=1, align="C")
    pdf.set_font("Arial", "", 9)
    pdf.set_x(10)
    for name, expiry in use_by:
        pdf.cell(190 / 3, 6, f"{name} - {expiry:%d/%m/%Y}", 1, align="C")
    pdf.ln(9)
    return pdf.get_y()


def draw_quality_control_section(pdf, frame):
    """A handwriting sheet: only Planned is populated from the validated summary."""
    pdf.add_page()
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 9, 'Quality & Batch Control', ln=1, align='C')
    pdf.ln(2)
    x, y = 10, pdf.get_y()
    widths = [74, 20, 20, 30, 21, 25]
    header_h, half_h, row_h = 16, 8, 7
    pdf.set_line_width(0.3)
    pdf.set_font('Arial', 'B', 9)
    # Vertically merged headings surrounding the Planned/Actual group.
    for index, label in [(0, 'Meal'), (3, 'Batch Number'), (4, 'Label Check'), (5, 'Sign Off')]:
        left = x + sum(widths[:index])
        pdf.set_xy(left, y)
        pdf.cell(widths[index], header_h, label, 1, align='C')
    left = x + widths[0]
    pdf.rect(left, y, widths[1] + widths[2], half_h)
    pdf.set_xy(left, y)
    pdf.cell(widths[1] + widths[2], half_h, 'Total Manufacturing', align='C')
    pdf.set_xy(left, y + half_h)
    pdf.cell(widths[1], half_h, 'Planned', 1, align='C')
    pdf.cell(widths[2], half_h, 'Actual', 1, align='C')
    y += header_h
    pdf.set_font('Arial', '', 8)
    for _, row in frame.iterrows():
        pdf.set_xy(x, y)
        pdf.cell(widths[0], row_h, meal_label(row['Product name']), 1)
        pdf.cell(widths[1], row_h, str(int(row['Total'])), 1, align='C')
        for width in widths[2:]:
            pdf.cell(width, row_h, '', 1)
        y += row_h
    notes_y = y + 5
    pdf.set_xy(x, notes_y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(190, 6, 'Notes', ln=1)
    box_y = notes_y + 6
    pdf.rect(x, box_y, 190, 283 - box_y)
    pdf.set_y(283)


def build_daily_report(frame, brands, production_date, bulk_toggles=None):
    frame = daily_summary(frame, brands)
    totals = normalize_meal_totals(dict(zip(frame['Product name'].str.upper(), frame['Total'])))
    check_recipe_readiness(totals)
    recipes = copy.deepcopy(meal_recipes)
    for name, prepared in (bulk_toggles or {}).items():
        if prepared and name in recipes:
            for ingredient in recipes[name].get('ingredients', {}):
                recipes[name]['ingredients'][ingredient] = 0
            for ingredient in recipes[name].get('sub_section', {}).get('ingredients', {}):
                recipes[name]['sub_section']['ingredients'][ingredient] = 0
    pdf = ProductionPDF(header_date_str=production_date.strftime('%d/%m/%Y'))
    pdf.set_auto_page_break(False)
    for copy_no in (1, 2):
        pdf.copy_no, pdf.copy_total = copy_no, 2
        draw_summary_section(pdf, frame, brands, production_date)
    # One control sheet after the two existing summary copies.
    pdf.copy_no, pdf.copy_total = 1, 1
    draw_quality_control_section(pdf, frame)
    args = ([10, 110], 90, 6, 4, 280)
    for copy_no in (1, 2, 3):
        pdf.copy_no, pdf.copy_total = copy_no, 3
        draw_bulk_section(pdf, totals, *args)
    for copy_no in (1, 2):
        pdf.copy_no, pdf.copy_total = copy_no, 2
        pdf.add_page()
        draw_recipes_section(pdf, totals, *args, meal_recipes_override=recipes)
    pdf.copy_no, pdf.copy_total = 1, 1
    draw_prepack_room_section(pdf, totals, *args)
    for copy_no in (1, 2, 3):
        pdf.copy_no, pdf.copy_total = copy_no, 3
        draw_meat_veg_section(pdf, totals, recipes, bulk_sections, *args)
    return bytes(pdf.output())


def build_weekly_report(frame, start, end):
    if end < start:
        raise ValueError('Week end must be on or after week start.')
    frame = normalize_columns(sorted_meals(frame), ['Total'])
    pdf = ProductionPDF(header_date_str=f'{start:%d/%m/%Y}-{end:%d/%m/%Y}')
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 9, f'Weekly Meal Summary - {start:%d/%m/%Y} to {end:%d/%m/%Y}', ln=1, align='C')
    pdf.ln(2)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(130, 7, 'Meal', 1, align='C')
    pdf.cell(60, 7, 'Total', 1, ln=1, align='C')
    pdf.set_font('Arial', '', 8)
    for _, row in frame.iterrows():
        pdf.cell(130, 6, meal_label(row['Product name']), 1)
        pdf.cell(60, 6, str(int(row['Total'])), 1, ln=1)
    return bytes(pdf.output())
