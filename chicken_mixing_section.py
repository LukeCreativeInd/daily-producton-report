import math
from utils import fmt_int_up, fmt_weight, fmt_qty

def draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None):
    """
    Always starts on a NEW page (so it doesn't run directly after Sauces).
    Ignores start_y intentionally — header() controls the top spacing now.
    """

    pdf.add_page()

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Chicken Mixing", ln=1, align='C')
    pdf.ln(5)

    heights = [pdf.get_y(), pdf.get_y()]
    col = 0

    chicken_mixes = {
        "Roast Chicken Mix": {
            "meals": ["ROASTED LEMON CHICKEN & POTATOES", "CHICKEN FAJITA BOWL"],
            "batch_size": 0,
            "ingredients": [("Chicken", 160), ("Oil", 4), ("Roast Chicken Mix", 4)]
        }
    }

    for name, data in chicken_mixes.items():
        ingredients = data["ingredients"]
        amt = sum(meal_totals.get(m.upper(), 0) for m in data["meals"])
        batches = math.ceil(amt / data["batch_size"]) if data["batch_size"] else 0

        block_h = (len(ingredients) + 2) * ch + pad
        col = 0 if heights[0] <= heights[1] else 1
        if heights[col] + block_h > bottom:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Chicken Mixing (cont'd)", ln=1, align='C')
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
        for h, w in [("Ingredient", 0.22), ("Qty/Batch", 0.18), ("Amount", 0.18), ("Total", 0.21), ("Batches", 0.21)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)

        pdf.set_font("Arial", "", 8)
        for ing, qty in ingredients:
            total = qty * amt
            total_per_batch = math.ceil(total / batches) if batches else total

            pdf.set_x(x)
            pdf.cell(col_w * 0.22, ch, str(ing), 1)
            # ✅ per-unit must be exact
            pdf.cell(col_w * 0.18, ch, fmt_qty(qty), 1)
            pdf.cell(col_w * 0.18, ch, str(int(amt)), 1)
            # ✅ totals rounded up
            pdf.cell(col_w * 0.21, ch, fmt_int_up(total_per_batch), 1)
            pdf.cell(col_w * 0.21, ch, str(int(batches)), 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    return max(heights)
