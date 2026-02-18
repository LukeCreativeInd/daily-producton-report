import math
from utils import fmt_int_up, fmt_qty


def draw_prepack_room_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None):
    """
    Pre-Pack Room (combined section)

    Structure:
    - Sauces/Mixes to Prepare
    - Sauces/Mixes to Get Ready
    - Ingredients to Get Ready
    - Chicken to Mix
    - Rice to Mix
    - Prepack Cooked Ingredient Checks (placeholder for now)
    """

    # Start on a new page for cleanliness
    pdf.add_page()

    # Main title
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Pre-Pack Room", ln=1, align="C")
    pdf.ln(2)

    def ensure_page_space(block_h: float):
        if pdf.get_y() + block_h > bottom:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Pre-Pack Room (cont.)", ln=1, align="C")
            pdf.ln(2)

    def draw_group_heading(title: str):
        # Centered, slightly smaller than main title
        ensure_page_space(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, title, ln=1, align="C")
        pdf.ln(1)

    def table_title(x, title):
        pdf.set_xy(x, pdf.get_y())
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, title, ln=1, fill=True)

    def table_headers(x, cols):
        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for label, frac in cols:
            pdf.cell(col_w * frac, ch, label, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)

    # -------------------
    # Column helpers (within a group)
    # -------------------
    def group_init_heights():
        y0 = pdf.get_y()
        return [y0, y0]

    def choose_col(heights):
        return 0 if heights[0] <= heights[1] else 1

    def ensure_space_in_group(heights, block_h, group_heading=None):
        col = choose_col(heights)
        if heights[col] + block_h > bottom:
            col2 = 1 - col
            if heights[col2] + block_h <= bottom:
                col = col2
            else:
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "Pre-Pack Room (cont.)", ln=1, align="C")
                pdf.ln(2)
                if group_heading:
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 8, group_heading, ln=1, align="C")
                    pdf.ln(1)
                heights = group_init_heights()
                col = 0
        return heights, col

    def end_group(heights):
        pdf.set_y(max(heights) + pad)

    # -------------------
    # Sauces/Mixes to Prepare
    # -------------------
    draw_group_heading("Sauces/Mixes to Prepare")
    heights = group_init_heights()

    # Lamb Sauce
    lamb = {
        "title": "Lamb Sauce",
        "meal_key": "LAMB SOUVLAKI",
        "ingredients": [("Greek Yogurt", 20), ("Garlic", 1), ("Salt", 0.2)],
    }

    block_h = (2 + len(lamb["ingredients"])) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Sauces/Mixes to Prepare")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)
    table_title(x, lamb["title"])
    table_headers(x, [("Ingredient", 0.3), ("Meal Amount", 0.2), ("Total Meals", 0.2), ("Required", 0.3)])

    tm = meal_totals.get(lamb["meal_key"].upper(), 0) or 0
    for ing, am in lamb["ingredients"]:
        req = (am * tm)
        pdf.set_x(x)
        pdf.cell(col_w * 0.3, ch, str(ing)[:20], 1)
        pdf.cell(col_w * 0.2, ch, fmt_qty(am), 1)          # exact
        pdf.cell(col_w * 0.2, ch, str(int(tm)), 1)
        pdf.cell(col_w * 0.3, ch, fmt_int_up(req), 1)       # totals rounded up
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad
    end_group(heights)

    # -------------------
    # Sauces/Mixes to Get Ready
    # -------------------
    draw_group_heading("Sauces/Mixes to Get Ready")
    heights = group_init_heights()

    # NOTE:
    # Fajita Sauce + Burrito Sauce are the same sauce (Chunky Salsa).
    # We hide them from print, but we still calculate their totals.
    fajita_meals = meal_totals.get("CHICKEN FAJITA BOWL", 0) or 0
    burrito_meals = meal_totals.get("BEEF BURRITO BOWL", 0) or 0
    chunky_salsa_amt = int(fajita_meals + burrito_meals)
    chunky_salsa_total = (33 * fajita_meals) + (43 * burrito_meals)

    sauces_to_get_ready = [
        ("MONGOLIAN", 70, "MONGOLIAN BEEF"),
        ("MEATBALLS", 120, "BEEF MEATBALLS"),
        ("LEMON", 50, "ROASTED LEMON CHICKEN & POTATOES"),
        ("MUSHROOM", 100, "STEAK WITH MUSHROOM SAUCE"),
        # removed from print: ("FAJITA SAUCE", 33, "CHICKEN FAJITA BOWL"),
        # removed from print: ("BURRITO SAUCE", 43, "BEEF BURRITO BOWL"),
        # printed combined row:
        ("CHUNKY SALSA", None, None),
    ]

    block_h = (2 + len(sauces_to_get_ready)) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Sauces/Mixes to Get Ready")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)
    table_title(x, "Sauces to Get Ready")
    table_headers(x, [("Sauce", 0.4), ("Qty", 0.2), ("Amt", 0.2), ("Total", 0.2)])

    for sauce, qty, meal_key in sauces_to_get_ready:
        if sauce == "CHUNKY SALSA":
            # Qty blank, Amt = combined meals, Total = (33*fajita) + (43*burrito)
            pdf.set_x(x)
            pdf.cell(col_w * 0.4, ch, "CHUNKY SALSA", 1)
            pdf.cell(col_w * 0.2, ch, "", 1)  # qty blank
            pdf.cell(col_w * 0.2, ch, str(int(chunky_salsa_amt)), 1)
            pdf.cell(col_w * 0.2, ch, fmt_int_up(chunky_salsa_total), 1)
            pdf.ln(ch)
            continue

        amt = meal_totals.get(meal_key.upper(), 0) or 0
        total = qty * amt
        pdf.set_x(x)
        pdf.cell(col_w * 0.4, ch, sauce, 1)
        pdf.cell(col_w * 0.2, ch, fmt_qty(qty), 1)          # exact
        pdf.cell(col_w * 0.2, ch, str(int(amt)), 1)
        pdf.cell(col_w * 0.2, ch, fmt_int_up(total), 1)     # totals rounded up
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad

    # NEW: Meat to Get Ready table
    meat_to_get_ready = [
        ("SPAGHETTI BOLOGNESE", 230, "SPAGHETTI BOLOGNESE"),
        ("CHOW MEIN", 230, "BEEF CHOW MEIN"),
        ("SHEPPERDS PIE", 210, "SHEPHERD'S PIE"),
        ("BURRITO BOWL", 130, "BEEF BURRITO BOWL"),
    ]

    block_h = (2 + len(meat_to_get_ready)) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Sauces/Mixes to Get Ready")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)
    table_title(x, "Meat to Get Ready")
    table_headers(x, [("Meat Mix", 0.4), ("Qty", 0.2), ("Amount", 0.2), ("Total", 0.2)])

    for meat_mix, qty, meal_key in meat_to_get_ready:
        amt = meal_totals.get(meal_key.upper(), 0) or 0
        total = qty * amt
        pdf.set_x(x)
        pdf.cell(col_w * 0.4, ch, meat_mix[:20], 1)
        pdf.cell(col_w * 0.2, ch, fmt_qty(qty), 1)          # exact
        pdf.cell(col_w * 0.2, ch, str(int(amt)), 1)
        pdf.cell(col_w * 0.2, ch, fmt_int_up(total), 1)     # totals rounded up
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad
    end_group(heights)

    # -------------------
    # Ingredients to Get Ready
    # -------------------
    draw_group_heading("Ingredients to Get Ready")
    heights = group_init_heights()

    # Parma Cheese (cheese only)
    parma_meals = meal_totals.get("NAKED CHICKEN PARMA", 0) or 0
    parma_rows = [("Mozzarella Cheese", 40, parma_meals)]

    block_h = (2 + len(parma_rows)) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Ingredients to Get Ready")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)
    table_title(x, "Parma Cheese")
    table_headers(x, [("Ingredient", 0.4), ("Qty", 0.2), ("Amt", 0.2), ("Total", 0.2)])

    for ing, qty, amt in parma_rows:
        total = qty * amt
        pdf.set_x(x)
        pdf.cell(col_w * 0.4, ch, ing[:20], 1)
        pdf.cell(col_w * 0.2, ch, fmt_qty(qty), 1)
        pdf.cell(col_w * 0.2, ch, str(int(amt)), 1)
        pdf.cell(col_w * 0.2, ch, fmt_int_up(total), 1)
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad

    # Chicken Pesto Sundried
    pesto_meals = meal_totals.get("CHICKEN PESTO PASTA", 0) or 0
    sundried_qty = 20
    sundried_total = sundried_qty * pesto_meals

    block_h = (2 + 1) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Ingredients to Get Ready")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)
    table_title(x, "Chicken Pesto Sundried")
    table_headers(x, [("Ingredient", 0.4), ("Qty", 0.2), ("Meals", 0.2), ("Total", 0.2)])

    pdf.set_x(x)
    pdf.cell(col_w * 0.4, ch, "Sundried Tomatos", 1)
    pdf.cell(col_w * 0.2, ch, fmt_qty(sundried_qty), 1)
    pdf.cell(col_w * 0.2, ch, str(int(pesto_meals)), 1)
    pdf.cell(col_w * 0.2, ch, fmt_int_up(sundried_total), 1)
    pdf.ln(ch)

    heights[col] = pdf.get_y() + pad
    end_group(heights)

    # -------------------
    # Chicken to Mix
    # -------------------
    draw_group_heading("Chicken to Mix")
    heights = group_init_heights()

    mixes = [
        ("Pesto", [("Chicken", 107), ("Sauce", 80)], "CHICKEN PESTO PASTA", 50, 1),
        ("Butter Chicken", [("Chicken", 123), ("Sauce", 90)], "BUTTER CHICKEN", 50, 2),
        ("Broccoli Pasta", [("Chicken", 102), ("Sauce", 100)], "CHICKEN AND BROCCOLI PASTA", 50, 1),
        ("Thai", [("Chicken", 115.36), ("Sauce", 92.7)], "THAI GREEN CHICKEN CURRY", 50, 1),
        ("Gnocchi", [("Gnocchi", 147), ("Chicken", 80), ("Sauce", 200), ("Spinach", 25)], "CREAMY CHICKEN & MUSHROOM GNOCCHI", 36, 1),
    ]

    for name, ingredients, meal_key, divisor, extra in mixes:
        block_h = (2 + len(ingredients)) * ch + pad
        heights, col = ensure_space_in_group(heights, block_h, "Chicken to Mix")
        x = xpos[col]
        y = heights[col]
        pdf.set_xy(x, y)

        amt = meal_totals.get(meal_key.upper(), 0) or 0
        batches = math.ceil((amt + extra) / divisor) if divisor else 1

        table_title(x, name)
        table_headers(x, [("Ingredient", 0.22), ("Qty/Batch", 0.18), ("Amount", 0.18), ("Total", 0.21), ("Batches", 0.21)])

        for ing, qty in ingredients:
            total = qty * amt
            total_per_batch = math.ceil(total / batches) if batches else total

            pdf.set_x(x)
            pdf.cell(col_w * 0.22, ch, str(ing)[:20], 1)
            pdf.cell(col_w * 0.18, ch, fmt_qty(qty), 1)
            pdf.cell(col_w * 0.18, ch, str(int(amt)), 1)
            pdf.cell(col_w * 0.21, ch, fmt_int_up(total_per_batch), 1)
            pdf.cell(col_w * 0.21, ch, str(int(batches)), 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    end_group(heights)

    # -------------------
    # Rice to Mix
    # -------------------
    draw_group_heading("Rice to Mix")
    heights = group_init_heights()

    amt = meal_totals.get("BEEF BURRITO BOWL", 0) or 0
    batches = math.ceil(amt / 60) if amt else 1
    burrito_ings = [("Salsa", 43), ("Black Beans", 50), ("Corn", 50), ("Rice", 130)]

    block_h = (2 + len(burrito_ings)) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Rice to Mix")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)

    table_title(x, "Beef Burrito")
    table_headers(x, [("Ingredient", 0.23), ("Qty", 0.17), ("Amt", 0.17), ("Total", 0.21), ("Batches", 0.22)])

    for ing, qty in burrito_ings:
        total = qty * amt
        total_per_batch = math.ceil(total / batches) if batches else total
        pdf.set_x(x)
        pdf.cell(col_w * 0.23, ch, ing[:20], 1)
        pdf.cell(col_w * 0.17, ch, fmt_qty(qty), 1)
        pdf.cell(col_w * 0.17, ch, str(int(amt)), 1)
        pdf.cell(col_w * 0.21, ch, fmt_int_up(total_per_batch), 1)
        pdf.cell(col_w * 0.22, ch, str(int(batches)), 1)
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad

    bc_meals = meal_totals.get("BUTTER CHICKEN", 0) or 0
    bc_batches = math.ceil(bc_meals / 70) if bc_meals else 1
    bc_ings = [("Peas", 40), ("Rice", 130)]

    block_h = (2 + len(bc_ings)) * ch + pad
    heights, col = ensure_space_in_group(heights, block_h, "Rice to Mix")
    x = xpos[col]
    y = heights[col]
    pdf.set_xy(x, y)

    table_title(x, "Butter Chicken")
    table_headers(x, [("Ingredient", 0.23), ("Qty", 0.17), ("Amt", 0.17), ("Total", 0.21), ("Batches", 0.22)])

    for ing, qty in bc_ings:
        total = qty * bc_meals
        total_per_batch = math.ceil(total / bc_batches) if bc_batches else total
        pdf.set_x(x)
        pdf.cell(col_w * 0.23, ch, ing[:20], 1)
        pdf.cell(col_w * 0.17, ch, fmt_qty(qty), 1)
        pdf.cell(col_w * 0.17, ch, str(int(bc_meals)), 1)
        pdf.cell(col_w * 0.21, ch, fmt_int_up(total_per_batch), 1)
        pdf.cell(col_w * 0.22, ch, str(int(bc_batches)), 1)
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad
    end_group(heights)

    # -------------------
    # Prepack Cooked Ingredient Checks (placeholder)
    # -------------------
    draw_group_heading("Prepack Cooked Ingredient Checks")
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 6, "TBC", ln=1)
    pdf.ln(1)

    return pdf.get_y()
