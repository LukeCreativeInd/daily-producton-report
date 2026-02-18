import math
from datetime import datetime
from utils import fmt_int_up, fmt_qty

# --- BULK SECTIONS (match names to uploaded CSV exactly) ---
bulk_sections = [
    {"title": "Spaghetti Order", "batch_ingredient": "Spaghetti", "batch_size": 85,
     "ingredients": {"Spaghetti": 64, "Oil": 0.7},
     "meals": ["Spaghetti Bolognese"]},

    {"title": "Penne Order", "batch_ingredient": "Penne", "batch_size": 135,
     "ingredients": {"Penne": 59, "Oil": 0.7},
     "meals": ["Chicken Pesto Pasta", "Chicken and Broccoli Pasta"]},

    {"title": "Rice Order", "batch_ingredient": "Rice", "batch_size": 180,
     "ingredients": {"Rice": 53, "Water": 95, "Oil": 1.5},
     "meals": [
         "Beef Chow Mein",
         "Beef Burrito Bowl",
         "Lebanese Beef Stew",
         "Mongolian Beef",
         "Butter Chicken",
         "Thai Green Chicken Curry",
         "Chicken Fajita Bowl"
     ]},

    {"title": "Moroccan Chicken", "batch_ingredient": "Chicken", "batch_size": 0,
     "ingredients": {"Chicken": 180, "Oil": 2, "Lemon Juice": 6, "Moroccan Chicken Mix": 4},
     "meals": ["Moroccan Chicken"]},

    # Premixed Chicken Thigh: remove Oil + Roast Chicken Mix entirely (160g per meal)
    {"title": "Premixed Chicken Thigh", "batch_ingredient": "Premixed Chicken Thigh", "batch_size": 0,
     "ingredients": {"Premixed Chicken Thigh": 160},
     "meals": ["Chicken Fajita Bowl", "Naked Chicken Parma"]},

    {"title": "Steak", "batch_ingredient": "Steak", "batch_size": 0,
     "ingredients": {"Steak": 116.3, "Oil": 1.9, "Baking Soda": 3.8},
     "meals": ["Steak with Mushroom Sauce"]},

    {"title": "Lamb Marinate", "batch_ingredient": "Lamb Shoulder", "batch_size": 0,
     "ingredients": {"Lamb Shoulder": 162, "Oil": 2, "Oregano": 0.3, "Baking Soda": 5.27},
     "meals": ["Lamb Souvlaki"]},

    {"title": "Potato Mash", "batch_ingredient": "Potato", "batch_size": 0,
     "ingredients": {"Potato": 150, "Cooking Cream": 20, "Butter": 7, "Salt": 1.5, "White Pepper": 0.5},
     "meals": ["Beef Meatballs", "Steak with Mushroom Sauce"]},

    # Sweet Potato Mash: hidden per-meal split, displayed as final recipe ratio allocation
    {"title": "Sweet Potato Mash", "custom_type": "sweet_potato_split",
     "meals": {
         "Shepherd's Pie": 195,
         "Chicken with Sweet Potato and Beans": 169
     },
     "seasoning_per_200": {"Salt": 1, "White Pepper": 0.5}},

    {"title": "Roasted Parma Potatoes", "batch_ingredient": "Roasted Potatoes", "batch_size": 63,
     "ingredients": {"Roasted Potatoes": 190, "Oil": 1.62, "Spices Mix": 2.5},
     "meals": ["Naked Chicken Parma", "Spaghetti Bolognese"]},

    {"title": "Roasted Lemon Potatoes", "batch_ingredient": "Potatoes", "batch_size": 63,
     "ingredients": {"Potatoes": 207, "Oil": 2, "Salt": 1.2},
     "meals": ["Roasted Lemon Chicken & Potatoes"]},

    {"title": "Roasted Thai Potatoes", "batch_ingredient": "Potato", "batch_size": 0,
     "ingredients": {"Potato": 60, "Salt": 0.5},
     "meals": ["Thai Green Chicken Curry"]},

    {"title": "Lamb Onion Marinated", "batch_ingredient": "Red Onion", "batch_size": 0,
     "ingredients": {"Red Onion": 30, "Parsley": 1.5, "Paprika": 0.5},
     "meals": ["Lamb Souvlaki"]},

    {"title": "Green Beans", "batch_ingredient": "Green Beans", "batch_size": 0,
     "ingredients": {"Green Beans": 60},
     "meals": ["Chicken with Vegetables", "Chicken with Sweet Potato and Beans", "Butter Chicken"]},

    {"title": "Beef Burrito Mix", "batch_ingredient": "Salsa", "batch_size": 50,
     "ingredients": {"Salsa": 43, "Black Beans": 50, "Corn": 50, "Rice": 130},
     "meals": ["Beef Burrito Bowl"]},
]


