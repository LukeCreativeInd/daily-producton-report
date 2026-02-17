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
    pdf.ln(2)

    heights = [pdf.get_y(), pdf.get_y()]
    col = 0

    mixes = [
        ("Pesto", [("Chicken", 107), ("Sauce", 80)], "CHICKEN PESTO PASTA", 50, 1),
        ("Butter Chicken", [("Chicken", 123), ("Sauce", 90)], "BUTTER CHICKEN", 50, 2),
        ("Broccoli Pasta", [("Chicken", 102), ("Sauce", 100)], "CHICKEN AND BROCCOLI PASTA", 50, 1),
        ("Thai", [("Chicken", 115.36), ("Sauce", 92.7)], "THAI GREEN CHICKEN CURRY", 50, 1),
        ("Gnocchi", [("Gnocchi", 147), ("Chicken", 80), ("Sauce", 200), ("Spinach", 25)], "CREAMY CHICKEN & MUSHROOM GNOCCHI", 36, 1),
    ]

    def next_pos(heights, col, block_h):
        # balance columns first
        col = 0 if heights[0] <= heights[1] else 1

        # if doesn't fit in chosen col, try other col
        if heights[col] + block_h > bottom:
            col = 1 - col

        # if still doesn't fit, add a new page
        if heights[col] + block_h > bottom:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Chicken Mixing (cont.)", ln=1, align='C')
            pdf.ln(2)
            heights = [pdf.get_y(), pdf.get_y()]
            col = 0

        return heights, col

    for name, ingredients, meal_key, divisor, extra in mixes:
        block_h = (2 + len(ingredients)) * ch + pad
        heights, col = next_pos(heights, col, block_h)

        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)

        amt = meal_totals.get(meal_key.upper(), 0)
        batches = math.ceil((amt + extra) / divisor) if divisor else 1

        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, name, ln=1, fill=True)

        pdf.set_font("Arial", "B", 8)
        pdf.set_x(x)
        for h, w in [("Ingredient", 0.22), ("Qty/Batch", 0.18), ("Amount", 0.18), ("Total", 0.21), ("Batches", 0.21)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)

        pdf.set_font("Arial", "", 8)
        for ing, qty in ingredients:
            total = qty * amt
            total_per_batch = math.ceil(total / batches) if batches else total

            pdf.set_x(x)
            pdf.cell(col_w * 0.22, ch, str(ing), 1)
            # ✅ per-unit exact (as listed)
            pdf.cell(col_w * 0.18, ch, fmt_qty(qty), 1)
            # Meal count: integer
            pdf.cell(col_w * 0.18, ch, str(int(amt)), 1)
            # ✅ totals rounded up
            pdf.cell(col_w * 0.21, ch, fmt_int_up(total_per_batch), 1)
            # Batches: integer
            pdf.cell(col_w * 0.21, ch, str(int(batches)), 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    return max(heights)
