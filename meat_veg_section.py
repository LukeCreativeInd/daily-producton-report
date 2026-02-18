import math
from utils import fmt_int_up

def draw_meat_veg_section(
    pdf, meal_totals, meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=None
):
    """Meat Order + Veg Prep

    - Always starts on its own NEW page
    - Two columns: Veg Prep (left) + Meat Order (right)
    - Respects HACCP header spacing (do NOT set y=10)
    - All totals are rounded UP to whole numbers (no decimals)
    """

    # Always start on a new page (header() will place cursor below HACCP header)
    pdf.add_page()

    left_x = xpos[0] if isinstance(xpos, (list, tuple)) else xpos
    right_x = xpos[1] if isinstance(xpos, (list, tuple)) and len(xpos) > 1 else (left_x + col_w + 10)

    # Page title (full width)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Meat Order and Veg Prep", ln=1, align="C")
    pdf.ln(2)

    y0 = pdf.get_y()

    # ---------- helpers ----------
    def draw_table_header(x, y, title, cols):
        # cols = list of (label, fraction_of_col_w)
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, title, ln=1, fill=True)

        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for label, frac in cols:
            pdf.cell(col_w * frac, ch, label, 1)
        pdf.ln(ch)

        pdf.set_font("Arial", "", 8)
        return pdf.get_y()

    def draw_row(x, y, values, fracs):
        pdf.set_xy(x, y)
        for v, f in zip(values, fracs):
            pdf.cell(col_w * f, ch, str(v), 1)
        return y + ch

    # ---------- calculations ----------
    def get_total_recipe_ingredient(recipe, ingredient):
        data = meal_recipes.get(recipe, {})
        meals = meal_totals.get(recipe.upper(), 0)
        qty = data.get("ingredients", {}).get(ingredient, 0)
        return qty * meals

    def get_total_bulk_ingredient(bulk_title, ingredient):
        section = next((b for b in bulk_sections if b.get("title") == bulk_title), None)
        if not section:
            return 0
        total_meals = sum(meal_totals.get(m.upper(), 0) for m in section.get("meals", []))
        qty = section.get("ingredients", {}).get(ingredient, 0)
        return qty * total_meals

    def sum_totals_recipe_ingredients(recipe_list, ingredient, ingredient_override=None, multiplier=None):
        if multiplier is not None:
            total_meals = sum(meal_totals.get(rec.upper(), 0) for rec in recipe_list)
            return total_meals * multiplier

        total = 0
        for rec in recipe_list:
            data = meal_recipes.get(rec, {})
            meals = meal_totals.get(rec.upper(), 0)
            ing = ingredient_override if ingredient_override else ingredient
            qty = data.get("ingredients", {}).get(ing, 0)
            total += qty * meals
        return total

    def get_batch_total(recipe, ingredient):
        data = meal_recipes.get(recipe, {})
        meals = meal_totals.get(recipe.upper(), 0)
        qty = data.get("ingredients", {}).get(ingredient, 0)
        batch_size = data.get("batch", 0)

        batches = math.ceil(meals / batch_size) if batch_size and batch_size > 0 else 1
        total = qty * meals

        # Keep totals aligned to full batches, and round UP to whole numbers.
        if batches > 1:
            per_batch = math.ceil(total / batches) if batches else total
            return per_batch * batches
        return total

    def get_bulk_total(bulk_title, ingredient):
        section = next((b for b in bulk_sections if b.get("title") == bulk_title), None)
        if not section:
            return 0

        total_meals = sum(meal_totals.get(m.upper(), 0) for m in section.get("meals", []))
        qty = section.get("ingredients", {}).get(ingredient, 0)
        batch_size = section.get("batch_size", 0)

        batches = math.ceil(total_meals / batch_size) if batch_size and batch_size > 0 else 1
        total = qty * total_meals

        if batches > 1:
            per_batch = math.ceil(total / batches) if batches else total
            return per_batch * batches
        return total

    def get_total_from_chicken_mixing():
        # Spinach for Gnocchi (force even batch count like production)
        meals = meal_totals.get("CREAMY CHICKEN & MUSHROOM GNOCCHI".upper(), 0)
        qty = 25
        divisor = 36

        raw_batches = math.ceil(meals / divisor) if divisor and divisor > 0 else 0
        batches = raw_batches + (raw_batches % 2) if raw_batches > 0 else 0

        total = qty * meals
        if batches > 1:
            per_batch = math.ceil(total / batches)
            return per_batch * batches
        return total

    # ---------- Meat Order (RIGHT column) ----------
    meat_order = [
        ("CHUCK ROLL (LEBO)", get_total_recipe_ingredient("Lebanese Beef Stew", "Chuck Diced")),
        ("BEEF TOPSIDE (MONG)", get_total_recipe_ingredient("Mongolian Beef", "Chuck")),
        (
            "MINCE",
            sum_totals_recipe_ingredients(
                ["Spaghetti Bolognese", "Shepherd's Pie", "Beef Chow Mein", "Beef Burrito Bowl"],
                "Beef Mince",
            )
            + sum_totals_recipe_ingredients(["Beef Meatballs"], "Mince"),
        ),
        (
            "TOPSIDE STEAK",
            get_total_bulk_ingredient("Steak", "Steak")
            + get_total_recipe_ingredient("Steak On Its Own", "Topside Steak"),
        ),
        ("LAMB SHOULDER", get_total_bulk_ingredient("Lamb Marinate", "Lamb Shoulder")),
        ("MORROCAN CHICKEN", get_total_bulk_ingredient("Moroccan Chicken", "Chicken")),
        (
            "ITALIAN CHICKEN",
            sum_totals_recipe_ingredients(
                ["Chicken With Vegetables", "Chicken with Sweet Potato and Beans", "Naked Chicken Parma", "Chicken On Its Own"],
                "Chicken",
                multiplier=153,
            ),
        ),
        (
            "NORMAL CHICKEN",
            sum_totals_recipe_ingredients(
                ["Chicken Pesto Pasta", "Chicken and Broccoli Pasta", "Butter Chicken", "Thai Green Chicken Curry", "Creamy Chicken & Mushroom Gnocchi"],
                "Chicken",
                multiplier=130,
            ),
        ),
        ("PREMIXED CHICKEN", get_total_bulk_ingredient("Premixed Chicken Thigh", "Premixed Chicken Thigh")),
    ]

    # ---------- Veg Prep (LEFT column) ----------
    veg_prep = [
        ("10MM DICED CARROT", get_batch_total("Lebanese Beef Stew", "Carrot")),
        ("10MM DICED POTATO (LEBO)", get_batch_total("Lebanese Beef Stew", "Potato")),
        (
            "10MM DICED ZUCCHINI",
            meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Zucchini", 0)
            * meal_totals.get("MOROCCAN CHICKEN".upper(), 0),
        ),
        ("5MM DICED CABBAGE", get_batch_total("Beef Chow Mein", "Cabbage")),
        (
            "5MM DICED CAPSICUM",
            get_batch_total("Shepherd's Pie", "Capsicum")
            + get_batch_total("Beef Burrito Bowl", "Capsicum")
            + (
                meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Red Capsicum", 0)
                * meal_totals.get("MOROCCAN CHICKEN".upper(), 0)
            ),
        ),
        ("5MM DICED CARROTS", get_batch_total("Shepherd's Pie", "Carrots") + get_batch_total("Beef Chow Mein", "Carrot")),
        ("5MM DICED CELERY", get_batch_total("Beef Chow Mein", "Celery")),
        ("5MM DICED MUSHROOMS", get_batch_total("Shepherd's Pie", "Mushroom")),
        (
            "5MM DICED ONION",
            get_batch_total("Spaghetti Bolognese", "Onion")
            + get_batch_total("Beef Chow Mein", "Onion")
            + get_batch_total("Shepherd's Pie", "Onion")
            + get_batch_total("Beef Burrito Bowl", "Onion")
            + get_batch_total("Beef Meatballs", "Onion")
            + get_batch_total("Lebanese Beef Stew", "Onion")
            + (
                meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Onion", 0)
                * meal_totals.get("MOROCCAN CHICKEN".upper(), 0)
            )
            + get_batch_total("Bean Nachos with Rice", "Onion"),
        ),
        ("5MM MONGOLIAN CAPSICUM", get_batch_total("Mongolian Beef", "Capsicum") + get_batch_total("Chicken Fajita Bowl", "Capsicum")),
        ("5MM MONGOLIAN ONION", get_batch_total("Mongolian Beef", "Onion") + get_batch_total("Chicken Fajita Bowl", "Red Onion")),
        ("BROCCOLI", get_batch_total("Chicken and Broccoli Pasta", "Broccoli") + get_batch_total("Chicken With Vegetables", "Broccoli")),
        ("CRATED CARROTS", get_batch_total("Spaghetti Bolognese", "Carrot") + get_batch_total("Bean Nachos with Rice", "Carrot")),
        ("CRATED ZUCCHINI", get_batch_total("Spaghetti Bolognese", "Zucchini")),
        ("LEMON POTATO", get_bulk_total("Roasted Lemon Potatoes", "Potatoes")),
        ("ROASTED POTATO", get_bulk_total("Roasted Potatoes", "Roasted Potatoes")),
        ("THAI POTATOS", get_bulk_total("Roasted Thai Potatoes", "Potato")),
        ("POTATO MASH", get_bulk_total("Potato Mash", "Potato")),
        ("SWEET POTATO MASH", get_bulk_total("Sweet Potato Mash", "Sweet Potato")),
        ("SPINACH", get_total_from_chicken_mixing()),
        ("RED ONION", get_bulk_total("Lamb Onion Marinated", "Red Onion")),
        ("PARSLEY", get_bulk_total("Lamb Onion Marinated", "Parsley")),
    ]

    # Render Veg (left)
    y_left = draw_table_header(left_x, y0, "Veg Prep", [("Veg Prep", 0.7), ("Amount (g)", 0.3)])
    for name, amt in veg_prep:
        y_left = draw_row(left_x, y_left, [name, fmt_int_up(amt)], [0.7, 0.3])

    # Render Meat (right)
    y_right = draw_table_header(right_x, y0, "Meat Order", [("Meat Type", 0.6), ("Amount (g)", 0.4)])
    for name, amt in meat_order:
        y_right = draw_row(right_x, y_right, [name, fmt_int_up(amt)], [0.6, 0.4])

    return max(y_left, y_right) + pad