def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    y = pdf.get_y() if start_y is None else start_y

    left_x = xpos[0] if isinstance(xpos, (list, tuple)) else xpos
    right_x = xpos[1] if isinstance(xpos, (list, tuple)) and len(xpos) > 1 else (left_x + col_w + pad)

    pdf.set_xy(left_x, y)

    if header_date is None:
        header_date = datetime.now().strftime("%d/%m/%Y")

    # IMPORTANT: widths must sum to 1.0 to prevent left/right column overlap
    COLS = [("Ingredient", 0.30), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Total", 0.25), ("Batches", 0.15)]

    def ensure_space(needed_h, x_for_page):
        nonlocal y
        if y + needed_h > bottom:
            pdf.add_page()
            y = pdf.get_y()
            pdf.set_xy(x_for_page, y)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(col_w * 2 + pad, ch, "Bulk Raw Ingredients to Cook", 0, 1, "C")
    y = pdf.get_y() + pad
    pdf.set_xy(left_x, y)

    col_x = [left_x, right_x]
    heights = [y, y]
    col = 0

    for sec in bulk_sections:
        title = sec.get("title", "")
        batch_size = sec.get("batch_size", 0) or 0

        if sec.get("custom_type") == "sweet_potato_split":
            est_rows = 3
        else:
            est_rows = len(sec.get("ingredients", {}))
            hide = set(sec.get("hide_ingredients", []))
            est_rows -= len([k for k in sec.get("ingredients", {}).keys() if k in hide])

        needed_h = ch + ch + (est_rows + 1) * ch + pad * 2

        y = heights[col]
        x = col_x[col]
        pdf.set_xy(x, y)
        ensure_space(needed_h, x)
        pdf.set_xy(x, y)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_w, ch, title, 0, 1)
        pdf.set_x(x)

        pdf.set_font("Helvetica", "B", 8)
        for h, w in COLS:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)

        pdf.set_font("Helvetica", "", 8)

        if sec.get("custom_type") == "sweet_potato_split":
            meals_map = sec.get("meals", {})

            total_potato = 0
            for meal_name, per in meals_map.items():
                total_potato += (per or 0) * (meal_totals.get(meal_name.upper(), 0) or 0)

            sweet_qty = 200.0
            salt_qty = float(sec.get("seasoning_per_200", {}).get("Salt", 0) or 0)
            pep_qty = float(sec.get("seasoning_per_200", {}).get("White Pepper", 0) or 0)
            denom = sweet_qty + salt_qty + pep_qty

            def pct(xv):
                return (xv / denom) if denom else 0.0

            def draw_ratio_row(name, qty, pct_val):
                alloc = total_potato * pct_val
                pdf.set_x(x)
                pdf.cell(col_w * COLS[0][1], ch, name[:18], 1)
                pdf.cell(col_w * COLS[1][1], ch, fmt_qty(qty), 1)
                pdf.cell(col_w * COLS[2][1], ch, f"{pct_val * 100:.1f}%", 1)
                pdf.cell(col_w * COLS[3][1], ch, fmt_int_up(alloc), 1)
                pdf.cell(col_w * COLS[4][1], ch, "", 1)
                pdf.ln(ch)

            draw_ratio_row("Sweet Potato", sweet_qty, pct(sweet_qty))
            draw_ratio_row("Salt", salt_qty, pct(salt_qty))
            draw_ratio_row("White Pepper", pep_qty, pct(pep_qty))

            heights[col] = pdf.get_y() + pad
            col = 1 - col
            continue

        ingredients = sec.get("ingredients", {})
        hide = set(sec.get("hide_ingredients", []))
        fold_into = sec.get("fold_hidden_into")

        meals_list = sec.get("meals", [])
        total_meals = sum(int(meal_totals.get(m.upper(), 0) or 0) for m in meals_list)

        batches = int(math.ceil(total_meals / batch_size)) if batch_size else 0
        batch_ingredient = sec.get("batch_ingredient", "")

        folded = dict(ingredients)
        if fold_into and hide:
            folded_qty = folded.get(fold_into, 0) or 0
            for h in hide:
                folded_qty += folded.get(h, 0) or 0
            folded[fold_into] = folded_qty

        for ingr, per in folded.items():
            if ingr in hide:
                continue

            qty_total = (per or 0) * total_meals
            adj_qty = (qty_total / batches) if (batch_size and batches) else qty_total
            batches_lbl = str(batches) if (ingr == batch_ingredient and batch_size) else ""

            pdf.set_x(x)
            pdf.cell(col_w * COLS[0][1], ch, ingr[:18], 1)
            pdf.cell(col_w * COLS[1][1], ch, fmt_qty(per), 1)
            pdf.cell(col_w * COLS[2][1], ch, str(total_meals), 1)
            pdf.cell(col_w * COLS[3][1], ch, fmt_int_up(adj_qty), 1)
            pdf.cell(col_w * COLS[4][1], ch, batches_lbl, 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad
        col = 1 - col

    pdf.set_y(max(heights))
    return pdf.get_y()
