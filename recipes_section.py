import math

# Export meal_recipes for use elsewhere
meal_recipes = {
    "Spaghetti Bolognese": {
        "batch": 90,
        "ingredients": {
            "Beef Mince": 100, "Napoli Sauce": 65, "Crushed Tomatoes": 45, "Beef Stock": 30,
            "Onion": 15, "Zucchini": 15, "Carrot": 15, "Vegetable Oil": 1, "Salt": 3, "Pepper": 1
        }
    },
    "Beef Chow Mein": {
        "batch": 80,
        "ingredients": {
            "Beef Mince": 120, "Celery": 42, "Carrot": 42, "Cabbage": 42, "Onion": 42,
            "Oil": 2, "Pepper": 1, "Salt": 0.5, "Soy Sauce": 13, "Oyster Sauce": 13
        }
    },
    "Shepherd's Pie": {
        "batch": 82,
        "ingredients": {
            "Beef Mince": 100, "Oil": 2, "Carrots": 15, "Capsicum": 15, "Onion": 15,
            "Mushroom": 15, "Peas": 15, "Tomato Paste": 6, "Beef Stock": 20, "Salt": 2, "Pepper": 0.5, "Napoli Sauce": 70
        }
    },
    "Beef Burrito Bowl": {
        "batch": 130,
        "ingredients": {
            "Beef Mince": 95, "Onion": 12, "Capsicum": 12, "Vegetable Oil": 2,
            "Taco Seasoning": 7, "Salt": 1.5, "Pepper": 0.5, "Beef Stock": 40
        }
    },
    "Beef Meatballs": {
        "batch": 0,
        "ingredients": {
            "Mince": 150, "Onion": 10, "Parsley": 3, "Salt": 1.5, "Pepper": 0.2
        }
    },
    "Lebanese Beef Stew": {
        "batch": 80,
        "ingredients": {
            "Chuck Diced": 97, "Onion": 30, "Carrot": 30, "Potato": 30, "Peas": 30,
            "Oil": 2, "Salt": 2.5, "Pepper": 0.5, "Tomato Paste": 20, "Water": 30, "Beef Stock": 30, "Rice": 130
        }
    },
    "Mongolian Beef": {
        "batch": 0,
        "ingredients": {
            "Chuck": 100, "Baking Soda": 2.5, "Water": 10, "Soy Sauce": 5, "Cornflour": 2.5, "Capsicum": 37, "Onion": 37, "Rice": 130
        }
    },
    "Chicken With Vegetables": {
        "batch": 60,
        "ingredients": {
            "Chicken": 135, "Corn": 50, "Beans": 60, "Broccoli": 67
        }
    },
    "Chicken with Sweet Potato and Beans": {
        "batch": 60,
        "ingredients": {
            "Chicken": 135, "Beans": 60
        }
    },
    "Naked Chicken Parma": {
        "batch": 0,
        "ingredients": {
            "Chicken": 150
        }
    },
    "Chicken Pesto Pasta": {
        "batch": 0,
        "ingredients": {
            "Chicken": 130, "Penne": 59, "Sundried Tomatoes": 20
        }
    },
    "Chicken and Broccoli Pasta": {
        "batch": 0,
        "ingredients": {
            "Chicken": 130, "Penne": 59, "Broccoli": 40
        }
    },
    "Butter Chicken": {
        "batch": 60,
        "ingredients": {
            "Chicken": 140, "Peas": 40, "Rice": 130
        }
    },
    "Thai Green Chicken Curry": {
        "batch": 0,
        "ingredients": {
            "Chicken": 144.2, "Rice": 130
        }
    },
    "Moroccan Chicken": {
        "batch": 0,
        "ingredients": {
            "Chicken": 180
        },
        "sub_section": {
            "title": "Chickpea Recipe",
            "ingredients": {
                "Onion": 18, "Zucchini": 27, "Red Capsicum": 27, "Garlic": 1.8, "Oil": 1.8, "Chickpeas": 103.5, "Mix Spices": 1.53, "Chicken Stock": 45
            }
        }
    },
    "Steak with Mushroom Sauce": {
        "batch": 0,
        "ingredients": {
            "Topside Steak": 110
        }
    },
    "Steak On Its Own": {
        "batch": 20,
        "ingredients": {
            "Topside Steak": 200
        }
    },
    "Bean Nachos with Rice": {
        "batch": 60,
        "ingredients": {
            "Drained Beans": 80, "Carrot": 25, "Onion": 20, "Taco Seasoning": 1, "Salt": 1.5, "Pepper": 0.5, "Garlic": 2.5,
            "Vegetable Oil": 1.5, "Cumin": 0.5, "Crushed Tomato": 85, "Water": 41.7
        }
    },
    "Beef Lasagna": {
        "batch": 0,
        "ingredients": {
            "Lasange Sheets": 150, "Mozzerala Cheese Alba": 750, "Napoli Sauce": 500, "Bolognese": 3200
        }
    },
    "Lamb Souvlaki": {
        "batch": 90,
        "ingredients": {
            "Lamb Shoulder": 140, "Potatoes": 140
        }
    },
    "Chicken Fajita Bowl": {
        "batch": 60,
        "ingredients": {
            "Chicken Thigh": 150, "Capsicum": 52, "Red Onion": 52, "Salsa": 30, "Rice": 130
        }
    },
    "Chicken On Its Own": {
        "batch": 6,
        "ingredients": {
            "Chicken Breast": 200
        }
    },
    "Creamy Chicken & Mushroom Gnocchi": {
        "batch": 36,
        "ingredients": {
            "Gnocchi": 150, "Chicken": 80, "Sauce": 200, "Spinach": 25
        }
    }
}

