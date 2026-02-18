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
         "Bean Nachos with Rice",
         "Chicken Fajita Bowl"
     ]},

    {"title": "Moroccan Chicken", "batch_ingredient": "Chicken", "batch_size": 0,
     "ingredients": {"Chicken": 180, "Oil": 2, "Lemon Juice": 6, "Moroccan Chicken Mix": 4},
     "meals": ["Moroccan Chicken"]},

    # Supplier provides premixed chicken with oil + seasoning already included.
    # We hide Oil + Roast Chicken Mix rows, but add their weight into Premixed Chicken totals.
    {"title": "Premixed Chicken Thigh", "batch_ingredient": "Premixed Chicken Thigh", "batch_size": 0,
     "ingredients": {"Premixed Chicken Thigh": 160, "Oil": 4, "Roast Chicken Mix": 4},
     "hide_ingredients": ["Oil", "Roast Chicken Mix"],
     "fold_hidden_into": "Premixed Chicken Thigh",
     "meals": ["Roasted Lemon Chicken & Potatoes", "Chicken Fajita Bowl"]},

    # Updated Steak quantities
    {"title": "Steak", "batch_ingredient": "Steak", "batch_size": 0,
     "ingredients": {"Steak": 116.3, "Oil": 1.9, "Baking Soda": 3.8},
     "meals": ["Steak with Mushroom Sauce", "Steak On Its Own"]},

    # Removed Salt from Lamb Marinate
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
          "custom_meal_qty": {"Shepherd's Pie": 195, "Chicken with Sweet Potato and Beans": 169}},
# Base seasoning ratios per 200g sweet potato
     "seasoning_per_200": {"Salt": 1, "White Pepper": 0.5}},

    # Renamed
    {"title": "Roasted Parma Potatoes", "batch_ingredient": "Roasted Potatoes", "batch_size": 63,
     "ingredients": {"Roasted Potatoes": 190, "Oil": 1.62, "Spices Mix": 2.5},
     "meals": ["Naked Chicken Parma", "Lamb Souvlaki"]},

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
     "meals": [
         "Chicken with Vegetables",
         "Chicken with Sweet Potato and Beans",
         "Steak with Mushroom Sauce"
     ]},

    # Copied from To Pack In Fridge (kept there as well)
    {"title": "Beef Burrito Mix", "batch_ingredient": "Salsa", "batch_size": 60,
     "ingredients": {"Salsa": 43, "Black Beans": 50, "Corn": 50, "Rice": 130},
     "meals": ["Beef Burrito Bowl"]},
]

