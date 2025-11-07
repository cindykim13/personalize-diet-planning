# planner/default_plans.py

"""
Default Meal Plans Repository

This module provides pre-defined, safe default meal plans that serve as fallback
options when the dynamic optimization pipeline fails. These plans use REAL recipes
from the database when available, with fallback to pre-defined nutritional data.

Each default plan is structured as a multi-day meal plan dictionary, matching
the format returned by the optimization pipeline.
"""

from planner.models import Recipe
from django.db.models import Q


def get_default_plan(primary_goal: str, number_of_days: int = 7) -> dict:
    """
    Returns a default meal plan based on the user's primary goal.
    
    These plans use REAL recipes from the database when available, with fallback
    to pre-defined nutritional data. The plans are designed to be nutritionally
    reasonable but may not perfectly match user-specific targets.
    
    :param primary_goal: User's primary goal ('lose_weight', 'maintain', 'gain_muscle')
    :param number_of_days: Number of days for the plan (default: 7)
    :return: Dictionary with structure matching the optimization pipeline output
    """
    # Select appropriate default plan based on goal
    if primary_goal == 'gain_muscle':
        return _get_high_protein_default_plan(number_of_days)
    elif primary_goal == 'lose_weight':
        return _get_weight_loss_default_plan(number_of_days)
    else:  # maintain or default
        return _get_balanced_default_plan(number_of_days)


def _find_real_recipe(search_terms: list, meal_type: str, nutritional_targets: dict = None, tolerance_pct: float = 30.0) -> dict:
    """
    Attempts to find a real recipe in the database that matches the search criteria.
    
    :param search_terms: List of search terms to match in recipe name (e.g., ['scrambled', 'egg', 'spinach'])
    :param meal_type: Required meal_type for the recipe
    :param nutritional_targets: Optional dict with 'calories', 'protein_g', etc. for nutritional matching
    :param tolerance_pct: Percentage tolerance for nutritional matching (default 30%)
    :return: Recipe dictionary with required fields, or None if not found
    """
    try:
        # Build query with search terms
        query = Q(meal_type=meal_type) & ~Q(meal_type='Unknown')
        
        # Add name search (case-insensitive, ANY term matches for flexibility)
        # Try exact match first (all terms), then fall back to partial match (any term)
        name_query_all = Q()
        for term in search_terms:
            name_query_all &= Q(name__icontains=term)
        
        # Try exact match first
        recipe = Recipe.objects.filter(query & name_query_all).first()
        
        # If no exact match, try partial match (any term)
        if not recipe:
            name_query_any = Q()
            for term in search_terms:
                name_query_any |= Q(name__icontains=term)
            recipe = Recipe.objects.filter(query & name_query_any).first()
        
        if recipe:
            # If nutritional targets provided, check if recipe is within tolerance
            if nutritional_targets:
                cal_match = abs(recipe.avg_calories - nutritional_targets.get('calories', 0)) / max(nutritional_targets.get('calories', 1), 1) * 100 <= tolerance_pct
                pro_match = abs(recipe.avg_protein_g - nutritional_targets.get('protein_g', 0)) / max(nutritional_targets.get('protein_g', 1), 1) * 100 <= tolerance_pct
                
                # If nutritional match is close, use real recipe
                if cal_match and pro_match:
                    return {
                        'id': recipe.id,
                        'name': recipe.name,
                        'meal_type': recipe.meal_type,
                        'avg_calories': recipe.avg_calories,
                        'avg_protein_g': recipe.avg_protein_g,
                        'avg_fat_g': recipe.avg_fat_g,
                        'avg_carbs_g': recipe.avg_carbs_g
                    }
            else:
                # No nutritional targets, just use the recipe
                return {
                    'id': recipe.id,
                    'name': recipe.name,
                    'meal_type': recipe.meal_type,
                    'avg_calories': recipe.avg_calories,
                    'avg_protein_g': recipe.avg_protein_g,
                    'avg_fat_g': recipe.avg_fat_g,
                    'avg_carbs_g': recipe.avg_carbs_g
                }
    except Exception as e:
        print(f"[DEFAULT PLANS] Error searching for recipe: {e}")
    
    return None


