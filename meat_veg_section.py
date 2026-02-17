import math

def draw_meat_veg_section(
    pdf, meal_totals, meal_recipes, bulk_sections, xpos, col_w, ch, pad, bottom, start_y=None
):
    """Meat Order + Veg Prep (two columns).
    Left column: Veg Prep
    Right column: Meat Order
    """

    # Always start on a new page!
    pdf.add_page()

    # Respect the PDF header height (header() runs inside add_page()).
    # If a custom start_y is provided, use it; otherwise start just below header.
    y_start = start_y if start_y is not None else (pdf.get_y() + 6)
    pdf.set_xy(xpos, y_start)

    # Page title (full-width, centered)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Meat Order and Veg Prep", ln=1, align="C")
    pdf.ln(2)

    # Column positions
    left_x = xpos
    right_x = xpos + col_w + pad
    y_tables = pdf.get_y()

    # ---------- helpers ----------
    def _table_header(x, y, title, headers, widths):
        """Draw a section header + table header row."""
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, title, ln=1, fill=True)

        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in zip(headers, widths):
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)
        return pdf.get_y()

    def _table_row(x, y, cells, widths):
        pdf.set_xy(x, y)
        for val, w in zip(cells, widths):
            pdf.cell(col_w * w, ch, str(val), 1)
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
            return math.ceil(qty * total_meals)
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

        # ✅ Round UP to whole numbers; keep totals aligned to full batches
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

            # ✅ Round UP to whole numbers; keep totals aligned to full batches
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
        # ✅ Round UP to whole numbers; keep totals aligned to full batches
        if batches > 1:
            per_batch = math.ceil(total / batches) if batches else total
            return per_batch * batches
        return total

    # Meat order calculations (RIGHT column)
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
                [
                    "Chicken With Vegetables",
                    "Chicken with Sweet Potato and Beans",
                    "Naked Chicken Parma",
                    "Chicken On Its Own",
                ],
                "Chicken",
                multiplier=153,
            ),
        ),
        (
            "NORMAL CHICKEN",
            sum_totals_recipe_ingredients(
                [
                    "Chicken Pesto Pasta",
                    "Chicken and Broccoli Pasta",
                    "Butter Chicken",
                    "Thai Green Chicken Curry",
                    "Creamy Chicken & Mushroom Gnocchi",
                ],
                "Chicken",
                multiplier=130,
            ),
        ),
        ("CHICKEN THIGH", get_total_bulk_ingredient("Chicken Thigh", "Chicken")),
    ]

    # Veg prep calculations (LEFT column)
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
                meal_recipes.get("Moroccan Chicken", {})
                .get("sub_section", {})
                .get("ingredients", {})
                .get("Red Capsicum", 0)
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
        ("5MM SLICED MUSHROOMS", 0),
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

    # ---------- draw LEFT (Veg Prep) ----------
    y_left = _table_header(
        left_x,
        y_tables,
        "Veg Prep",
        headers=["Veg Prep", "Amount (g)"],
        widths=[0.7, 0.3],
    )
    for veg, amt in veg_prep:
        y_left = _table_row(left_x, y_left, [veg, int(math.ceil(amt))], widths=[0.7, 0.3])

    # ---------- draw RIGHT (Meat Order) ----------
    y_right = _table_header(
        right_x,
        y_tables,
        "Meat Order",
        headers=["Meat Type", "Amount (g)"],
        widths=[0.6, 0.4],
    )
    for mtype, amt in meat_order:
        y_right = _table_row(right_x, y_right, [mtype, int(math.ceil(amt))], widths=[0.6, 0.4])

    pdf.ln(4)
    return max(y_left, y_right)
