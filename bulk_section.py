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

    # Removed Salt from Rice Order
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

    # Premixed Chicken Thigh (no oil/mix lines – total is meals x 160)
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

    # Custom Sweet Potato Mash logic (different per-meal grams by meal)
    {"title": "Sweet Potato Mash", "custom_type": "sweet_potato_split",
     "meals": {
         "Shepherd's Pie": 195,
         "Chicken with Sweet Potato and Beans": 169
     },
     # Base seasoning ratios per 200g sweet potato
     "seasoning_per_200": {"Salt": 1, "White Pepper": 0.5}},

    # Renamed
    {"title": "Roasted Parma Potatoes", "batch_ingredient": "Roasted Potatoes", "batch_size": 63,
     "ingredients": {"Roasted Potatoes": 190, "Oil": 1.62, "Spices Mix": 2.5},
     "meals": ["Naked Chicken Parma", "Spaghetti Bolognese"]},

    {"title": "Roasted Lemon Potatoes", "batch_ingredient": "Potatoes", "batch_size": 63,
     "ingredients": {"Potatoes": 207, "Oil": 2, "Salt": 1.2},
     "meals": ["Roasted Lemon Chicken & Potatoes"]},

    # Updated salt to 0.5
    {"title": "Roasted Thai Potatoes", "batch_ingredient": "Potato", "batch_size": 0,
     "ingredients": {"Potato": 60, "Salt": 0.5},
     "meals": ["Thai Green Chicken Curry"]},

    {"title": "Lamb Onion Marinated", "batch_ingredient": "Red Onion", "batch_size": 0,
     "ingredients": {"Red Onion": 30, "Parsley": 1.5, "Paprika": 0.5},
     "meals": ["Lamb Souvlaki"]},

    {"title": "Green Beans", "batch_ingredient": "Green Beans", "batch_size": 0,
     "ingredients": {"Green Beans": 60},
     "meals": ["Chicken with Vegetables", "Chicken with Sweet Potato and Beans", "Butter Chicken"]},

    # Burrito mix includes salsa, beans, corn, and rice in bulk section
    {"title": "Beef Burrito Mix", "batch_ingredient": "Salsa", "batch_size": 50,
     "ingredients": {"Salsa": 43, "Black Beans": 50, "Corn": 50, "Rice": 130},
     "meals": ["Beef Burrito Bowl"]},
]


