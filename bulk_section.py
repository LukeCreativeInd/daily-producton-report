from quantities import normalize_meal_totals
import math
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
from utils import fmt_int_up, fmt_qty

# --- BULK SECTIONS (match names to uploaded CSV exactly) ---
bulk_sections = [
    {"title": "Spaghetti Order", "custom_type": "pasta_trays",
     "pasta_name": "Spaghetti", "pasta_per_meal": 64, "oil_per_meal": 0.7,
     "pasta_per_tray": 2000, "water_per_tray": 4500,
     "meals": ["Spaghetti Bolognese"]},

    {"title": "Penne Order", "custom_type": "pasta_trays",
     "pasta_name": "Penne", "pasta_per_meal": 65.26, "oil_per_meal": 0.79,
     "pasta_per_tray": 2000, "water_per_tray": 5000,
     "meals": ["Chicken Pesto Pasta", "Chicken and Broccoli Pasta"]},

    {"title": "Fettuccine Order", "custom_type": "pasta_trays",
     "pasta_name": "Fettuccine", "pasta_per_meal": 85.32, "oil_per_meal": 0.85,
     "pasta_per_tray": 2000, "water_per_tray": 4500,
     "show_oil": True, "show_raw_pasta": True,
     "meals": ["Creamy Fettuccine"]},

    # Rice is now steamed in oven trays: 2kg rice + 3kg water per tray
    {"title": "Rice Order", "custom_type": "rice_trays",
     "rice_per_meal": 55.39,
     "rice_per_tray": 2000,
     "water_per_tray": 3000,
     "meals": [
         "Beef Chow Mein",
         "Beef Burrito Bowl",
         "Lebanese Beef Stew",
         "Mongolian Beef",
         "Butter Chicken",
         "Thai Green Chicken Curry",
     ]},

    {"title": "Moroccan Chicken", "batch_ingredient": "Chicken", "batch_size": 0,
     "ingredients": {"Chicken": 180, "Oil": 2, "Lemon Juice": 6, "Moroccan Chicken Mix": 4},
     "meals": ["Moroccan Chicken"]},

    # Supplier provides premixed chicken with oil + seasoning already included.
    # We hide Oil + Roast Chicken Mix rows, but add their weight into Premixed Chicken totals.
    {"title": "Premixed Chicken Thigh", "batch_ingredient": "Premixed Chicken Thigh", "batch_size": 0,
 "ingredients": {"Premixed Chicken Thigh": 160},
 "meals": ["Roasted Lemon Chicken & Potatoes"]},

    # Updated Steak quantities
    {"title": "Steak", "batch_ingredient": "Steak", "batch_size": 0,
     "ingredients": {"Steak": 100, "Oil": 1.6, "Baking Soda": 1},
     "meals": ["Steak with Mushroom Sauce"]},

    {"title": "Lamb Marinate", "batch_ingredient": "Lamb Shoulder", "batch_size": 0,
 "ingredients": {"Lamb Shoulder": 148.7, "Oil": 1.8, "Oregano": 1.1, "Baking Soda": 2.4},
 "meals": ["Lamb Souvlaki"]},

    # Custom Sweet Potato Mash logic (different per-meal grams by meal)
    {"title": "Sweet Potato Mash", "custom_type": "sweet_potato_split",
     "meals": {
         "Shepherd's Pie": 197.94,
         "Chicken with Sweet Potato and Beans": 171.55
     },
     # Base seasoning ratios per 200g sweet potato
     "seasoning_per_200": {"Salt": 1, "White Pepper": 0.2}},

    # Renamed
    {"title": "Roasted Parma Potatoes", "custom_type": "roasted_potato_split",
     "max_batch_grams": 7500,
     "ingredients": {"Oil": 1.9, "Spices Mix": 1.9},
     "meals": {"Naked Chicken Parma": 186, "Lamb Souvlaki": 173.6,
               "Smashed Burger": 198.4, "Sunday Roast Lamb": 124}},

    {"title": "Roasted Lemon Potatoes", "batch_ingredient": "Potatoes", "batch_size": 63,
     "ingredients": {"Potatoes": 207, "Oil": 2, "Salt": 1.2},
     "meals": ["Roasted Lemon Chicken & Potatoes"]},

    {"title": "Sunday Roast Vegetables", "batch_size": 0,
     "ingredients": {"Roast Diced Pumpkin": 82, "Roast Carrot Discs": 54},
     "meals": ["Sunday Roast Lamb"]},

    {"title": "Creamy Fettuccine", "batch_size": 0,
     "ingredients": {"Steamed Broccoli": 36},
     "meals": ["Creamy Fettuccine"]},

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
         "Chicken with Sweet Potato and Beans",
         "Steak with Mushroom Sauce"
     ]},

    # Copied from To Pack In Fridge (kept there as well)
    {"title": "Beef Burrito Mix", "batch_ingredient": "Salsa", "batch_size": 60,
     "ingredients": {"Salsa": 43, "Black Beans": 50, "Corn": 50, "Rice": 130},
     "meals": ["Beef Burrito Bowl"]},
]

