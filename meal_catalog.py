"""Canonical upload names; weights affect printed labels only."""

ACTIVE_BRANDS = ("Clean Eats", "Made Active")

SUMMARY_MEAL_ORDER = ['Spaghetti Bolognese', 'Beef Chow Mein', "Shepherd's Pie", 'Beef Burrito Bowl', 'Beef Meatballs', 'Lebanese Beef Stew', 'Mongolian Beef', 'Chicken with Sweet Potato and Beans', 'Naked Chicken Parma', 'Chicken Pesto Pasta', 'Chicken and Broccoli Pasta', 'Butter Chicken', 'Thai Green Chicken Curry', 'Moroccan Chicken', 'Steak with Mushroom Sauce', 'Creamy Chicken & Mushroom Gnocchi', 'Roasted Lemon Chicken & Potatoes', 'Beef Lasagna', 'Lamb Souvlaki', 'Baked Family Lasagna', 'Sunday Roast Lamb', 'Smashed Burger', 'Creamy Fettuccine']

# Finished-meal net weights from GS1_Products, 13 August 2026 barcode master.
# Exact workbook rows and name mappings are documented in WEIGHT_SOURCES.md.
MEAL_WEIGHTS_G = {'Spaghetti Bolognese': 380, 'Beef Chow Mein': 360, "Shepherd's Pie": 360, 'Beef Burrito Bowl': 400, 'Beef Meatballs': 370, 'Lebanese Beef Stew': 350, 'Mongolian Beef': 360, 'Chicken with Sweet Potato and Beans': 320, 'Naked Chicken Parma': 350, 'Chicken Pesto Pasta': 330, 'Chicken and Broccoli Pasta': 350, 'Butter Chicken': 380, 'Thai Green Chicken Curry': 370, 'Moroccan Chicken': 320, 'Steak with Mushroom Sauce': 380, 'Creamy Chicken & Mushroom Gnocchi': 450, 'Roasted Lemon Chicken & Potatoes': 340, 'Beef Lasagna': 350, 'Lamb Souvlaki': 300, 'Baked Family Lasagna': 1500, 'Sunday Roast Lamb': 380, 'Smashed Burger': 400, 'Creamy Fettuccine': 400}

# Names are available for planning; production instructions still need supplying.
PENDING_RECIPE_MEALS = ('Sunday Roast Lamb', 'Smashed Burger', 'Creamy Fettuccine')

def meal_label(name):
    weight = MEAL_WEIGHTS_G.get(name)
    return f"{name} - {weight:g}g" if weight is not None else name

def check_recipe_readiness(meal_totals):
    pending = [name for name in PENDING_RECIPE_MEALS if meal_totals.get(name.upper(), 0) > 0]
    if pending:
        raise ValueError("Production instructions are still needed for: " + ", ".join(pending))