def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    title1 = "Bulk Raw Ingredients to Cook"
    if start_y is None:
        pdf.add_page()
        start_y = pdf.get_y()
    pdf.set_y(start_y)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title1, ln=1, align='C')
    pdf.ln(5)

    heights = [pdf.get_y(), pdf.get_y()]

    def choose_col(heights):
        return 0 if heights[0] <= heights[1] else 1

    def ensure_space(heights, block_h, title=None):
        col = choose_col(heights)
        # try chosen col, then other col, else new page
        if heights[col] + block_h > bottom:
            col2 = 1 - col
            if heights[col2] + block_h <= bottom:
                col = col2
            else:
                pdf.add_page()
                if title:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, title, ln=1, align='C')
                    pdf.ln(5)
                heights = [pdf.get_y(), pdf.get_y()]
                col = 0
        return heights, col

    def table_headers(x):
        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in [("Ingredient", 0.4), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Total", 0.15), ("Batches", 0.15)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)

    for sec in bulk_sections:
        # Custom Sweet Potato Mash rendering
        if sec.get("custom_type") == "sweet_potato_split":
            # rows: title + headers + 5 lines (2 subtotals + total + salt + pepper)
            block_h = (2 + 5) * ch + pad
            heights, col = ensure_space(heights, block_h, title1)
            x, y = xpos[col], heights[col]
            pdf.set_xy(x, y)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(col_w, ch, sec["title"], ln=1, fill=True)

            table_headers(x)

            # Meal split totals
            m1, m2 = list(sec["meals"].items())
            meal1, per1 = m1
            meal2, per2 = m2

            n1 = int(meal_totals.get(meal1.upper(), 0) or 0)
            n2 = int(meal_totals.get(meal2.upper(), 0) or 0)

            t1 = per1 * n1
            t2 = per2 * n2
            total_potato = t1 + t2

            # Display lines
            def row(label, per, meals, total, batches_lbl=""):
                pdf.set_x(x)
                pdf.cell(col_w * 0.4, ch, str(label)[:20], 1)
                pdf.cell(col_w * 0.15, ch, "" if per is None else fmt_qty(per), 1)
                pdf.cell(col_w * 0.15, ch, "" if meals is None else (fmt_qty(meals) if isinstance(meals, float) else str(int(meals))), 1)
                pdf.cell(col_w * 0.15, ch, fmt_int_up(total) if total is not None else "", 1)
                pdf.cell(col_w * 0.15, ch, batches_lbl, 1)
                pdf.ln(ch)

            row(f"Sweet Potato ({meal1})", per1, n1, t1)
            row(f"Sweet Potato ({meal2})", per2, n2, t2)
            row("Sweet Potato TOTAL", None, None, total_potato)

            factor = (total_potato / 200.0) if total_potato else 0.0
            salt_per = sec["seasoning_per_200"].get("Salt", 0)
            pep_per = sec["seasoning_per_200"].get("White Pepper", 0)

            row("Salt", salt_per, factor, salt_per * factor)
            row("White Pepper", pep_per, factor, pep_per * factor)

            heights[col] = pdf.get_y() + pad
            continue

        ingredients = sec.get("ingredients", {})
        hide = set(sec.get("hide_ingredients", []))
        fold_into = sec.get("fold_hidden_into")

        # Determine number of visible ingredient lines
        visible_ings = []

# --- Custom display: Sweet Potato Mash ---
# We keep Qty/Meal ratios exactly as defined in this file (200 / 1 / 0.5),
# but compute TOTAL POTATO from hidden per-meal quantities in custom_meal_qty,
# then allocate that total by ratio and display percentages in the Meals column.
if sec.get("title") == "Sweet Potato Mash" and sec.get("custom_meal_qty"):
    total_potato = 0
    for meal_name, per_meal in sec["custom_meal_qty"].items():
        total_potato += (per_meal or 0) * (meal_totals.get(meal_name.upper(), 0) or 0)

    denom = sum(ingredients.values()) if ingredients else 0

    for ingr, per in ingredients.items():
        pct = (per / denom) if denom else 0
        alloc = total_potato * pct

        pdf.set_x(x)
        pdf.cell(col_w * 0.4, ch, str(ingr)[:20], 1)
        pdf.cell(col_w * 0.15, ch, fmt_qty(per), 1)  # ratio value (exact)
        pdf.cell(col_w * 0.15, ch, f"{pct * 100:.1f}%", 1)
        pdf.cell(col_w * 0.15, ch, fmt_int_up(alloc), 1)  # totals rounded up only
        pdf.cell(col_w * 0.15, ch, "", 1)  # blank batches cell to preserve table layout
        pdf.ln(ch)

    heights[col] = pdf.get_y() + pad
    continue
        for ingr, per in ingredients.items():
            if ingr in hide:
                continue
            visible_ings.append((ingr, per))

        # fold hidden into a single ingredient (e.g. Premixed Chicken)
        if fold_into and fold_into in ingredients:
            hidden_sum = sum(v for k, v in ingredients.items() if k in hide)
            # override displayed per-unit for the folded ingredient to include hidden weights
            visible_ings = [
                (fold_into, ingredients[fold_into] + hidden_sum)
            ] + [(k, v) for k, v in visible_ings if k != fold_into]

        block_h = (len(visible_ings) + 2) * ch + pad
        heights, col = ensure_space(heights, block_h, title1)
        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, sec['title'], ln=1, fill=True)

        table_headers(x)

        total_meals = sum(int(meal_totals.get(m.upper(), 0) or 0) for m in sec.get('meals', []))
        batches = math.ceil(total_meals / sec.get('batch_size', 0)) if sec.get('batch_size', 0) > 0 else 0

        for ingr, per in visible_ings:
            qty = per * total_meals
            adj = (qty / batches) if batches else qty
            lbl = str(batches) if ingr == sec.get('batch_ingredient') else ""

            pdf.set_x(x)
            pdf.cell(col_w * 0.4, ch, str(ingr)[:20], 1)
            pdf.cell(col_w * 0.15, ch, fmt_qty(per), 1)  # per-unit exact
            pdf.cell(col_w * 0.15, ch, str(total_meals), 1)
            pdf.cell(col_w * 0.15, ch, fmt_int_up(adj), 1)  # totals rounded
            pdf.cell(col_w * 0.15, ch, lbl, 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    return max(heights)
