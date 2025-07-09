import math
from datetime import datetime

# --- BULK SECTIONS (match names to uploaded CSV exactly) ---
bulk_sections = [
    # ... (existing bulk_sections unchanged)
]

def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    title1 = f"Daily Production Report - {header_date or datetime.today().strftime('%d/%m/%Y')}"
    if not start_y:
        pdf.add_page()
        pdf.set_y(0)
    else:
        pdf.set_y(start_y)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title1, ln=1, align='C')
    pdf.ln(5)

    heights = [pdf.get_y(), pdf.get_y()]
    col = 0
    def next_pos(heights, col, block_h, title=None):
        if heights[col] + block_h > bottom:
            col = 1 - col
            if heights[col] + block_h > bottom:
                pdf.add_page()
                if title:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, title, ln=1, align='C')
                    pdf.ln(5)
                heights = [pdf.get_y(), pdf.get_y()]
        return heights, col

    for sec in bulk_sections:
        block_h = (len(sec['ingredients']) + 2) * ch + pad
        heights, col = next_pos(heights, col, block_h, title1)
        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, sec['title'], ln=1, fill=True)
        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in [("Ingredient", 0.4), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Total", 0.15), ("Batches", 0.15)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)
        total_meals = sum(meal_totals.get(m.upper(), 0) for m in sec['meals'])
        batches = math.ceil(total_meals / sec['batch_size']) if sec['batch_size'] > 0 else 0
        for ingr, per in sec['ingredients'].items():
            qty = per * total_meals
            adj = round(qty / batches) if batches else round(qty, 2)
            lbl = str(batches) if ingr == sec['batch_ingredient'] else ""
            pdf.set_x(x)
            pdf.cell(col_w * 0.4, ch, ingr[:20], 1)
            pdf.cell(col_w * 0.15, ch, str(per), 1)
            pdf.cell(col_w * 0.15, ch, str(total_meals), 1)
            pdf.cell(col_w * 0.15, ch, str(adj), 1)
            pdf.cell(col_w * 0.15, ch, lbl, 1)
            pdf.ln(ch)
        heights[col] = pdf.get_y() + pad
    return max(heights)
