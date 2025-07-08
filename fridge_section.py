import math

def draw_fridge_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None):
    left_x = xpos[0]
    right_x = xpos[1]
    y = start_y or pdf.get_y()
    pdf.set_y(y)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "To Pack In Fridge", ln=1, align='C')
    pdf.ln(2)
    
    # Table 1: Sauces to Prepare (left col)
    left_y = pdf.get_y()
    pdf.set_xy(left_x, left_y)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_w, ch, "Sauces to Prepare", ln=1, fill=True)
    pdf.set_x(left_x)
    pdf.set_font("Arial", "B", 8)
    for h, w in [("Sauce", 0.4), ("Qty", 0.2), ("Amt", 0.2), ("Total", 0.2)]:
        pdf.cell(col_w * w, ch, h, 1)
    pdf.ln(ch)
    pdf.set_font("Arial", "", 8)
    sauces = [
        ("MONGOLIAN", 70, "MONGOLIAN BEEF"),
        ("MEATBALLS", 120, "BEEF MEATBALLS"),
        ("LEMON", 50, "ROASTED LEMON CHICKEN & POTATOES"),
        ("MUSHROOM", 100, "STEAK WITH MUSHROOM SAUCE"),
        ("FAJITA SAUCE", 33, "CHICKEN FAJITA BOWL"),
        ("BURRITO SAUCE", 43, "BEEF BURRITO BOWL"),
    ]
    for sauce, qty, meal_key in sauces:
        # For Lemon, always use 115 as "Amt", otherwise use meal totals
        if sauce == "LEMON":
            amt = 115  # or use whatever static value is correct
        else:
            amt = meal_totals.get(meal_key, 0)
        total = qty * amt
        pdf.set_x(left_x)
        pdf.cell(col_w * 0.4, ch, sauce, 1)
        pdf.cell(col_w * 0.2, ch, str(qty), 1)
        pdf.cell(col_w * 0.2, ch, str(amt), 1)
        pdf.cell(col_w * 0.2, ch, str(total), 1)
        pdf.ln(ch)
    left_end_y = pdf.get_y()
    
    # Table 2: Beef Burrito Mix (right col)
    pdf.set_xy(right_x, left_y)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_w, ch, "Beef Burrito Mix", ln=1, fill=True)
    pdf.set_x(right_x)
    pdf.set_font("Arial", "B", 8)
    for h, w in [("Ingredient", 0.4), ("Qty", 0.2), ("Amt", 0.2), ("Total", 0.2)]:
        pdf.cell(col_w * w, ch, h, 1)
    pdf.ln(ch)
    pdf.set_font("Arial", "", 8)
    amt = meal_totals.get("BEEF BURRITO BOWL", 0)
    for ing, qty in [("Salsa", 43), ("Black Beans", 50), ("Corn", 50), ("Rice", 130)]:
        total = qty * amt
        pdf.set_x(right_x)
        pdf.cell(col_w * 0.4, ch, ing, 1)
        pdf.cell(col_w * 0.2, ch, str(qty), 1)
        pdf.cell(col_w * 0.2, ch, str(amt), 1)
        pdf.cell(col_w * 0.2, ch, str(total), 1)
        pdf.ln(ch)
    right_end_y = pdf.get_y()
    
    # Table 3: Parma Mix (below both)
    parma_start_y = max(left_end_y, right_end_y) + pad
    pdf.set_xy(left_x, parma_start_y)
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(col_w, ch, "Parma Mix", ln=1, fill=True)
    pdf.set_x(left_x)
    pdf.set_font("Arial", "B", 8)
    for h, w in [("Ingredient", 0.4), ("Qty", 0.2), ("Amt", 0.2), ("Total", 0.2)]:
        pdf.cell(col_w * w, ch, h, 1)
    pdf.ln(ch)
    pdf.set_font("Arial", "", 8)
    parma_amt = meal_totals.get("NAKED CHICKEN PARMA", 0)
    for ing, qty in [("Napoli Sauce", 50), ("Mozzarella Cheese", 40)]:
        total = qty * parma_amt
        pdf.set_x(left_x)
        pdf.cell(col_w * 0.4, ch, ing, 1)
        pdf.cell(col_w * 0.2, ch, str(qty), 1)
        pdf.cell(col_w * 0.2, ch, str(parma_amt), 1)
        pdf.cell(col_w * 0.2, ch, str(total), 1)
        pdf.ln(ch)
    
    # Return y position for next section
    return pdf.get_y() + pad
