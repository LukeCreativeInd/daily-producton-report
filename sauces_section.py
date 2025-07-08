import math

def draw_sauces_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None):
    sauces = {
        "Thai Sauce": {
            "ingredients": [("Green Curry Paste", 7), ("Coconut Cream", 90)],
            "meal_key": "THAI GREEN CHICKEN CURRY"
        },
        "Lamb Sauce": {
            "ingredients": [("Greek Yogurt", 20), ("Garlic", 2), ("Salt", 1)],
            "meal_key": "LAMB SOUVLAKI"
        }
    }
    # Add page and heading
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Sauces", ln=1, align='C')
    pdf.ln(5)
    heights = [pdf.get_y(), pdf.get_y()]
    col = 0
    for name, data in sauces.items():
        # All tables are similar size, but let's keep it robust for future expansion
        rows = 2 + len(data["ingredients"])
        block_h = rows * ch + pad
        col = 0 if heights[0] <= heights[1] else 1
        # New page if necessary
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
        tm = meal_totals.get(data["meal_key"], 0)
        for ing, am in data["ingredients"]:
            pdf.set_x(x)
            pdf.cell(col_w * 0.3, ch, ing[:20], 1)
            pdf.cell(col_w * 0.2, ch, str(am), 1)
            pdf.cell(col_w * 0.2, ch, str(tm), 1)
            pdf.cell(col_w * 0.3, ch, str(am * tm), 1)
            pdf.ln(ch)
        heights[col] = pdf.get_y() + pad
    return max(heights)