def _create_default_recipe(recipe_id: int, name: str, meal_type: str, nutritional_data: dict) -> dict:
    """
    Creates a default recipe dictionary with pre-defined nutritional data.
    
    :param recipe_id: Unique negative ID for default recipe
    :param name: Recipe name
    :param meal_type: Meal type
    :param nutritional_data: Dict with 'calories', 'protein_g', 'fat_g', 'carbs_g'
    :return: Recipe dictionary
    """
    return {
        'id': recipe_id,
        'name': f"{name} (Default)",
        'meal_type': meal_type,
        'avg_calories': nutritional_data.get('calories', 0.0),
        'avg_protein_g': nutritional_data.get('protein_g', 0.0),
        'avg_fat_g': nutritional_data.get('fat_g', 0.0),
        'avg_carbs_g': nutritional_data.get('carbs_g', 0.0)
    }


def _ensure_unique_recipe_for_day(recipe_template: dict, meal_type: str, used_recipe_ids: set, day_number: int) -> dict:
    """
    Helper function to ensure recipe uniqueness across days in default plans.
    
    If the template recipe is already used, finds an alternative from the database.
    If no alternative found, returns a modified template with unique ID (for negative IDs).
    
    :param recipe_template: Template recipe dictionary
    :param meal_type: Required meal type
    :param used_recipe_ids: Set of already-used recipe IDs
    :param day_number: Current day number (for unique ID generation)
    :return: Recipe dictionary (either template or alternative)
    """
    # If template is not yet used, return it
    if recipe_template['id'] not in used_recipe_ids:
        return recipe_template
    
    # Try to find an alternative recipe from database
    try:
        alt_recipe = Recipe.objects.filter(
            meal_type=meal_type
        ).exclude(
            id__in=used_recipe_ids
        ).exclude(
            meal_type='Unknown'
        ).order_by('?').first()
        
        if alt_recipe:
            return {
                'id': alt_recipe.id,
                'name': alt_recipe.name,
                'meal_type': alt_recipe.meal_type,
                'avg_calories': alt_recipe.avg_calories,
                'avg_protein_g': alt_recipe.avg_protein_g,
                'avg_fat_g': alt_recipe.avg_fat_g,
                'avg_carbs_g': alt_recipe.avg_carbs_g
            }
    except Exception:
        pass  # If database query fails, fall through to unique ID modification
    
    # If no alternative found and template has negative ID, make it unique per day
    if recipe_template['id'] < 0:
        unique_id = recipe_template['id'] - (day_number * 1000)
        unique_recipe = recipe_template.copy()
        unique_recipe['id'] = unique_id
        unique_recipe['name'] = f"{recipe_template['name']} (Day {day_number})"
        return unique_recipe
    
    # Last resort: return template as-is (may cause repetition, but better than crashing)
    return recipe_template


