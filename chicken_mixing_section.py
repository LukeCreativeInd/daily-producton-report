import math

def draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y):
    # Two-column logic, like bulk_section
    heights = [start_y if start_y is not None else pdf.get_y(), start_y if start_y is not None else pdf.get_y()]
    col = 0

    mixes = [
        # (Mix Title, Ingredients, meal_key, divisor, extra_meals)
        ("Pesto", [("Chicken", 110), ("Sauce", 80)], "CHICKEN PESTO PASTA", 50, 1),
        ("Butter Chicken", [("Chicken", 120), ("Sauce", 90)], "BUTTER CHICKEN", 50, 2),
        ("Broccoli Pasta", [("Chicken", 100), ("Sauce", 100)], "CHICKEN AND BROCCOLI PASTA", 50, 1),
        ("Thai", [("Chicken", 110), ("Sauce", 90)], "THAI GREEN CHICKEN CURRY", 50, 1),
        ("Gnocchi", [("Gnocchi", 150), ("Chicken", 80), ("Sauce", 200), ("Spinach", 25)], "CREAMY CHICKEN & MUSHROOM GNOCCHI", 36, 1)
    ]

    def next_pos(heights, col, block_h):
        if heights[col] + block_h > bottom:
            col = 1 - col
            if heights[col] + block_h > bottom:
                pdf.add_page()
                heights = [pdf.get_y(), pdf.get_y()]
                col = 0
        return heights, col

    for name, ingredients, meal_key, divisor, extra in mixes:
        # Estimate the height of the block (header + header row + ingredient rows + pad)
        block_h = (2 + len(ingredients)) * ch + pad
        heights, col = next_pos(heights, col, block_h)
        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)
        amt = meal_totals.get(meal_key, 0)
        batches = math.ceil((amt + extra) / divisor) if divisor else 1
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, name, ln=1, fill=True)
        pdf.set_font("Arial", "B", 8)
        pdf.set_x(x)
        for h, w in [("Ingredient", 0.28), ("Qty/Batch", 0.24), ("Amount", 0.24), ("Batches", 0.24)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)
        for ing, qty in ingredients:
            pdf.set_x(x)
            pdf.cell(col_w * 0.28, ch, ing, 1)
            pdf.cell(col_w * 0.24, ch, str(qty), 1)
            pdf.cell(col_w * 0.24, ch, str(amt), 1)
            pdf.cell(col_w * 0.24, ch, str(batches), 1)
            pdf.ln(ch)
        heights[col] = pdf.get_y() + pad

    return max(heights)
