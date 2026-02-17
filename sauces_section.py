import math
from utils import fmt_int_up, fmt_weight, fmt_qty

def draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None):
    sauces = {
        "Thai Sauce": {
            "ingredients": [("Green Curry Paste", 7.21), ("Coconut Cream", 97.85)],
            "meal_key": "THAI GREEN CHICKEN CURRY"
        },
        "Lamb Sauce": {
            "ingredients": [("Greek Yogurt", 20), ("Garlic", 1), ("Salt", 0.2)],
            "meal_key": "LAMB SOUVLAKI"
        }
    }

    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Sauces", ln=1, align='C')
    pdf.ln(5)

    heights = [pdf.get_y(), pdf.get_y()]
    col = 0

    for name, data in sauces.items():
        if not isinstance(data, dict) or "ingredients" not in data or "meal_key" not in data:
            continue
        if not isinstance(data["ingredients"], list):
            continue

        rows = 2 + len(data["ingredients"])
        block_h = rows * ch + pad

        col = 0 if heights[0] <= heights[1] else 1
        if heights[col] + block_h > bottom:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Sauces (cont'd)", ln=1, align='C')
            pdf.ln(5)
            heights = [pdf.get_y(), pdf.get_y()]
            col = 0

        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)

        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, name, ln=1, fill=True)

        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in [("Ingredient", 0.3), ("Meal Amount", 0.2), ("Total Meals", 0.2), ("Required Ingredient", 0.3)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)

        pdf.set_font("Arial", "", 8)

        key = data["meal_key"].upper()
        tm = meal_totals.get(key, 0)
        if not isinstance(tm, (int, float)):
            tm = 0

        for ing, am in data["ingredients"]:
            req_ing = (am * tm) if isinstance(am, (int, float)) and isinstance(tm, (int, float)) else 0
            pdf.set_x(x)
            pdf.cell(col_w * 0.3, ch, str(ing)[:20], 1)
            # ✅ per-unit exact (as listed)
            pdf.cell(col_w * 0.2, ch, fmt_qty(am), 1)
            pdf.cell(col_w * 0.2, ch, str(int(tm)), 1)
            # ✅ totals rounded up
            pdf.cell(col_w * 0.3, ch, fmt_int_up(req_ing), 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    return max(heights)
