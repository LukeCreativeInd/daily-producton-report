import math

def draw_meat_veg_section(
    pdf, meal_totals, meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=None
):
    """Meat & Veg page in TWO columns.

    LEFT:  Veg Prep
    RIGHT: Meat Order
    """
    pdf.add_page()

    # xpos is passed in from app as [left_x, right_x]
    left_x = xpos[0] if isinstance(xpos, (list, tuple)) else xpos
    right_x = xpos[1] if isinstance(xpos, (list, tuple)) and len(xpos) > 1 else (left_x + col_w + pad)

    # Start just below the header that is drawn in pdf.header()
    y_start = start_y if start_y is not None else (pdf.get_y() + 2)

    # Title spanning both columns
    pdf.set_xy(left_x, y_start)
    pdf.set_font("Arial", "B", 14)
    page_w = (right_x + col_w) - left_x
    pdf.cell(page_w, 10, "Meat Order and Veg Prep", ln=1, align="C")
    pdf.ln(2)

    y_tables = pdf.get_y()

    # ---------- helpers ----------
    def _header(x, y, title, cols):
        """cols: list[(label, width_frac)]"""
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

    def _row(x, y, values, fracs):
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
        section = next((b for b in bulk_sections if b["title"] == bulk_title), None)
        if section:
            total_meals = sum(meal_totals.get(m.upper(), 0) for m in section["meals"])
            qty = section["ingredients"].get(ingredient, 0)
            return qty * total_meals
        return 0

    def sum_totals_recipe_ingredients(recipe_list, ingredient, ingredient_override=None, multiplier=None):
        if multiplier is not None:
            total_meals = 0
            for rec in recipe_list:
                total_meals += meal_totals.get(rec.upper(), 0)
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
        batch = data.get("batch", 0)
        batches = math.ceil(meals / batch) if batch > 0 else 1
        total = qty * meals

        # Round UP to whole numbers; keep totals aligned to full batches
        if batches > 1:
            per_batch = math.ceil(total / batches) if batches else total
            return per_batch * batches
        return total

    def get_bulk_total(bulk_title, ingredient):
        section = next((b for b in bulk_sections if b["title"] == bulk_title), None)
        if section:
            total_meals = sum(meal_totals.get(m.upper(), 0) for m in section["meals"])
            qty = section["ingredients"].get(ingredient, 0)
            batch_size = section.get("batch_size", 0)
            batches = math.ceil(total_meals / batch_size) if batch_size > 0 else 1
            total = qty * total_meals

            # Round UP to whole numbers; keep totals aligned to full batches
            if batches > 1:
                per_batch = math.ceil(total / batches) if batches else total
                return per_batch * batches
            return total
        return 0

    def get_total_from_chicken_mixing():
        meals = meal_totals.get("CREAMY CHICKEN & MUSHROOM GNOCCHI".upper(), 0)
        qty = 25
        divisor = 36
        raw_b = math.ceil(meals / divisor) if divisor > 0 else 0
        batches = raw_b + (raw_b % 2) if raw_b > 0 else 0
        total = qty * meals

        # Round UP to whole numbers; keep totals aligned to full batches
        if batches > 1:
            per_batch = math.ceil(total / batches) if batches else total
            return per_batch * batches
        return total

    # ---------- Meat Order (RIGHT) ----------
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
        ("TOPSIDE STEAK", get_total_bulk_ingredient("Steak", "Steak") + get_total_recipe_ingredient("Steak On Its Own", "Topside Steak")),
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
        ("CHICKEN THIGH", get_total_bulk_ingredient("Chicken Thigh", "Chicken")),
    ]

    # ---------- Veg Prep (LEFT) ----------
    veg_prep = [
        ("10MM DICED CARROT", get_batch_total("Lebanese Beef Stew", "Carrot")),
        ("10MM DICED POTATO (LEBO)", get_batch_total("Lebanese Beef Stew", "Potato")),
        ("10MM DICED ZUCCHINI", meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Zucchini", 0) * meal_totals.get("MOROCCAN CHICKEN".upper(), 0)),
        ("5MM DICED CABBAGE", get_batch_total("Beef Chow Mein", "Cabbage")),
        (
            "5MM DICED CAPSICUM",
            get_batch_total("Shepherd's Pie", "Capsicum")
            + get_batch_total("Beef Burrito Bowl", "Capsicum")
            + (meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Red Capsicum", 0) * meal_totals.get("MOROCCAN CHICKEN".upper(), 0)),
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
            + (meal_recipes.get("Moroccan Chicken", {}).get("sub_section", {}).get("ingredients", {}).get("Onion", 0) * meal_totals.get("MOROCCAN CHICKEN".upper(), 0))
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

    # Whole-number output (rounded UP)
    def _int_up(v):
        try:
            return int(math.ceil(float(v)))
        except Exception:
            return 0

    # ---------- draw LEFT table ----------
    y_left = _header(left_x, y_tables, "Veg Prep", [("Veg Prep", 0.7), ("Amount (g)", 0.3)])
    for name, amt in veg_prep:
        y_left = _row(left_x, y_left, [name, _int_up(amt)], [0.7, 0.3])

    # ---------- draw RIGHT table ----------
    y_right = _header(right_x, y_tables, "Meat Order", [("Meat Type", 0.6), ("Amount (g)", 0.4)])
    for name, amt in meat_order:
        y_right = _row(right_x, y_right, [name, _int_up(amt)], [0.6, 0.4])

    pdf.ln(4)
    return max(y_left, y_right)