def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    """
    Draws the bulk section tables in a 2-column layout.
    Ensures each block stays intact and respects existing header offset (start_y).

    NOTE: app.py passes xpos as a 2-item list of X positions.
    This function supports both list/tuple (preferred) and a single numeric xpos.
    """
    # xpos can be [left, right] from app.py
    if isinstance(xpos, (list, tuple)):
        col_x = [float(xpos[0]), float(xpos[1])]
        left_x = col_x[0]
    else:
        left_x = float(xpos)
        col_x = [left_x, left_x + col_w + pad]

    y = pdf.get_y() if start_y is None else start_y
    pdf.set_xy(left_x, y)

    # Use header date provided by app.py (do not alter HACCP logic in app.py)
    if header_date is None:
        header_date = datetime.now().strftime("%d/%m/%Y")

    def ensure_space(needed_h, cur_y):
        """
        Ensures there is enough vertical space. If not, add a page and return new y.
        Must respect HACCP header offset via pdf.get_y().
        """
        if cur_y + needed_h > bottom:
            pdf.add_page()
            return pdf.get_y()
        return cur_y

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(col_w * 2 + pad, ch, "Bulk Raw Ingredients to Cook", 0, 1, "C")

    y = pdf.get_y() + pad
    pdf.set_xy(left_x, y)

    # Track y for both columns
    heights = [y, y]
    col = 0

    for sec in bulk_sections:
        title = sec.get("title", "")
        batch_size = sec.get("batch_size", 0) or 0

        # estimate block height: title + header + ingredient rows
        if sec.get("custom_type") == "sweet_potato_split":
            # Displayed as 3 ratio rows (Sweet Potato / Salt / White Pepper)
            est_rows = 3
        else:
            est_rows = len(sec.get("ingredients", {}))
            hide = set(sec.get("hide_ingredients", []))
            if hide:
                est_rows -= len([k for k in sec.get("ingredients", {}).keys() if k in hide])

        needed_h = ch + ch + (est_rows + 1) * ch + pad * 2

        # Set cursor to the current column
        y = heights[col]
        y = ensure_space(needed_h, y)
        pdf.set_xy(col_x[col], y)

        # title
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_w, ch, title, 0, 1)
        pdf.set_x(col_x[col])

        # table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w * 0.55, ch, "Ingredient", 1)
        pdf.cell(col_w * 0.15, ch, "Qty/Meal", 1)
        pdf.cell(col_w * 0.15, ch, "Meals", 1)
        pdf.cell(col_w * 0.15, ch, "Total", 1)
        pdf.cell(col_w * 0.15, ch, "Batches", 1)
        pdf.ln(ch)

        pdf.set_font("Helvetica", "", 8)

        # --- Custom: Sweet Potato Mash split (meal-specific totals remain hidden) ---
        if sec.get("custom_type") == "sweet_potato_split":
            meals_map = sec.get("meals", {})
            items = list(meals_map.items())
            if len(items) != 2:
                heights[col] = pdf.get_y() + pad
                col = 1 - col
                continue

            (meal1, per1), (meal2, per2) = items
            n1 = int(meal_totals.get(meal1.upper(), 0) or 0)
            n2 = int(meal_totals.get(meal2.upper(), 0) or 0)

            # Hidden calculations (must remain correct)
            total_potato = (per1 * n1) + (per2 * n2)

            # Display as final recipe ratio allocation based on the "Qty/Meal" recipe column
            sweet_qty = 200.0
            salt_qty = float(sec.get("seasoning_per_200", {}).get("Salt", 0) or 0)
            pep_qty = float(sec.get("seasoning_per_200", {}).get("White Pepper", 0) or 0)
            denom = sweet_qty + salt_qty + pep_qty

            def pct(x):
                return (x / denom) if denom else 0.0

            def row_ratio(name, qty):
                p = pct(qty)
                alloc = total_potato * p
                pdf.cell(col_w * 0.55, ch, name, 1)
                pdf.cell(col_w * 0.15, ch, fmt_qty(qty), 1)
                pdf.cell(col_w * 0.15, ch, f"{p * 100:.1f}%", 1)
                pdf.cell(col_w * 0.15, ch, fmt_int_up(alloc), 1)
                pdf.cell(col_w * 0.15, ch, "", 1)
                pdf.ln(ch)

            row_ratio("Sweet Potato", sweet_qty)
            row_ratio("Salt", salt_qty)
            row_ratio("White Pepper", pep_qty)

            heights[col] = pdf.get_y() + pad
            col = 1 - col
            continue

        ingredients = sec.get("ingredients", {})
        hide = set(sec.get("hide_ingredients", []))
        fold_into = sec.get("fold_hidden_into")

        # compute total meals for this bulk section
        meals_list = sec.get("meals", [])
        total_meals = sum(int(meal_totals.get(m.upper(), 0) or 0) for m in meals_list)

        # batch count (for display only)
        batches = int(math.ceil(total_meals / batch_size)) if batch_size else 0
        batch_ingredient = sec.get("batch_ingredient", "")

        # fold hidden ingredients into a main ingredient for display
        folded = dict(ingredients)
        if fold_into and hide:
            folded_qty = folded.get(fold_into, 0) or 0
            for h in hide:
                folded_qty += folded.get(h, 0) or 0
            folded[fold_into] = folded_qty

        # draw rows
        for ingr, per in folded.items():
            if ingr in hide:
                continue

            qty = (per or 0) * total_meals

            # Bulk batch behaviour: display per-batch requirement when batch_size is set
            if batch_size and batches:
                adj_qty = qty / batches
            else:
                adj_qty = qty

            batches_lbl = str(batches) if (ingr == batch_ingredient and batch_size) else ""
            if ingr == batch_ingredient and batch_size == 0:
                batches_lbl = "0"

            pdf.cell(col_w * 0.55, ch, ingr[:18], 1)
            pdf.cell(col_w * 0.15, ch, fmt_qty(per), 1)
            pdf.cell(col_w * 0.15, ch, str(total_meals), 1)
            pdf.cell(col_w * 0.15, ch, fmt_int_up(adj_qty), 1)
            pdf.cell(col_w * 0.15, ch, batches_lbl, 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad
        col = 1 - col

    # set y to max of both columns so next section starts below
    pdf.set_y(max(heights))
    return pdf.get_y()
