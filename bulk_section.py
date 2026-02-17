import math
from datetime import datetime
from utils import fmt_int_up, fmt_weight

# --- BULK SECTIONS (match names to uploaded CSV exactly) ---
bulk_sections = [
    {"title": "Spaghetti Order", "batch_ingredient": "Spaghetti", "batch_size": 85,
     "ingredients": {"Spaghetti": 64, "Oil": 0.7},
     "meals": ["Spaghetti Bolognese"]},
    {"title": "Penne Order", "batch_ingredient": "Penne", "batch_size": 135,
     "ingredients": {"Penne": 59, "Oil": 0.7},
     "meals": ["Chicken Pesto Pasta", "Chicken and Broccoli Pasta"]},
    {"title": "Rice Order", "batch_ingredient": "Rice", "batch_size": 180,
     "ingredients": {"Rice": 53, "Water": 95, "Salt": 1, "Oil": 1.5},
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
    {"title": "Chicken Thigh", "batch_ingredient": "Chicken Thigh", "batch_size": 0,
     "ingredients": {"Chicken": 160, "Oil": 4, "Roast Chicken Mix": 4},
     "meals": ["Roasted Lemon Chicken & Potatoes", "Chicken Fajita Bowl"]},
    {"title": "Steak", "batch_ingredient": "Steak", "batch_size": 0,
     "ingredients": {"Steak": 93, "Oil": 1.5, "Baking Soda": 3},
     "meals": ["Steak with Mushroom Sauce", "Steak On Its Own"]},
    {"title": "Lamb Marinate", "batch_ingredient": "Lamb Shoulder", "batch_size": 0,
     "ingredients": {"Lamb Shoulder": 162, "Oil": 2, "Salt": 1.5, "Oregano": 0.3, "Baking Soda": 5.27},
     "meals": ["Lamb Souvlaki"]},
    {"title": "Potato Mash", "batch_ingredient": "Potato", "batch_size": 0,
     "ingredients": {"Potato": 150, "Cooking Cream": 20, "Butter": 7, "Salt": 1.5, "White Pepper": 0.5},
     "meals": ["Beef Meatballs", "Steak with Mushroom Sauce"]},
    {"title": "Sweet Potato Mash", "batch_ingredient": "Sweet Potato", "batch_size": 0,
     "ingredients": {"Sweet Potato": 200, "Salt": 1, "White Pepper": 0.5},
     "meals": ["Shepherd's Pie", "Chicken with Sweet Potato and Beans"]},
    {"title": "Roasted Potatoes", "batch_ingredient": "Roasted Potatoes", "batch_size": 63,
     "ingredients": {"Roasted Potatoes": 190, "Oil": 1.62, "Spices Mix": 2.5},
     "meals": ["Naked Chicken Parma", "Lamb Souvlaki"]},
    {"title": "Roasted Lemon Potatoes", "batch_ingredient": "Potatoes", "batch_size": 63,
     "ingredients": {"Potatoes": 207, "Oil": 2, "Salt": 1.2},
     "meals": ["Roasted Lemon Chicken & Potatoes"]},
    {"title": "Roasted Thai Potatoes", "batch_ingredient": "Potato", "batch_size": 0,
     "ingredients": {"Potato": 60, "Salt": 1},
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
     ]}
]

def draw_bulk_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, header_date=None):
    title1 = f"Daily Production Report - {header_date or datetime.today().strftime('%d/%m/%Y')}"
    if not start_y:
        pdf.add_page()
        pdf.set_y(0)
    else:
        pdf.set_y(start_y)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title1, ln=1, align='C')
    pdf.ln(5)

    heights = [pdf.get_y(), pdf.get_y()]
    col = 0

    def next_pos(heights, col, block_h, title=None):
        if heights[col] + block_h > bottom:
            col = 1 - col
            if heights[col] + block_h > bottom:
                pdf.add_page()
                if title:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, title, ln=1, align='C')
                    pdf.ln(5)
                heights = [pdf.get_y(), pdf.get_y()]
        return heights, col

    for sec in bulk_sections:
        block_h = (len(sec['ingredients']) + 2) * ch + pad
        heights, col = next_pos(heights, col, block_h, title1)
        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, sec['title'], ln=1, fill=True)

        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in [("Ingredient", 0.4), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Total", 0.15), ("Batches", 0.15)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)

        pdf.set_font("Arial", "", 8)
        total_meals = sum(meal_totals.get(m.upper(), 0) for m in sec['meals'])
        batches = math.ceil(total_meals / sec['batch_size']) if sec['batch_size'] > 0 else 0

        for ingr, per in sec['ingredients'].items():
            qty = per * total_meals
            adj = (qty / batches) if batches else qty
            lbl = str(batches) if ingr == sec['batch_ingredient'] else ""

            pdf.set_x(x)
            pdf.cell(col_w * 0.4, ch, ingr[:20], 1)
            pdf.cell(col_w * 0.15, ch, fmt_int_up(per), 1)
            pdf.cell(col_w * 0.15, ch, str(total_meals), 1)
            pdf.cell(col_w * 0.15, ch, fmt_int_up(adj), 1)
            pdf.cell(col_w * 0.15, ch, lbl, 1)
            pdf.ln(ch)

        heights[col] = pdf.get_y() + pad

    return max(heights)