def draw_recipes_section(pdf, meal_totals, xpos, col_w, ch, pad, bottom, start_y=None, meal_recipes_override=None):
    # Use override if passed, otherwise use module-level variable
    recipes = meal_recipes_override if meal_recipes_override is not None else meal_recipes

    pdf.set_y(start_y or pdf.get_y())
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Meal Recipes", ln=1, align='C')
    pdf.ln(5)
    heights = [pdf.get_y(), pdf.get_y()]
    for name, data in recipes.items():
        main = len(data["ingredients"])
        sub = len(data.get("sub_section", {}).get("ingredients", {}))
        rows = 2 + main + (2 + sub if sub else 0)
        block_h = rows * ch + pad
        col = 0 if heights[0] <= heights[1] else 1
        if heights[col] + block_h > bottom:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Meal Recipes (cont'd)", ln=1, align='C')
            pdf.ln(5)
            heights = [pdf.get_y(), pdf.get_y()]
            col = 0
        x, y = xpos[col], heights[col]
        pdf.set_xy(x, y)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, ch, name, ln=1, fill=True)
        pdf.set_x(x)
        pdf.set_font("Arial", "B", 8)
        for h, w in [("Ingredient", 0.3), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Batch Total", 0.25), ("Batch", 0.15)]:
            pdf.cell(col_w * w, ch, h, 1)
        pdf.ln(ch)
        pdf.set_font("Arial", "", 8)
        tot = meal_totals.get(name.upper(), 0)
        batch_val = data.get("batch", 0)
        batches = math.ceil(tot / batch_val) if batch_val > 0 else 0
        for i, (ing, qty) in enumerate(data["ingredients"].items()):
            # If batch > 0, use batch logic; else just qty * tot
            if batch_val > 0 and batches > 0:
                bt = round(qty * tot / batches)
                bl = str(batches) if i == 0 else ""
            else:
                bt = qty * tot
                bl = ""
            pdf.set_x(x)
            pdf.cell(col_w * 0.3, ch, ing[:20], 1)
            pdf.cell(col_w * 0.15, ch, str(qty), 1)
            pdf.cell(col_w * 0.15, ch, str(tot), 1)
            pdf.cell(col_w * 0.25, ch, str(bt), 1)
            pdf.cell(col_w * 0.15, ch, bl, 1)
            pdf.ln(ch)
        if "sub_section" in data:
            sub = data["sub_section"]
            pdf.set_x(x)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(col_w, ch, sub["title"], ln=1)
            pdf.set_x(x)
            pdf.set_font("Arial", "B", 8)
            for h, w in [("Ingredient", 0.3), ("Qty/Meal", 0.15), ("Meals", 0.15), ("Total", 0.25), ("", 0.15)]:
                pdf.cell(col_w * w, ch, h, 1)
            pdf.ln(ch)
            pdf.set_font("Arial", "", 8)
            for ingr, per in sub["ingredients"].items():
                adj = per * tot
                pdf.set_x(x)
                pdf.cell(col_w * 0.3, ch, ingr[:20], 1)
                pdf.cell(col_w * 0.15, ch, str(per), 1)
                pdf.cell(col_w * 0.15, ch, str(tot), 1)
                pdf.cell(col_w * 0.25, ch, str(adj), 1)
                pdf.cell(col_w * 0.15, ch, "", 1)
                pdf.ln(ch)
        heights[col] = pdf.get_y() + pad
    return max(heights)
