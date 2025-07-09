import math

def draw_chicken_mixing_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y):
    pdf.set_xy(xpos[0], start_y)
    pdf.set_font("Arial","B",14)
    pdf.cell(0,10,"Chicken Mixing", ln=1, align='C')
    pdf.ln(5)

    mixes = [
        # (Mix Title, Ingredients, meal_key, divisor, extra_meals)
        ("Pesto", [("Chicken",110),("Sauce",80)], "CHICKEN PESTO PASTA", 50, 1),
        ("Butter Chicken", [("Chicken",120),("Sauce",90)], "BUTTER CHICKEN", 50, 2),
        ("Broccoli Pasta", [("Chicken",100),("Sauce",100)], "CHICKEN AND BROCCOLI PASTA", 50, 1),
        ("Thai", [("Chicken",110),("Sauce",90)], "THAI GREEN CHICKEN CURRY", 50, 1),
        ("Gnocchi", [("Gnocchi",150),("Chicken",80),("Sauce",200),("Spinach",25)], "CREAMY CHICKEN & MUSHROOM GNOCCHI", 36, 1)
    ]
    y = pdf.get_y()
    for name, ingredients, meal_key, divisor, extra in mixes:
        amt = meal_totals.get(meal_key, 0)
        batches = math.ceil((amt+extra)/divisor) if divisor else 1
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, name, ln=1, fill=True)
        pdf.set_font("Arial", "B", 8)
        pdf.set_x(xpos[0])
        for h, w in [("Ingredient",0.4),("Qty/Batch",0.3),("Batches",0.3)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial","",8)
        for ing, qty in ingredients:
            pdf.set_x(xpos[0])
            pdf.cell(col_w*0.4, ch, ing, 1)
            pdf.cell(col_w*0.3, ch, str(qty), 1)
            pdf.cell(col_w*0.3, ch, str(batches), 1)
            pdf.ln(ch)
        pdf.ln(2)
    return pdf.get_y()
