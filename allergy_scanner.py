import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
from collections import defaultdict, OrderedDict

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("six-90963-firebase-adminsdk-fbsvc-a693c73228.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://six-90963-default-rtdb.firebaseio.com/'
    })

ref = db.reference("menu_items")

# Fetch dishes from Firebase
def fetch_dishes():
    data = ref.get() or {}
    dishes = []
    for category, entries in data.items():
        for key, item in entries.items():
            item["id"] = key
            item["category"] = category
            dishes.append(item)
    return dishes

# Save dish to Firebase
def save_dish(category, dish):
    ref.child(category).push(dish)

# Delete dish
def delete_dish(category, dish_id):
    ref.child(category).child(dish_id).delete()

# Update dish
def update_dish(category, dish_id, updated):
    ref.child(category).child(dish_id).update(updated)

# Load dishes
dishes = fetch_dishes()
dish_names = [dish["name"] for dish in dishes]

# Tabs for features
tab1, tab2 = st.tabs(["🔍 Allergy Scanner", "🛠️ Admin Panel"])

# -------------------- Allergy Scanner --------------------
with tab1:
    st.markdown("<h2 style='text-align:center; color:white; margin-top: 0;'>🍽️ Allergy Scanner</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='background-color: #f9f9f9; padding: 10px 15px; border-radius: 10px; 
             text-align: center; font-size: 20px; font-weight: bold; color: #333; 
             border: 1px solid #eee; margin-bottom: 15px;'>
            💡 KNOWLEDGE IS MONEY
        </div>
        """,
        unsafe_allow_html=True
    )

    category_order = OrderedDict([
        ("To Snack", "🧂 To Snack"),
        ("To Break", "🍳 To Break"),
        ("To Start", "🥗 To Start"),
        ("To Follow", "🍽️ To Follow"),
        ("To Share", "👫 To Share"),
        ("Dessert", "🍰 Dessert")
    ])

    with st.expander("🔻 Filter by Allergens"):
        all_allergens = sorted({a for dish in dishes for a in dish.get("allergens", [])})
        selected_allergens = st.multiselect("Select allergens to avoid:", all_allergens)

    with st.expander("🔻 Filter by Dietary Preferences"):
        diet_tags = ["Vegetarian", "Pescetarian", "Halal", "Vegan"]
        selected_diet = st.multiselect("Select dietary preferences to follow:", diet_tags)

    with st.expander("🧂 Filter by Required Ingredients"):
        all_ingredients = sorted({i for dish in dishes for i in dish.get("ingredients", [])})
        include_ingredients = st.multiselect("Must include ingredients:", all_ingredients)

    safe_dishes = []
    modifiable_dishes = []

    for dish in dishes:
        allergens = dish.get("allergens", [])
        removable = dish.get("removable_allergens", [])
        diet = dish.get("diet", [])
        ingredients = dish.get("ingredients", [])

        allergens_block = [
            a for a in selected_allergens
            if any(a.lower() in x.lower() for x in allergens) and
               not any(a.lower() in r.lower() for r in removable)
        ]
        removable_ok = [
            a for a in selected_allergens
            if any(a.lower() in r.lower() for r in removable)
        ]
        diet_ok = all(d in diet for d in selected_diet)

        includes_ok = all(
            ing.lower() in [i.lower() for i in ingredients] for ing in include_ingredients
        )

        if not allergens_block and diet_ok and includes_ok:
            if removable_ok:
                modifiable_dishes.append((dish, removable_ok))
            else:
                safe_dishes.append(dish)

    grouped_safe = defaultdict(list)
    grouped_modifiable = defaultdict(list)
    for dish in safe_dishes:
        cat = dish.get("category", "Uncategorized")
        grouped_safe[cat].append(f"✅ {dish['name']}")
    for dish, mods in modifiable_dishes:
        cat = dish.get("category", "Uncategorized")
        grouped_modifiable[cat].append(f"⚠️ {dish['name']} *(Can be made {', '.join(m + '-free' for m in mods)})*")

    if selected_allergens or selected_diet or include_ingredients:
        st.subheader("✅ Safe Dishes")
        any_displayed = False
        for key, label in category_order.items():
            safe = grouped_safe.get(key, [])
            modifiable = grouped_modifiable.get(key, [])
            if safe or modifiable:
                st.markdown(f"### {label}")
                for name in safe:
                    st.markdown(f"- {name}")
                for name in modifiable:
                    st.markdown(f"- {name}")
                any_displayed = True
        if not any_displayed:
            st.warning("No matching dishes found based on your filters.")
    else:
        st.info("Please select allergens, dietary preferences, or ingredients to filter menu options.")

# -------------------- Admin Panel --------------------
with tab2:
    st.title("🛠️ Admin Panel")
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["➕ Add Dish", "✏️ Edit Dish", "🗑️ Delete Dish"])

    with admin_tab1:
        name = st.text_input("Dish Name")
        category = st.selectbox("Category", ["To Snack", "To Break", "To Start", "To Follow", "To Share", "Dessert"])
        ingredients = st.text_area("Ingredients (comma-separated)")
        allergens = st.text_area("Allergens (comma-separated)")
        removable = st.text_area("Removable Allergens (comma-separated)")
        diet = st.multiselect("Diet Tags", ["Vegetarian", "Pescetarian", "Halal", "Vegan"])

        if st.button("Save Dish"):
            new_dish = {
                "name": name,
                "ingredients": [i.strip() for i in ingredients.split(",") if i.strip()],
                "allergens": [a.strip() for a in allergens.split(",") if a.strip()],
                "removable_allergens": [r.strip() for r in removable.split(",") if r.strip()],
                "diet": diet
            }
            save_dish(category, new_dish)
            st.success("✅ Dish added to Firebase!")

    with admin_tab2:
        selected = st.selectbox("Select Dish to Edit", dish_names)
        selected_dish = next((d for d in dishes if d["name"] == selected), None)

        if selected_dish:
            new_name = st.text_input("Dish Name", value=selected_dish["name"])
            new_ingredients = st.text_area("Ingredients", value=", ".join(selected_dish.get("ingredients", [])))
            new_allergens = st.text_area("Allergens", value=", ".join(selected_dish.get("allergens", [])))
            new_removable = st.text_area("Removable Allergens", value=", ".join(selected_dish.get("removable_allergens", [])))
            new_diet = st.multiselect("Diet Tags", ["Vegetarian", "Pescetarian", "Halal", "Vegan"], default=selected_dish.get("diet", []))

            if st.button("Update Dish"):
                updated = {
                    "name": new_name,
                    "ingredients": [i.strip() for i in new_ingredients.split(",") if i.strip()],
                    "allergens": [a.strip() for a in new_allergens.split(",") if a.strip()],
                    "removable_allergens": [r.strip() for r in new_removable.split(",") if r.strip()],
                    "diet": new_diet
                }
                update_dish(selected_dish["category"], selected_dish["id"], updated)
                st.success("✅ Dish updated in Firebase!")

    with admin_tab3:
        delete_target = st.selectbox("Select Dish to Delete", dish_names)
        delete_dish_data = next((d for d in dishes if d["name"] == delete_target), None)

        if delete_dish_data and st.button("Delete This Dish"):
            delete_dish(delete_dish_data["category"], delete_dish_data["id"])
            st.success("🗑️ Dish deleted from Firebase!")