def _get_balanced_default_plan(number_of_days: int) -> dict:
    """
    Returns a balanced, maintenance-focused default plan.
    
    This plan provides approximately 2000-2200 calories per day with
    balanced macronutrients (20% protein, 30% fat, 50% carbs).
    
    Uses Template 2: Maintenance Day from requirements.
    """
    plan = {}
    
    # Template 2: Maintenance Day (~2200 kcal, Balanced)
    # Try to find real recipes, fallback to pre-defined data
    
    # Breakfast: Oatmeal with Nuts and Berries
    breakfast_main = _find_real_recipe(
        ['oatmeal', 'nuts', 'berries'],
        'Breakfast',
        {'calories': 450, 'protein_g': 15, 'fat_g': 20, 'carbs_g': 60}
    ) or _create_default_recipe(
        -1, 'Oatmeal with Nuts and Berries', 'Breakfast',
        {'calories': 450, 'protein_g': 15, 'fat_g': 20, 'carbs_g': 60}
    )
    
    # Lunch: Beef Stir-Fry with Brown Rice
    lunch_main = _find_real_recipe(
        ['beef', 'stir', 'fry', 'rice'],
        'Main Course',
        {'calories': 650, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 70}
    ) or _find_real_recipe(
        ['stir', 'fry'],
        'Main Course',
        {'calories': 650, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 70}
    ) or _create_default_recipe(
        -2, 'Beef Stir-Fry with Brown Rice', 'Main Course',
        {'calories': 650, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 70}
    )
    
    # Dinner: Pasta with Marinara Sauce and Turkey Meatballs
    dinner_main = _find_real_recipe(
        ['pasta', 'marinara', 'turkey', 'meatball'],
        'Main Course',
        {'calories': 700, 'protein_g': 45, 'fat_g': 28, 'carbs_g': 75}
    ) or _find_real_recipe(
        ['pasta', 'meatball'],
        'Main Course',
        {'calories': 700, 'protein_g': 45, 'fat_g': 28, 'carbs_g': 75}
    ) or _create_default_recipe(
        -3, 'Pasta with Marinara Sauce and Turkey Meatballs', 'Main Course',
        {'calories': 700, 'protein_g': 45, 'fat_g': 28, 'carbs_g': 75}
    )
    
    # Dinner Side: Green Salad with Vinaigrette
    dinner_side = _find_real_recipe(
        ['green', 'salad', 'vinaigrette'],
        'Salad',
        {'calories': 150, 'protein_g': 3, 'fat_g': 12, 'carbs_g': 8}
    ) or _find_real_recipe(
        ['salad'],
        'Salad',
        {'calories': 150, 'protein_g': 3, 'fat_g': 12, 'carbs_g': 8}
    ) or _create_default_recipe(
        -4, 'Side Green Salad with Vinaigrette', 'Salad',
        {'calories': 150, 'protein_g': 3, 'fat_g': 12, 'carbs_g': 8}
    )
    
    # CRITICAL FIX: Default plans must use DIFFERENT recipes for each day to avoid repetition
    used_recipe_ids = set()
    
    for day in range(1, number_of_days + 1):
        # Ensure uniqueness for each recipe type
        day_breakfast = _ensure_unique_recipe_for_day(breakfast_main, 'Breakfast', used_recipe_ids, day)
        day_lunch = _ensure_unique_recipe_for_day(lunch_main, 'Main Course', used_recipe_ids, day)
        day_dinner = _ensure_unique_recipe_for_day(dinner_main, 'Main Course', used_recipe_ids, day)
        day_side = _ensure_unique_recipe_for_day(dinner_side, 'Salad', used_recipe_ids, day)
        
        day_structure = {
            'Breakfast': [day_breakfast],
            'Lunch': [day_lunch],
            'Dinner': [day_dinner, day_side]
        }
        
        # Track used recipes
        used_recipe_ids.add(day_breakfast['id'])
        used_recipe_ids.add(day_lunch['id'])
        used_recipe_ids.add(day_dinner['id'])
        used_recipe_ids.add(day_side['id'])
        
        plan[f"Day {day}"] = day_structure
    
    return plan