def roasted_potato_requirements(meal_totals, section=None):
    """Shared calculation for cooking batches and the vegetable order.

    The 7.5kg cap includes oil and seasoning, including the displayed whole-gram
    rounding of every ingredient. Decimal arithmetic avoids phantom extra grams.
    """
    if section is None:
        section = next(s for s in bulk_sections if s.get("custom_type") == "roasted_potato_split")
    counts = {m: meal_totals.get(m.upper(), 0) for m in section["meals"]}
    meals = sum(counts.values())
    totals = {"Roasted Potatoes": sum((Decimal(str(per)) * counts[m]
                                       for m, per in section["meals"].items()), Decimal(0))}
    totals.update({name: Decimal(str(per)) * meals for name, per in section["ingredients"].items()})
    ceil = lambda value: int(value.to_integral_value(rounding=ROUND_CEILING))
    batches = ceil(sum(totals.values()) / section["max_batch_grams"]) if meals else 0
    per_batch = {name: ceil(value / batches) if batches else 0 for name, value in totals.items()}
    while sum(per_batch.values()) > section["max_batch_grams"]:
        batches += 1
        per_batch = {name: ceil(value / batches) for name, value in totals.items()}
    return meals, totals, batches, per_batch


def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    meal_totals = normalize_meal_totals(meal_totals)
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
        if sec.get("custom_type") == "roasted_potato_split":
            heights, col = ensure_space(heights, 5 * ch + pad, title1)
            x = xpos[col]
            pdf.set_xy(x, heights[col])
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(col_w, ch, sec["title"], ln=1, fill=True)
            table_headers(x)
            meals, totals, batches, per_batch = roasted_potato_requirements(meal_totals, sec)
            for ingredient in totals:
                qty = "" if ingredient == "Roasted Potatoes" else fmt_qty(sec["ingredients"][ingredient])
                pdf.set_x(x)
                for value, width in [(ingredient, .4), (qty, .15), (str(meals), .15),
                                     (str(per_batch[ingredient]), .15),
                                     (str(batches) if ingredient == "Roasted Potatoes" else "", .15)]:
                    pdf.cell(col_w * width, ch, value, 1)
                pdf.ln(ch)
            heights[col] = pdf.get_y() + pad
            continue
        # Penne and spaghetti are cooked in oven trays using their own water ratios.
        if sec.get("custom_type") == "pasta_trays":
            # Fettuccine includes pasta, oil and water; existing pasta tables
            # also keep their raw-pasta row.
            lines = 2 + int(sec.get("show_oil", True)) + int(sec.get("show_raw_pasta", True))
            block_h = (2 + lines) * ch + pad
            heights, col = ensure_space(heights, block_h, title1)
            x, y = xpos[col], heights[col]
            pdf.set_xy(x, y)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(col_w, ch, sec["title"], ln=1, fill=True)

            table_headers(x)

            total_meals = sum(int(meal_totals.get(m.upper(), 0) or 0) for m in sec.get("meals", []))

            pasta_name = sec["pasta_name"]
            pasta_per_meal = float(sec.get("pasta_per_meal", 0) or 0)
            oil_per_meal = float(sec.get("oil_per_meal", 0) or 0)
            pasta_per_tray = float(sec.get("pasta_per_tray", 2000) or 2000)
            water_per_tray = float(sec.get("water_per_tray", 0) or 0)

            total_pasta = pasta_per_meal * total_meals
            total_oil = oil_per_meal * total_meals
            trays = math.ceil(total_pasta / pasta_per_tray) if total_pasta > 0 else 0
            pasta_per_actual_tray = total_pasta / trays if trays else 0
            oil_per_actual_tray = total_oil / trays if trays else 0
            total_water = trays * water_per_tray if trays else 0

            def pasta_row(label, qty_per, meals_display, total_display, batch_display=""):
                pdf.set_x(x)
                pdf.cell(col_w * 0.4, ch, str(label)[:20], 1)
                pdf.cell(col_w * 0.15, ch, fmt_qty(qty_per), 1)
                pdf.cell(col_w * 0.15, ch, str(meals_display), 1)
                pdf.cell(col_w * 0.15, ch, fmt_int_up(total_display), 1)
                pdf.cell(col_w * 0.15, ch, str(batch_display), 1)
                pdf.ln(ch)

            pasta_row(pasta_name, pasta_per_meal, total_meals, pasta_per_actual_tray, trays)
            if sec.get("show_oil", True):
                pasta_row("Oil", oil_per_meal, total_meals, oil_per_actual_tray, "")
            pasta_row("Water", water_per_tray, trays, total_water, "")
            if sec.get("show_raw_pasta", True):
                pasta_row(f"Raw {pasta_name}", pasta_per_tray, trays, total_pasta, "")

            heights[col] = pdf.get_y() + pad
            continue

        # Custom Rice Tray rendering
        if sec.get("custom_type") == "rice_trays":
            # rows: title + headers + 3 lines (Rice, Water, Tray Setup)
            block_h = (2 + 3) * ch + pad
            heights, col = ensure_space(heights, block_h, title1)
            x, y = xpos[col], heights[col]
            pdf.set_xy(x, y)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(col_w, ch, sec["title"], ln=1, fill=True)

            table_headers(x)

            total_meals = sum(int(meal_totals.get(m.upper(), 0) or 0) for m in sec.get("meals", []))

            rice_per_meal = float(sec.get("rice_per_meal", 0) or 0)
            rice_per_tray = float(sec.get("rice_per_tray", 2000) or 2000)
            water_per_tray = float(sec.get("water_per_tray", 3000) or 3000)

            total_rice = rice_per_meal * total_meals
            trays = math.ceil(total_rice / rice_per_tray) if total_rice > 0 else 0
            rice_per_actual_tray = total_rice / trays if trays else 0
            total_water = trays * water_per_tray if trays else 0

            def rice_row(label, qty_per, meals_display, total_display, batch_display=""):
                pdf.set_x(x)
                pdf.cell(col_w * 0.4, ch, str(label)[:20], 1)
                pdf.cell(col_w * 0.15, ch, fmt_qty(qty_per), 1)
                pdf.cell(col_w * 0.15, ch, str(meals_display), 1)
                pdf.cell(col_w * 0.15, ch, fmt_int_up(total_display), 1)
                pdf.cell(col_w * 0.15, ch, str(batch_display), 1)
                pdf.ln(ch)

            rice_row("Rice", rice_per_meal, total_meals, rice_per_actual_tray, trays)
            rice_row("Water", water_per_tray, trays, total_water, "")
            rice_row("Tray Setup", rice_per_tray, trays, total_rice, "")

            heights[col] = pdf.get_y() + pad
            continue

        # Custom Sweet Potato Mash rendering
        if sec.get("custom_type") == "sweet_potato_split":
            # rows: title + headers + 3 lines (Sweet Potato, Salt, White Pepper)
            block_h = (2 + 3) * ch + pad
            heights, col = ensure_space(heights, block_h, title1)
            x, y = xpos[col], heights[col]
            pdf.set_xy(x, y)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(col_w, ch, sec["title"], ln=1, fill=True)

            table_headers(x)

            # Hidden correct total potato grams from per-meal values per meal
            total_potato = 0
            for meal_name, per_meal in sec["meals"].items():
                n = int(meal_totals.get(meal_name.upper(), 0) or 0)
                total_potato += (per_meal or 0) * n

            # Allocate total_potato by recipe ratios (200 / 1 / 0.5)
            sweet_qty = 200.0
            salt_qty = float(sec.get("seasoning_per_200", {}).get("Salt", 0) or 0)
            pep_qty = float(sec.get("seasoning_per_200", {}).get("White Pepper", 0) or 0)
            denom = sweet_qty + salt_qty + pep_qty

            def pct(v):
                return (v / denom) if denom else 0.0

            def ratio_row(label, qty, pct_val, total_alloc):
                pdf.set_x(x)
                pdf.cell(col_w * 0.4, ch, str(label)[:20], 1)
                pdf.cell(col_w * 0.15, ch, fmt_qty(qty), 1)
                pdf.cell(col_w * 0.15, ch, f"{pct_val * 100:.1f}%", 1)
                pdf.cell(col_w * 0.15, ch, fmt_int_up(total_alloc), 1)
                pdf.cell(col_w * 0.15, ch, "", 1)
                pdf.ln(ch)

            ratio_row("Sweet Potato", sweet_qty, pct(sweet_qty), total_potato * pct(sweet_qty))
            ratio_row("Salt", salt_qty, pct(salt_qty), total_potato * pct(salt_qty))
            ratio_row("White Pepper", pep_qty, pct(pep_qty), total_potato * pct(pep_qty))

            heights[col] = pdf.get_y() + pad
            continue
        ingredients = sec.get("ingredients", {})
        hide = set(sec.get("hide_ingredients", []))
        fold_into = sec.get("fold_hidden_into")

        # Determine number of visible ingredient lines
        visible_ings = []
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
