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
    
    default_day_structure = {
        'Breakfast': [breakfast_main],
        'Lunch': [lunch_main],
        'Dinner': [dinner_main, dinner_side]  # Note: 3 items total (main + side)
    }
    
    # Repeat for requested number of days
    for day in range(1, number_of_days + 1):
        plan[f"Day {day}"] = default_day_structure.copy()
    
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
    
    default_day_structure = {
        'Breakfast': [breakfast_main, breakfast_fruit],
        'Lunch': [lunch_main],
        'Dinner': [dinner_main]
    }
    
    for day in range(1, number_of_days + 1):
        plan[f"Day {day}"] = default_day_structure.copy()
    
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
    
    default_day_structure = {
        'Breakfast': [breakfast_main, breakfast_fruit],
        'Lunch': [lunch_main, lunch_side],
        'Dinner': [dinner_main, dinner_side]
    }
    
    for day in range(1, number_of_days + 1):
        plan[f"Day {day}"] = default_day_structure.copy()
    
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