def _get_high_protein_default_plan(number_of_days: int) -> dict:
    """
    Returns a high-protein default plan for muscle gain.
    
    This plan provides approximately 2500-2800 calories per day with
    high protein content (40% protein, 20% fat, 40% carbs).
    
    Uses Template 3: Muscle Gain Day from requirements.
    """
    plan = {}
    
    # Template 3: Muscle Gain Day (~2800 kcal, Very High-Protein)
    
    # Breakfast: Greek Yogurt with Granola and Protein Powder
    breakfast_main = _find_real_recipe(
        ['greek', 'yogurt', 'granola', 'protein'],
        'Breakfast',
        {'calories': 600, 'protein_g': 50, 'fat_g': 15, 'carbs_g': 65}
    ) or _find_real_recipe(
        ['yogurt', 'granola'],
        'Breakfast',
        {'calories': 600, 'protein_g': 50, 'fat_g': 15, 'carbs_g': 65}
    ) or _create_default_recipe(
        -10, 'Greek Yogurt with Granola and Protein Powder', 'Breakfast',
        {'calories': 600, 'protein_g': 50, 'fat_g': 15, 'carbs_g': 65}
    )
    
    # Breakfast: Banana
    breakfast_fruit = _find_real_recipe(
        ['banana'],
        'Fruit',
        {'calories': 100, 'protein_g': 1, 'fat_g': 0.3, 'carbs_g': 27}
    ) or _create_default_recipe(
        -11, 'Banana', 'Fruit',
        {'calories': 100, 'protein_g': 1, 'fat_g': 0.3, 'carbs_g': 27}
    )
    
    # Lunch: Large Burrito Bowl with Double Chicken
    lunch_main = _find_real_recipe(
        ['burrito', 'bowl', 'chicken'],
        'Main Course',
        {'calories': 900, 'protein_g': 65, 'fat_g': 30, 'carbs_g': 90}
    ) or _find_real_recipe(
        ['burrito', 'chicken'],
        'Main Course',
        {'calories': 900, 'protein_g': 65, 'fat_g': 30, 'carbs_g': 90}
    ) or _create_default_recipe(
        -12, 'Large Burrito Bowl with Double Chicken', 'Main Course',
        {'calories': 900, 'protein_g': 65, 'fat_g': 30, 'carbs_g': 90}
    )
    
    # Dinner: Steak with Roasted Potatoes and Broccoli
    dinner_main = _find_real_recipe(
        ['steak', 'roasted', 'potato', 'broccoli'],
        'Main Course',
        {'calories': 850, 'protein_g': 60, 'fat_g': 40, 'carbs_g': 65}
    ) or _find_real_recipe(
        ['steak', 'potato'],
        'Main Course',
        {'calories': 850, 'protein_g': 60, 'fat_g': 40, 'carbs_g': 65}
    ) or _create_default_recipe(
        -13, 'Steak with Roasted Potatoes and Broccoli', 'Main Course',
        {'calories': 850, 'protein_g': 60, 'fat_g': 40, 'carbs_g': 65}
    )
    
    # CRITICAL FIX: Ensure uniqueness across days
    used_recipe_ids = set()
    
    for day in range(1, number_of_days + 1):
        day_breakfast = _ensure_unique_recipe_for_day(breakfast_main, 'Breakfast', used_recipe_ids, day)
        day_breakfast_fruit = _ensure_unique_recipe_for_day(breakfast_fruit, 'Fruit', used_recipe_ids, day)
        day_lunch = _ensure_unique_recipe_for_day(lunch_main, 'Main Course', used_recipe_ids, day)
        day_dinner = _ensure_unique_recipe_for_day(dinner_main, 'Main Course', used_recipe_ids, day)
        
        day_structure = {
            'Breakfast': [day_breakfast, day_breakfast_fruit],
            'Lunch': [day_lunch],
            'Dinner': [day_dinner]
        }
        
        used_recipe_ids.add(day_breakfast['id'])
        used_recipe_ids.add(day_breakfast_fruit['id'])
        used_recipe_ids.add(day_lunch['id'])
        used_recipe_ids.add(day_dinner['id'])
        
        plan[f"Day {day}"] = day_structure
    
    return plan


def _get_weight_loss_default_plan(number_of_days: int) -> dict:
    """
    Returns a weight-loss focused default plan.
    
    This plan provides approximately 1500-1800 calories per day with
    higher protein for satiety (40% protein, 30% fat, 30% carbs).
    
    Uses Template 1: Weight Loss Day from requirements.
    """
    plan = {}
    
    # Template 1: Weight Loss Day (~1500 kcal, High-Protein/Fiber)
    
    # Breakfast: Scrambled Eggs with Spinach
    breakfast_main = _find_real_recipe(
        ['scrambled', 'egg', 'spinach'],
        'Breakfast',
        {'calories': 300, 'protein_g': 25, 'fat_g': 20, 'carbs_g': 5}
    ) or _find_real_recipe(
        ['scrambled', 'egg'],
        'Breakfast',
        {'calories': 300, 'protein_g': 25, 'fat_g': 20, 'carbs_g': 5}
    ) or _create_default_recipe(
        -20, 'Scrambled Eggs with Spinach', 'Breakfast',
        {'calories': 300, 'protein_g': 25, 'fat_g': 20, 'carbs_g': 5}
    )
    
    # Breakfast: Apple Slices
    breakfast_fruit = _find_real_recipe(
        ['apple'],
        'Fruit',
        {'calories': 80, 'protein_g': 0.5, 'fat_g': 0.3, 'carbs_g': 22}
    ) or _create_default_recipe(
        -21, 'Apple Slices', 'Fruit',
        {'calories': 80, 'protein_g': 0.5, 'fat_g': 0.3, 'carbs_g': 22}
    )
    
    # Lunch: Grilled Chicken Salad
    lunch_main = _find_real_recipe(
        ['grilled', 'chicken', 'salad'],
        'Salad',
        {'calories': 450, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 15}
    ) or _find_real_recipe(
        ['chicken', 'salad'],
        'Salad',
        {'calories': 450, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 15}
    ) or _create_default_recipe(
        -22, 'Grilled Chicken Salad', 'Salad',
        {'calories': 450, 'protein_g': 40, 'fat_g': 25, 'carbs_g': 15}
    )
    
    # Lunch: Quinoa
    lunch_side = _find_real_recipe(
        ['quinoa'],
        'Side Dish',
        {'calories': 150, 'protein_g': 6, 'fat_g': 2.5, 'carbs_g': 28}
    ) or _create_default_recipe(
        -23, 'Quinoa', 'Side Dish',
        {'calories': 150, 'protein_g': 6, 'fat_g': 2.5, 'carbs_g': 28}
    )
    
    # Dinner: Baked Salmon with Asparagus
    dinner_main = _find_real_recipe(
        ['baked', 'salmon', 'asparagus'],
        'Main Course',
        {'calories': 400, 'protein_g': 35, 'fat_g': 28, 'carbs_g': 10}
    ) or _find_real_recipe(
        ['salmon', 'asparagus'],
        'Main Course',
        {'calories': 400, 'protein_g': 35, 'fat_g': 28, 'carbs_g': 10}
    ) or _create_default_recipe(
        -24, 'Baked Salmon with Asparagus', 'Main Course',
        {'calories': 400, 'protein_g': 35, 'fat_g': 28, 'carbs_g': 10}
    )
    
    # Dinner: Small Sweet Potato
    dinner_side = _find_real_recipe(
        ['sweet', 'potato'],
        'Side Dish',
        {'calories': 120, 'protein_g': 2, 'fat_g': 0.2, 'carbs_g': 28}
    ) or _create_default_recipe(
        -25, 'Small Sweet Potato', 'Side Dish',
        {'calories': 120, 'protein_g': 2, 'fat_g': 0.2, 'carbs_g': 28}
    )
    
    # CRITICAL FIX: Ensure uniqueness across days
    used_recipe_ids = set()
    
    for day in range(1, number_of_days + 1):
        day_breakfast = _ensure_unique_recipe_for_day(breakfast_main, 'Breakfast', used_recipe_ids, day)
        day_breakfast_fruit = _ensure_unique_recipe_for_day(breakfast_fruit, 'Fruit', used_recipe_ids, day)
        day_lunch = _ensure_unique_recipe_for_day(lunch_main, 'Main Course', used_recipe_ids, day)
        day_lunch_side = _ensure_unique_recipe_for_day(lunch_side, 'Side Dish', used_recipe_ids, day)
        day_dinner = _ensure_unique_recipe_for_day(dinner_main, 'Main Course', used_recipe_ids, day)
        day_dinner_side = _ensure_unique_recipe_for_day(dinner_side, 'Side Dish', used_recipe_ids, day)
        
        day_structure = {
            'Breakfast': [day_breakfast, day_breakfast_fruit],
            'Lunch': [day_lunch, day_lunch_side],
            'Dinner': [day_dinner, day_dinner_side]
        }
        
        used_recipe_ids.add(day_breakfast['id'])
        used_recipe_ids.add(day_breakfast_fruit['id'])
        used_recipe_ids.add(day_lunch['id'])
        used_recipe_ids.add(day_lunch_side['id'])
        used_recipe_ids.add(day_dinner['id'])
        used_recipe_ids.add(day_dinner_side['id'])
        
        plan[f"Day {day}"] = day_structure
    
    return plan


def calculate_nutritional_summary(plan: dict) -> dict:
    """
    Calculates the total nutritional summary for a meal plan.
    
    :param plan: Meal plan dictionary (Day 1, Day 2, etc.)
    :return: Dictionary with total calories, protein_g, fat_g, carbs_g
    """
    total_calories = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    
    for day_key, day_plan in plan.items():
        for meal_name, recipes in day_plan.items():
            for recipe in recipes:
                total_calories += recipe.get('avg_calories', 0.0)
                total_protein += recipe.get('avg_protein_g', 0.0)
                total_fat += recipe.get('avg_fat_g', 0.0)
                total_carbs += recipe.get('avg_carbs_g', 0.0)
    
    return {
        'total_calories': round(total_calories, 1),
        'total_protein_g': round(total_protein, 1),
        'total_fat_g': round(total_fat, 1),
        'total_carbs_g': round(total_carbs, 1),
        'number_of_days': len(plan)
    }

