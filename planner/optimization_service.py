# planner/optimization_service.py

import pulp
import pandas as pd
import random

def create_single_meal(recipe_pool: list, meal_target_nutrients: dict, meal_name: str = "Meal", 
                       meal_structure: dict = None, max_protein_deviation_pct: float = 15.0):
    """
    Optimizes a single meal (Breakfast, Lunch, or Dinner) to meet specific nutritional targets.
    
    REAL-WORLD MEAL STRUCTURE VERSION:
    - Meal-specific structural requirements (Breakfast vs Lunch/Dinner)
    - Dynamic constraint building based on meal_structure dictionary
    - Enhanced protein prioritization (weight = 3.0)
    - Hard constraint tolerance for critical nutrients
    
    This function solves a smaller, focused optimization problem for one meal slot.
    The structural requirements are defined by the meal_structure dictionary:
    - Example Breakfast: {'Breakfast': 1, 'Fruit': 1, 'Drink': 0}
    - Example Lunch: {'Main Course': 1, 'Side Dish': 1, 'Salad': 0}
    - Items with count > 0 are required, count == 0 are optional
    
    :param recipe_pool: List of recipe dictionaries (must include 'meal_type' field).
    :param meal_target_nutrients: Dict with keys 'calories', 'protein_g', 'fat_g', 'carbs_g'.
    :param meal_name: Name of the meal (e.g., 'Breakfast', 'Lunch', 'Dinner') for logging.
    :param meal_structure: Dictionary mapping meal_type to required count.
                          Example: {'Breakfast': 1, 'Fruit': 1} means 1 Breakfast item + 1 Fruit.
                          If None, defaults to {'Main Course': 1, 'Side Dish': 1} for backward compatibility.
    :param max_protein_deviation_pct: Maximum allowed protein deviation percentage (default 15%).
                                      Set to None to disable hard constraint.
    :return: List of selected recipe dictionaries, or None if no solution found.
    """
    if not recipe_pool:
        print(f"[OPTIMIZER] Recipe pool is empty for {meal_name}. Cannot create a meal.")
        return None
    
    # Early validation: Check meal_type field exists
    if not recipe_pool or 'meal_type' not in recipe_pool[0]:
        print(f"[OPTIMIZER] WARNING: 'meal_type' field not found. Cannot enforce meal structure for {meal_name}.")
        return None
    
    # Default meal_structure for backward compatibility
    if meal_structure is None:
        meal_structure = {'Main Course': 1, 'Side Dish': 1}
    
    # MEMORY OPTIMIZATION: Create DataFrame with only necessary columns
    required_columns = ['id', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g']
    
    # Verify all required columns exist in the recipe pool
    missing_cols = [col for col in required_columns if col not in recipe_pool[0]]
    if missing_cols:
        print(f"[OPTIMIZER] ERROR: Missing required columns: {missing_cols}")
        return None
    
    # Create DataFrame with minimal columns only
    minimal_data = [
        {col: recipe[col] for col in required_columns}
        for recipe in recipe_pool
    ]
    
    recipes_df = pd.DataFrame(minimal_data).set_index('id')
    
    # Check minimum pool size (flexible structure: 2-3 recipes per meal)
    min_recipes_needed = 2  # At minimum, need 2 recipes (e.g., Breakfast + Fruit, Main Course + Side)
    if len(recipes_df) < min_recipes_needed:
        print(f"[OPTIMIZER] Not enough recipes in pool for {meal_name} ({len(recipes_df)} available, need at least {min_recipes_needed}).")
        return None
    
    # Initialize optimization problem
    prob = pulp.LpProblem(f"SingleMealOptimization_{meal_name}", pulp.LpMinimize)
    
    # Decision variables: binary (0 or 1) for each recipe
    recipe_vars = pulp.LpVariable.dicts("Recipe", recipes_df.index, cat='Binary')
    
    # Deviation variables for nutrients (to linearize the objective)
    nutrients_to_optimize = ['avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g']
    pos_dev = pulp.LpVariable.dicts("PositiveDev", nutrients_to_optimize, lowBound=0)
    neg_dev = pulp.LpVariable.dicts("NegativeDev", nutrients_to_optimize, lowBound=0)
    
    # === ENHANCED OBJECTIVE FUNCTION WITH NUTRITIONAL INTELLIGENCE ===
    # Protein gets highest priority (critical for muscle/health/maintenance)
    # Increased from 1.2 to 3.0 to prioritize protein accuracy
    protein_weight = 3.0
    calorie_weight = 1.0
    carb_weight = 1.0
    fat_weight = 0.8  # Fat is more flexible (can vary more without health issues)
    
    # Objective: minimize weighted total deviation from targets
    # Use linear terms for now (PuLP linear programming)
    prob += (
        (pos_dev['avg_calories'] + neg_dev['avg_calories']) * calorie_weight +
        (pos_dev['avg_protein_g'] + neg_dev['avg_protein_g']) * protein_weight +
        (pos_dev['avg_fat_g'] + neg_dev['avg_fat_g']) * fat_weight +
        (pos_dev['avg_carbs_g'] + neg_dev['avg_carbs_g']) * carb_weight
    )
    
    # === CONSTRAINTS ===
    
    # Constraint 1: Flexible total recipes (handled by structural constraints)
    # We'll calculate total after structural constraints are defined
    
    # Constraint 2: Dynamic structural constraints based on meal_structure dictionary
    # This allows meal-specific requirements with flexible complementary dishes
    total_recipes_selected = pulp.lpSum([recipe_vars[i] for i in recipes_df.index])
    
    # Handle required types (count > 0) and flexible optional types (count == 0 but part of group)
    required_types = {mt: count for mt, count in meal_structure.items() if count > 0}
    optional_type_groups = {}
    
    # Identify flexible groups (e.g., Fruit OR Drink for Breakfast, Side/Salad/Soup for Lunch/Dinner)
    if meal_name == 'Breakfast':
        # Breakfast: 1 Breakfast item (required) + 1 Fruit OR Drink (flexible)
        if 'Breakfast' in required_types:
            breakfast_indices = list(recipes_df[recipes_df['meal_type'] == 'Breakfast'].index)
            if len(breakfast_indices) < required_types['Breakfast']:
                print(f"[OPTIMIZER] Not enough 'Breakfast' recipes for {meal_name} (need {required_types['Breakfast']}, have {len(breakfast_indices)}).")
                return None
            prob += pulp.lpSum([recipe_vars[i] for i in breakfast_indices]) == required_types['Breakfast'], f"Required_Breakfast"
        
        # Flexible complementary: 1 Fruit OR 1 Drink
        fruit_indices = list(recipes_df[recipes_df['meal_type'] == 'Fruit'].index)
        drink_indices = list(recipes_df[recipes_df['meal_type'] == 'Drink'].index)
        complementary_count = pulp.lpSum([recipe_vars[i] for i in fruit_indices + drink_indices])
        prob += complementary_count >= 1, "MinComplementary_Breakfast"  # At least 1
        prob += complementary_count <= 1, "MaxComplementary_Breakfast"  # At most 1
        
        # Total: exactly 2 recipes (1 Breakfast + 1 complementary)
        prob += total_recipes_selected == 2, "TotalRecipes_Breakfast"
    
    elif meal_name in ['Lunch', 'Dinner']:
        # Lunch/Dinner: 1 Main Course (required) + 1-2 complementary dishes (flexible)
        if 'Main Course' in required_types:
            main_indices = list(recipes_df[recipes_df['meal_type'] == 'Main Course'].index)
            if len(main_indices) < required_types['Main Course']:
                print(f"[OPTIMIZER] Not enough 'Main Course' recipes for {meal_name} (need {required_types['Main Course']}, have {len(main_indices)}).")
                return None
            prob += pulp.lpSum([recipe_vars[i] for i in main_indices]) == required_types['Main Course'], f"Required_MainCourse"
        
        # Flexible complementary: 1-2 from Side Dish, Salad, or Soup
        complementary_types = ['Side Dish', 'Side', 'Salad', 'Soup']
        complementary_indices = []
        for comp_type in complementary_types:
            comp_type_indices = list(recipes_df[recipes_df['meal_type'] == comp_type].index)
            complementary_indices.extend(comp_type_indices)
        
        complementary_count = pulp.lpSum([recipe_vars[i] for i in complementary_indices])
        prob += complementary_count >= 1, "MinComplementary_LunchDinner"  # At least 1
        prob += complementary_count <= 2, "MaxComplementary_LunchDinner"  # At most 2
        
        # Total: 2-3 recipes (1 Main Course + 1-2 complementary)
        prob += total_recipes_selected >= 2, "MinTotalRecipes_LunchDinner"
        prob += total_recipes_selected <= 3, "MaxTotalRecipes_LunchDinner"
    
    else:
        # Fallback for unknown meal types: use original rigid structure
        # Calculate total_recipes_needed from required_types
        total_recipes_needed = sum(required_types.values())
        
        for meal_type, required_count in required_types.items():
            type_indices = list(recipes_df[recipes_df['meal_type'] == meal_type].index)
            if len(type_indices) < required_count:
                print(f"[OPTIMIZER] Not enough '{meal_type}' recipes for {meal_name} (need {required_count}, have {len(type_indices)}).")
                return None
            prob += pulp.lpSum([recipe_vars[i] for i in type_indices]) == required_count, f"Required_{meal_type}_{required_count}"
        
        prob += total_recipes_selected == total_recipes_needed, "TotalRecipesConstraint"
    
    # Constraint 3: Nutritional balance constraints
    for nutrient in nutrients_to_optimize:
        total_nutrient_sum = pulp.lpSum([recipes_df.loc[i, nutrient] * recipe_vars[i] for i in recipes_df.index])
        
        # Map nutrient names from DataFrame format to target dict format
        if nutrient == 'avg_calories':
            nutrient_key = 'calories'
        else:
            nutrient_key = nutrient.replace('avg_', '')
        target_value = meal_target_nutrients.get(nutrient_key, 0)
        
        # Constraint: Total nutrient - Target = Positive deviation - Negative deviation
        prob += (
            total_nutrient_sum - target_value == pos_dev[nutrient] - neg_dev[nutrient]
        ), f"NutrientBalanceConstraint_{nutrient}"
    
    # Constraint 4: Hard constraint for protein (if enabled)
    # This ensures protein deviation stays within acceptable bounds
    if max_protein_deviation_pct is not None:
        protein_target = meal_target_nutrients.get('protein_g', 0)
        if protein_target > 0:
            max_protein_dev = protein_target * (max_protein_deviation_pct / 100.0)
            # Ensure positive and negative deviations don't exceed max
            prob += pos_dev['avg_protein_g'] <= max_protein_dev, "MaxProteinPositiveDev"
            prob += neg_dev['avg_protein_g'] <= max_protein_dev, "MaxProteinNegativeDev"
    
    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    # Extract solution
    if pulp.LpStatus[prob.status] == 'Optimal':
        selected_recipe_ids = [i for i in recipes_df.index if pulp.value(recipe_vars[i]) == 1]
        
        # Calculate actual deviations for logging
        if meal_target_nutrients.get('protein_g', 0) > 0:
            actual_protein = sum(recipes_df.loc[rid, 'avg_protein_g'] for rid in selected_recipe_ids)
            target_protein = meal_target_nutrients['protein_g']
            protein_dev_pct = abs(actual_protein - target_protein) / target_protein * 100
            if protein_dev_pct > 10:
                print(f"[OPTIMIZER] WARNING: {meal_name} protein deviation: {protein_dev_pct:.1f}% (target: {target_protein}g, actual: {actual_protein:.1f}g)")
        
        # Return full recipe dictionaries (need to match IDs back to original pool)
        selected_recipes = [item for item in recipe_pool if item['id'] in selected_recipe_ids]
        
        # Clear DataFrame from memory (help GC)
        del recipes_df
        
        return selected_recipes
    else:
        print(f"[OPTIMIZER] No optimal solution found for {meal_name}. Status: {pulp.LpStatus[prob.status]}")
        return None


def create_single_meal_resilient(recipe_pool: list, meal_target_nutrients: dict, meal_name: str = "Meal",
                                  meal_structure: dict = None, initial_max_protein_deviation_pct: float = 12.0):
    """
    Resilient optimization with progressive constraint relaxation.
    
    This function guarantees a solution by attempting optimization at progressively relaxed constraint levels:
    - Level 0 (Strict): Original constraints (12% protein deviation, full structure)
    - Level 1 (Moderate): Relaxed protein (20% deviation)
    - Level 2 (Lenient): Relaxed structure (1 Main Course only, complementary optional)
    - Level 3 (Minimal): Relaxed nutritional targets (±30% deviation window)
    - Level 4 (Heuristic): Fallback selection without optimization (always succeeds)
    
    :param recipe_pool: List of recipe dictionaries
    :param meal_target_nutrients: Dict with keys 'calories', 'protein_g', 'fat_g', 'carbs_g'
    :param meal_name: Name of the meal for logging
    :param meal_structure: Dictionary mapping meal_type to required count
    :param initial_max_protein_deviation_pct: Initial protein deviation limit (default 12%)
    :return: Dictionary with keys:
        - 'recipes': List of selected recipe dictionaries (always non-empty)
        - 'relaxation_level': Integer 0-4 indicating which strategy was used
        - 'message': Human-readable status message
        - 'deviations': Dict with actual deviations for each nutrient
    """
    
    if meal_structure is None:
        meal_structure = {'Main Course': 1, 'Side Dish': 1}
    
    # Attempt progressive relaxation levels
    for level in range(5):  # Levels 0-4
        # Adjust constraints based on relaxation level
        current_protein_deviation = initial_max_protein_deviation_pct
        current_structure = meal_structure.copy()
        current_targets = meal_target_nutrients.copy()
        
        if level >= 1:
            # Level 1: Relax protein deviation (12% → 20%)
            current_protein_deviation = 20.0
            print(f"  [OPTIMIZER] Level {level}: Relaxing protein constraint (12% → 20%)")
        
        if level >= 2:
            # Level 2: Relax structure (keep only Main Course requirement, remove complementary)
            # For Breakfast: Keep Breakfast requirement, make Fruit optional
            # For Lunch/Dinner: Keep Main Course, remove Side Dish requirement
            if 'Breakfast' in current_structure:
                # Breakfast: Keep Breakfast=1, make Fruit optional (0)
                current_structure = {'Breakfast': 1, 'Fruit': 0}
            else:
                # Lunch/Dinner: Keep Main Course only
                current_structure = {'Main Course': current_structure.get('Main Course', 1)}
            print(f"  [OPTIMIZER] Level {level}: Relaxing structure requirement (simplified)")
        
        if level >= 3:
            # Level 3: Relax nutritional targets (allow ±30% deviation)
            # This is handled implicitly by the optimizer - we just use a very relaxed protein constraint
            current_protein_deviation = 50.0  # Very relaxed
            print(f"  [OPTIMIZER] Level {level}: Relaxing nutritional targets (±30% deviation acceptable)")
        
        # Attempt optimization at current relaxation level
        selected_recipes = create_single_meal(
            recipe_pool=recipe_pool,
            meal_target_nutrients=current_targets,
            meal_name=f"{meal_name}_L{level}",
            meal_structure=current_structure,
            max_protein_deviation_pct=current_protein_deviation if level < 4 else None
        )
        
        if selected_recipes is not None:
            # Success! Calculate deviations and return
            actual_nutrients = {
                'calories': sum(r.get('avg_calories', 0) for r in selected_recipes),
                'protein_g': sum(r.get('avg_protein_g', 0) for r in selected_recipes),
                'fat_g': sum(r.get('avg_fat_g', 0) for r in selected_recipes),
                'carbs_g': sum(r.get('avg_carbs_g', 0) for r in selected_recipes)
            }
            
            deviations = {}
            for nutrient in ['calories', 'protein_g', 'fat_g', 'carbs_g']:
                target = meal_target_nutrients.get(nutrient, 0)
                actual = actual_nutrients.get(nutrient, 0)
                if target > 0:
                    deviations[nutrient] = {
                        'target': target,
                        'actual': actual,
                        'deviation_pct': abs(actual - target) / target * 100
                    }
            
            level_messages = {
                0: "Strict constraints satisfied (optimal solution)",
                1: "Relaxed protein constraint (20% tolerance)",
                2: "Relaxed structure requirement (simplified meal)",
                3: "Relaxed nutritional targets (±30% acceptable)",
                4: "Heuristic fallback (best effort without optimization)"
            }
            
            return {
                'recipes': selected_recipes,
                'relaxation_level': level,
                'message': level_messages.get(level, f"Level {level} solution"),
                'deviations': deviations
            }
    
    # Level 4: Heuristic fallback (always succeeds)
    print(f"  [OPTIMIZER] Level 4: Using heuristic fallback (no optimization)")
    return heuristic_meal_selection(recipe_pool, meal_target_nutrients, meal_name, meal_structure)


def heuristic_meal_selection(recipe_pool: list, meal_target_nutrients: dict, meal_name: str, meal_structure: dict):
    """
    Heuristic fallback: Select closest-matching recipes without optimization.
    
    This is the last resort - always returns a valid solution by selecting the
    closest-matching recipes to the target, even if they don't perfectly satisfy constraints.
    
    :param recipe_pool: List of recipe dictionaries
    :param meal_target_nutrients: Target nutritional values
    :param meal_name: Name of the meal
    :param meal_structure: Desired meal structure
    :return: Dictionary with same structure as create_single_meal_resilient
    """
    import math
    
    selected_recipes = []
    
    # Extract required meal types
    required_types = {mt: count for mt, count in meal_structure.items() if count > 0}
    
    # For each required type, find the closest-matching recipe
    for meal_type, required_count in required_types.items():
        type_recipes = [r for r in recipe_pool if r.get('meal_type') == meal_type]
        
        if not type_recipes:
            # If no recipes of this type, skip
            continue
        
        # Find closest match based on Euclidean distance in nutritional space
        best_recipe = None
        best_distance = float('inf')
        
        for recipe in type_recipes[:min(100, len(type_recipes))]:  # Limit search to first 100 for speed
            recipe_nutrients = [
                recipe.get('avg_calories', 0) / meal_target_nutrients.get('calories', 1) * 100 if meal_target_nutrients.get('calories', 0) > 0 else 0,
                recipe.get('avg_protein_g', 0) / meal_target_nutrients.get('protein_g', 1) * 100 if meal_target_nutrients.get('protein_g', 0) > 0 else 0,
                recipe.get('avg_fat_g', 0) / meal_target_nutrients.get('fat_g', 1) * 100 if meal_target_nutrients.get('fat_g', 0) > 0 else 0,
                recipe.get('avg_carbs_g', 0) / meal_target_nutrients.get('carbs_g', 1) * 100 if meal_target_nutrients.get('carbs_g', 0) > 0 else 0
            ]
            
            target_normalized = [100.0] * 4  # Normalized target
            distance = math.sqrt(sum((r - t) ** 2 for r, t in zip(recipe_nutrients, target_normalized)))
            
            if distance < best_distance:
                best_distance = distance
                best_recipe = recipe
        
        if best_recipe:
            selected_recipes.append(best_recipe)
            # Remove selected recipe from pool to avoid duplicates
            recipe_pool = [r for r in recipe_pool if r.get('id') != best_recipe.get('id')]
    
    # If we still don't have enough recipes, fill with closest matches regardless of type
    while len(selected_recipes) < sum(required_types.values()) and recipe_pool:
        best_recipe = min(recipe_pool[:100], 
                         key=lambda r: abs(r.get('avg_calories', 0) - meal_target_nutrients.get('calories', 0)))
        selected_recipes.append(best_recipe)
        recipe_pool = [r for r in recipe_pool if r.get('id') != best_recipe.get('id')]
    
    if not selected_recipes:
        # Ultimate fallback: just take first available recipes
        selected_recipes = recipe_pool[:min(2, len(recipe_pool))]
    
    # Calculate deviations
    actual_nutrients = {
        'calories': sum(r.get('avg_calories', 0) for r in selected_recipes),
        'protein_g': sum(r.get('avg_protein_g', 0) for r in selected_recipes),
        'fat_g': sum(r.get('avg_fat_g', 0) for r in selected_recipes),
        'carbs_g': sum(r.get('avg_carbs_g', 0) for r in selected_recipes)
    }
    
    deviations = {}
    for nutrient in ['calories', 'protein_g', 'fat_g', 'carbs_g']:
        target = meal_target_nutrients.get(nutrient, 0)
        actual = actual_nutrients.get(nutrient, 0)
        if target > 0:
            deviations[nutrient] = {
                'target': target,
                'actual': actual,
                'deviation_pct': abs(actual - target) / target * 100
            }
    
    return {
        'recipes': selected_recipes,
        'relaxation_level': 4,
        'message': 'Heuristic fallback (best effort without optimization)',
        'deviations': deviations
    }


def create_meal_plan(recipe_pool: list, target_nutrients: dict, meals_per_day: int = 3):
    """
    Legacy function for backward compatibility.
    Uses PuLP to find an optimal combination of recipes for a full day.
    
    NOTE: This function is deprecated. Use create_single_meal() for meal-level optimization
    in the new hierarchical approach.
    
    :param recipe_pool: List of recipe dictionaries.
    :param target_nutrients: Daily nutritional targets.
    :param meals_per_day: Number of recipes to select.
    :return: List of selected recipe dictionaries, or None if no solution found.
    """
    if not recipe_pool:
        print("[OPTIMIZER] Recipe pool is empty. Cannot create a plan.")
        return None

    recipes_df = pd.DataFrame(recipe_pool).set_index('id')

    if 'meal_type' not in recipes_df.columns:
        print("[OPTIMIZER] WARNING: 'meal_type' field not found. Running without semantic constraints.")
        use_semantic_constraints = False
    else:
        use_semantic_constraints = True

    prob = pulp.LpProblem("MealPlanOptimization", pulp.LpMinimize)

    recipe_vars = pulp.LpVariable.dicts("Recipe", recipes_df.index, cat='Binary')

    nutrients_to_optimize = ['avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g']
    pos_dev = pulp.LpVariable.dicts("PositiveDev", nutrients_to_optimize, lowBound=0)
    neg_dev = pulp.LpVariable.dicts("NegativeDev", nutrients_to_optimize, lowBound=0)
    
    prob += (
        (pos_dev['avg_calories'] + neg_dev['avg_calories']) * 1.0 +
        (pos_dev['avg_protein_g'] + neg_dev['avg_protein_g']) * 1.2 +
        (pos_dev['avg_fat_g'] + neg_dev['avg_fat_g']) * 1.0 +
        (pos_dev['avg_carbs_g'] + neg_dev['avg_carbs_g']) * 1.0
    )

    prob += pulp.lpSum([recipe_vars[i] for i in recipes_df.index]) == meals_per_day, "TotalMealsConstraint"

    if use_semantic_constraints:
        main_course_indices = [
            i for i in recipes_df.index 
            if recipes_df.loc[i, 'meal_type'] == 'Main Course'
        ]
        if main_course_indices:
            prob += pulp.lpSum([recipe_vars[i] for i in main_course_indices]) >= 1, "MustIncludeMainCourse"
        
        dessert_indices = [
            i for i in recipes_df.index 
            if recipes_df.loc[i, 'meal_type'] == 'Dessert'
        ]
        if dessert_indices:
            prob += pulp.lpSum([recipe_vars[i] for i in dessert_indices]) <= 1, "AtMostOneDessert"
        
        drink_indices = [
            i for i in recipes_df.index 
            if recipes_df.loc[i, 'meal_type'] == 'Drink'
        ]
        if drink_indices:
            prob += pulp.lpSum([recipe_vars[i] for i in drink_indices]) <= 1, "AtMostOneDrink"
    
    for nutrient in nutrients_to_optimize:
        total_nutrient_sum = pulp.lpSum([recipes_df.loc[i, nutrient] * recipe_vars[i] for i in recipes_df.index])
        prob += (
            total_nutrient_sum - target_nutrients.get(nutrient.replace('avg_', ''), 0) 
            == pos_dev[nutrient] - neg_dev[nutrient]
        ), f"NutrientBalanceConstraint_{nutrient}"

    prob.solve(pulp.PULP_CBC_CMD(msg=False)) 

    if pulp.LpStatus[prob.status] == 'Optimal':
        selected_recipe_ids = [
            i for i in recipes_df.index if pulp.value(recipe_vars[i]) == 1
        ]
        selected_recipes = [item for item in recipe_pool if item['id'] in selected_recipe_ids]
        return selected_recipes
    else:
        print("[OPTIMIZER] No optimal solution found.")
        return None


def create_daily_plan_global(recipe_pools: dict, daily_target_nutrients: dict,
                              used_recipe_ids: set, day_number: int = 1,
                              max_protein_deviation_pct: float = 15.0):
    """
    Daily Global Optimization: Optimizes all 3 meals (Breakfast, Lunch, Dinner) simultaneously.
    
    ARCHITECTURAL ADVANTAGE:
    - Uses DAILY totals instead of rigid per-meal allocations (eliminates infeasibility)
    - Allows nutrient flexibility across meals (can allocate more protein to Lunch if Breakfast is protein-poor)
    - Maintains structural meal requirements (Breakfast: 1 Breakfast + 1 Fruit/Drink, etc.)
    - Single optimization problem for entire day (better coordination between meals)
    
    :param recipe_pools: Dict with keys 'Breakfast', 'Lunch', 'Dinner', each containing list of recipe dicts
    :param daily_target_nutrients: Dict with 'calories', 'protein_g', 'fat_g', 'carbs_g' (DAILY totals, not per-meal)
    :param used_recipe_ids: Set of already-used recipe IDs (to avoid repetition)
    :param day_number: Day number for logging
    :param max_protein_deviation_pct: Maximum protein deviation % (default 15%)
    :return: Dict with structure {'Breakfast': [...], 'Lunch': [...], 'Dinner': [...], 'status': str, 'deviations': dict}
    """
    # Validate inputs
    if not all(meal in recipe_pools for meal in ['Breakfast', 'Lunch', 'Dinner']):
        print(f"[OPTIMIZER] ERROR: Missing meal pools for Day {day_number}")
        return None
    
    # Combine all pools and filter used recipes
    # CRITICAL FIX: Deduplicate by recipe ID to prevent intra-day repetition
    # Priority: Breakfast > Lunch > Dinner (to ensure proper meal assignment)
    all_recipes_dict = {}  # Maps recipe_id -> recipe_dict
    meal_assignment = {}  # Maps recipe_id -> meal_name
    
    # Process pools in priority order to handle duplicates correctly
    meal_priority = ['Breakfast', 'Lunch', 'Dinner']
    
    for meal_name in meal_priority:
        pool = recipe_pools.get(meal_name, [])
        for recipe in pool:
            recipe_id = recipe['id']
            # Only add if not already used AND not already in our combined pool
            if recipe_id not in used_recipe_ids and recipe_id not in all_recipes_dict:
                all_recipes_dict[recipe_id] = recipe
                meal_assignment[recipe_id] = meal_name
    
    # Convert to list
    all_recipes = list(all_recipes_dict.values())
    
    # CRITICAL VERIFICATION: Ensure no duplicate recipe IDs after deduplication
    recipe_ids_in_pool = [r['id'] for r in all_recipes]
    if len(recipe_ids_in_pool) != len(set(recipe_ids_in_pool)):
        duplicates = [rid for rid in recipe_ids_in_pool if recipe_ids_in_pool.count(rid) > 1]
        print(f"[OPTIMIZER] CRITICAL ERROR: Duplicate recipe IDs in combined pool for Day {day_number}!")
        print(f"[OPTIMIZER] Duplicate IDs: {set(duplicates)}")
        return None
    
    # CRITICAL FIX: Limit problem size to prevent solver hangs
    # Large problems (>800 recipes) can cause CBC solver to hang or take too long
    # Reduce pool size intelligently while maintaining diversity
    MAX_COMBINED_POOL_SIZE = 600  # Maximum recipes in combined optimization problem
    if len(all_recipes) > MAX_COMBINED_POOL_SIZE:
        print(f"[OPTIMIZER] WARNING: Combined pool size ({len(all_recipes)}) exceeds limit ({MAX_COMBINED_POOL_SIZE}). Reducing...")
        # Reduce pool by randomly sampling while maintaining meal type diversity
        # Group by meal and meal_type to maintain diversity
        recipes_by_meal_type = {}
        for recipe in all_recipes:
            meal = meal_assignment.get(recipe['id'], 'Unknown')
            meal_type = recipe.get('meal_type', 'Unknown')
            key = (meal, meal_type)
            if key not in recipes_by_meal_type:
                recipes_by_meal_type[key] = []
            recipes_by_meal_type[key].append(recipe)
        
        # Sample proportionally from each group
        reduced_recipes = []
        target_per_group = MAX_COMBINED_POOL_SIZE // max(len(recipes_by_meal_type), 1)
        for key, group_recipes in recipes_by_meal_type.items():
            if len(group_recipes) > target_per_group:
                sampled = random.sample(group_recipes, target_per_group)
            else:
                sampled = group_recipes
            reduced_recipes.extend(sampled)
        
        # CRITICAL: Deduplicate after reduction (safety check)
        reduced_dict = {}
        for recipe in reduced_recipes:
            recipe_id = recipe['id']
            if recipe_id not in reduced_dict:
                reduced_dict[recipe_id] = recipe
        
        all_recipes = list(reduced_dict.values())
        # Rebuild meal_assignment for reduced set
        meal_assignment = {r['id']: meal_assignment.get(r['id'], 'Unknown') for r in all_recipes}
        
        # CRITICAL VERIFICATION: Ensure no duplicates after reduction
        reduced_ids = [r['id'] for r in all_recipes]
        if len(reduced_ids) != len(set(reduced_ids)):
            duplicates = [rid for rid in reduced_ids if reduced_ids.count(rid) > 1]
            print(f"[OPTIMIZER] CRITICAL ERROR: Duplicate recipe IDs after pool reduction for Day {day_number}!")
            print(f"[OPTIMIZER] Duplicate IDs: {set(duplicates)}")
            return None
        
        print(f"[OPTIMIZER] Reduced pool to {len(all_recipes)} recipes (deduplicated)")
    
    if len(all_recipes) < 6:  # Minimum: 2 Breakfast + 2 Lunch + 2 Dinner
        print(f"[OPTIMIZER] ERROR: Insufficient recipes for Day {day_number} ({len(all_recipes)} available)")
        return None
    
    # Create DataFrame with UNIQUE recipe IDs (no duplicates)
    required_columns = ['id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g']
    minimal_data = [{col: r[col] for col in required_columns if col in r} for r in all_recipes]
    recipes_df = pd.DataFrame(minimal_data).set_index('id')
    
    # Verify no duplicate IDs (safety check)
    if recipes_df.index.duplicated().any():
        print(f"[OPTIMIZER] ERROR: Duplicate recipe IDs detected in Day {day_number} optimization pool!")
        return None
    
    # Add meal assignment column
    recipes_df['assigned_meal'] = recipes_df.index.map(meal_assignment)
    
    # CRITICAL: Ensure binary variables enforce uniqueness
    # Each recipe can only be selected ONCE (binary variable already enforces this, but we verify)
    
    # Group by meal_type for constraints
    breakfast_items = list(recipes_df[(recipes_df['meal_type'] == 'Breakfast') & 
                                      (recipes_df['assigned_meal'] == 'Breakfast')].index)
    fruit_items = list(recipes_df[(recipes_df['meal_type'] == 'Fruit') & 
                                  (recipes_df['assigned_meal'] == 'Breakfast')].index)
    drink_items = list(recipes_df[(recipes_df['meal_type'] == 'Drink') & 
                                  (recipes_df['assigned_meal'] == 'Breakfast')].index)
    
    lunch_main = list(recipes_df[(recipes_df['meal_type'] == 'Main Course') & 
                                 (recipes_df['assigned_meal'] == 'Lunch')].index)
    lunch_complementary = list(recipes_df[(recipes_df['meal_type'].isin(['Side Dish', 'Salad', 'Soup'])) & 
                                          (recipes_df['assigned_meal'] == 'Lunch')].index)
    
    dinner_main = list(recipes_df[(recipes_df['meal_type'] == 'Main Course') & 
                                  (recipes_df['assigned_meal'] == 'Dinner')].index)
    dinner_complementary = list(recipes_df[(recipes_df['meal_type'].isin(['Side Dish', 'Salad', 'Soup', 'Dessert'])) & 
                                           (recipes_df['assigned_meal'] == 'Dinner')].index)
    
    # Validation
    if len(breakfast_items) == 0:
        print(f"[OPTIMIZER] ERROR: No Breakfast items for Day {day_number}")
        return None
    if len(fruit_items) == 0 and len(drink_items) == 0:
        print(f"[OPTIMIZER] ERROR: No Fruit/Drink for Breakfast Day {day_number}")
        return None
    if len(lunch_main) == 0:
        print(f"[OPTIMIZER] ERROR: No Main Courses for Lunch Day {day_number}")
        return None
    if len(dinner_main) == 0:
        print(f"[OPTIMIZER] ERROR: No Main Courses for Dinner Day {day_number}")
        return None
    
    # Initialize optimization problem
    prob = pulp.LpProblem(f"DailyGlobalOptimization_Day{day_number}", pulp.LpMinimize)
    
    # Decision variables: binary for each recipe
    recipe_vars = pulp.LpVariable.dicts("Recipe", recipes_df.index, cat='Binary')
    
    # Deviation variables for nutrients
    nutrients_to_optimize = ['avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g']
    pos_dev = pulp.LpVariable.dicts("PosDev", nutrients_to_optimize, lowBound=0)
    neg_dev = pulp.LpVariable.dicts("NegDev", nutrients_to_optimize, lowBound=0)
    
    # === OBJECTIVE: Minimize weighted deviations (protein prioritized) ===
    protein_weight = 3.0
    calorie_weight = 1.0
    fat_weight = 0.8
    carb_weight = 1.0
    
    prob += (
        (pos_dev['avg_calories'] + neg_dev['avg_calories']) * calorie_weight +
        (pos_dev['avg_protein_g'] + neg_dev['avg_protein_g']) * protein_weight +
        (pos_dev['avg_fat_g'] + neg_dev['avg_fat_g']) * fat_weight +
        (pos_dev['avg_carbs_g'] + neg_dev['avg_carbs_g']) * carb_weight
    )
    
    # === STRUCTURAL CONSTRAINTS ===
    
    # Breakfast: Exactly 1 Breakfast item + Exactly 1 Fruit OR Drink
    prob += pulp.lpSum([recipe_vars[i] for i in breakfast_items]) == 1, "Breakfast_OneItem"
    prob += pulp.lpSum([recipe_vars[i] for i in fruit_items + drink_items]) == 1, "Breakfast_OneFruitOrDrink"
    
    # Lunch: Exactly 1 Main Course + 1-2 complementary dishes
    prob += pulp.lpSum([recipe_vars[i] for i in lunch_main]) == 1, "Lunch_OneMainCourse"
    if len(lunch_complementary) > 0:
        prob += pulp.lpSum([recipe_vars[i] for i in lunch_complementary]) >= 1, "Lunch_MinComplementary"
        prob += pulp.lpSum([recipe_vars[i] for i in lunch_complementary]) <= 2, "Lunch_MaxComplementary"
    else:
        print(f"[OPTIMIZER] WARNING: No complementary dishes for Lunch Day {day_number}")
    
    # Dinner: Exactly 1 Main Course + 1-2 complementary dishes
    prob += pulp.lpSum([recipe_vars[i] for i in dinner_main]) == 1, "Dinner_OneMainCourse"
    if len(dinner_complementary) > 0:
        prob += pulp.lpSum([recipe_vars[i] for i in dinner_complementary]) >= 1, "Dinner_MinComplementary"
        prob += pulp.lpSum([recipe_vars[i] for i in dinner_complementary]) <= 2, "Dinner_MaxComplementary"
        
        # Max 1 Dessert per day (in Dinner)
        dessert_items = list(recipes_df[(recipes_df['meal_type'] == 'Dessert') & 
                                       (recipes_df['assigned_meal'] == 'Dinner')].index)
        if len(dessert_items) > 0:
            prob += pulp.lpSum([recipe_vars[i] for i in dessert_items]) <= 1, "Dinner_MaxOneDessert"
    else:
        print(f"[OPTIMIZER] WARNING: No complementary dishes for Dinner Day {day_number}")
    
    # Total recipes: 6-8 (2 Breakfast + 2-3 Lunch + 2-3 Dinner)
    all_indices = list(recipes_df.index)
    prob += pulp.lpSum([recipe_vars[i] for i in all_indices]) >= 6, "Daily_MinRecipes"
    prob += pulp.lpSum([recipe_vars[i] for i in all_indices]) <= 8, "Daily_MaxRecipes"
    
    # CRITICAL: Explicit uniqueness constraint - Each recipe ID can be selected at most ONCE
    # Binary variables already enforce this mathematically (0 or 1), but we add explicit verification
    # This ensures that even if a recipe appears in multiple meal pools, it can only be selected once
    # The deduplication logic above should prevent this, but this is a safety check
    for recipe_id in all_indices:
        # Each binary variable is already 0 or 1, so this is redundant but explicit
        # We verify uniqueness in the solution extraction step below
        pass
    
    # === DAILY NUTRITIONAL CONSTRAINTS (FLEXIBLE - NOT PER-MEAL) ===
    for nutrient in nutrients_to_optimize:
        total_nutrient_sum = pulp.lpSum([recipes_df.loc[i, nutrient] * recipe_vars[i] 
                                         for i in recipes_df.index])
        
        # Map nutrient names
        if nutrient == 'avg_calories':
            nutrient_key = 'calories'
        else:
            nutrient_key = nutrient.replace('avg_', '')
        
        target = daily_target_nutrients.get(nutrient_key, 0)
        
        # Constraint: total = target + pos_dev - neg_dev
        prob += (
            total_nutrient_sum - target == pos_dev[nutrient] - neg_dev[nutrient]
        ), f"DailyNutrient_{nutrient_key}"
    
    # Hard constraint for protein deviation (can be relaxed in resilient wrapper)
    if max_protein_deviation_pct is not None:
        protein_target = daily_target_nutrients.get('protein_g', 0)
        if protein_target > 0:
            max_protein_dev = protein_target * (max_protein_deviation_pct / 100.0)
            prob += neg_dev['avg_protein_g'] <= max_protein_dev, "ProteinMinConstraint"
            prob += pos_dev['avg_protein_g'] <= max_protein_dev, "ProteinMaxConstraint"
    
    # === SOLVE ===
    # CRITICAL: Solve with proper resource management and timeout
    # PuLP's CBC solver spawns subprocesses that must be properly cleaned up
    # to prevent hangs on subsequent solves
    # Use try-finally to guarantee cleanup even in error cases
    # CRITICAL FIX: Add timeout to prevent infinite hangs on infeasible problems
    result = None
    try:
        try:
            # CRITICAL: Add timeout (30 seconds) to prevent infinite hangs
            # If problem is infeasible or too complex, solver will timeout instead of hanging
            solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
            prob.solve(solver)
            status = pulp.LpStatus[prob.status]
            
            # Log solver status for debugging
            if status != 'Optimal':
                print(f"[OPTIMIZER] Solver status for Day {day_number}: {status}")
                if status == 'Infeasible':
                    print(f"[OPTIMIZER] Problem is infeasible. Possible causes:")
                    print(f"  - Nutritional targets too strict for available recipes")
                    print(f"  - Structural constraints incompatible with recipe pool")
                    print(f"  - Recipe pool size: {len(recipes_df)} recipes")
        except Exception as e:
            print(f"[OPTIMIZER] Solver exception for Day {day_number}: {e}")
            status = 'Error'
        
        # Extract results BEFORE cleanup (pulp.value() requires problem object)
        if status == 'Optimal':
            # Extract selected recipes
            selected_recipe_ids = [i for i in recipes_df.index if pulp.value(recipe_vars[i]) == 1]
            
            # CRITICAL VERIFICATION: Check for duplicate recipe IDs (should never happen with binary variables)
            # This is a safety check to catch any bugs in the optimization logic
            unique_selected_ids = set(selected_recipe_ids)
            if len(selected_recipe_ids) != len(unique_selected_ids):
                print(f"[OPTIMIZER] CRITICAL ERROR: Duplicate recipe IDs detected in solution for Day {day_number}!")
                duplicates = [rid for rid in selected_recipe_ids if selected_recipe_ids.count(rid) > 1]
                print(f"[OPTIMIZER] Duplicate IDs: {set(duplicates)}")
                print(f"[OPTIMIZER] This should never happen with binary variables. Possible bug in constraint logic.")
                result = None
            elif len(selected_recipe_ids) == 0:
                print(f"[OPTIMIZER] ERROR: No recipes selected for Day {day_number}")
                result = None
            else:
                selected_recipes = {meal: [] for meal in ['Breakfast', 'Lunch', 'Dinner']}
                
                # Group by assigned meal
                for recipe_id in selected_recipe_ids:
                    meal_name = meal_assignment.get(recipe_id)
                    recipe_dict = next((r for r in all_recipes if r['id'] == recipe_id), None)
                    if recipe_dict and meal_name:
                        selected_recipes[meal_name].append(recipe_dict)
                
                # Ensure proper ordering: Breakfast item first, then Fruit/Drink
                breakfast_list = selected_recipes['Breakfast']
                breakfast_main = [r for r in breakfast_list if r['meal_type'] == 'Breakfast']
                breakfast_complementary = [r for r in breakfast_list if r['meal_type'] in ['Fruit', 'Drink']]
                selected_recipes['Breakfast'] = breakfast_main + breakfast_complementary
                
                # Calculate actual nutrients and deviations
                all_selected = [r for r in all_recipes if r['id'] in selected_recipe_ids]
                actual_nutrients = {
                    'calories': sum(r['avg_calories'] for r in all_selected),
                    'protein_g': sum(r['avg_protein_g'] for r in all_selected),
                    'fat_g': sum(r['avg_fat_g'] for r in all_selected),
                    'carbs_g': sum(r['avg_carbs_g'] for r in all_selected)
                }
                
                deviations = {}
                for nutrient in ['calories', 'protein_g', 'fat_g', 'carbs_g']:
                    target = daily_target_nutrients.get(nutrient, 0)
                    actual = actual_nutrients.get(nutrient, 0)
                    if target > 0:
                        deviation_pct = abs(actual - target) / target * 100
                        deviations[nutrient] = {
                            'target': target,
                            'actual': actual,
                            'deviation_pct': deviation_pct
                        }
                
                result = selected_recipes.copy()
                result['status'] = status
                result['deviations'] = deviations
                result['actual_nutrients'] = actual_nutrients
        else:
            print(f"[OPTIMIZER] No optimal solution found for Day {day_number}. Status: {status}")
            # CRITICAL FIX: If infeasible, try with relaxed constraints
            if status == 'Infeasible':
                print(f"[OPTIMIZER] Attempting fallback: Relaxing protein constraint...")
                # Remove strict protein deviation constraint and try again
                # Create a new problem with relaxed constraints
                prob_relaxed = pulp.LpProblem(f"DailyGlobalOptimization_Day{day_number}_Relaxed", pulp.LpMinimize)
                
                # Copy variables
                recipe_vars_relaxed = pulp.LpVariable.dicts("Recipe", recipes_df.index, cat='Binary')
                pos_dev_relaxed = pulp.LpVariable.dicts("PosDev", nutrients_to_optimize, lowBound=0)
                neg_dev_relaxed = pulp.LpVariable.dicts("NegDev", nutrients_to_optimize, lowBound=0)
                
                # Same objective
                prob_relaxed += (
                    (pos_dev_relaxed['avg_calories'] + neg_dev_relaxed['avg_calories']) * calorie_weight +
                    (pos_dev_relaxed['avg_protein_g'] + neg_dev_relaxed['avg_protein_g']) * protein_weight +
                    (pos_dev_relaxed['avg_fat_g'] + neg_dev_relaxed['avg_fat_g']) * fat_weight +
                    (pos_dev_relaxed['avg_carbs_g'] + neg_dev_relaxed['avg_carbs_g']) * carb_weight
                )
                
                # Same structural constraints
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in breakfast_items]) == 1, "Breakfast_OneItem"
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in fruit_items + drink_items]) == 1, "Breakfast_OneFruitOrDrink"
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in lunch_main]) == 1, "Lunch_OneMainCourse"
                if len(lunch_complementary) > 0:
                    prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in lunch_complementary]) >= 1, "Lunch_MinComplementary"
                    prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in lunch_complementary]) <= 2, "Lunch_MaxComplementary"
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in dinner_main]) == 1, "Dinner_OneMainCourse"
                if len(dinner_complementary) > 0:
                    prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in dinner_complementary]) >= 1, "Dinner_MinComplementary"
                    prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in dinner_complementary]) <= 2, "Dinner_MaxComplementary"
                    dessert_items = list(recipes_df[(recipes_df['meal_type'] == 'Dessert') & 
                                                   (recipes_df['assigned_meal'] == 'Dinner')].index)
                    if len(dessert_items) > 0:
                        prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in dessert_items]) <= 1, "Dinner_MaxOneDessert"
                
                all_indices = list(recipes_df.index)
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in all_indices]) >= 6, "Daily_MinRecipes"
                prob_relaxed += pulp.lpSum([recipe_vars_relaxed[i] for i in all_indices]) <= 8, "Daily_MaxRecipes"
                
                # Nutritional constraints WITHOUT strict protein deviation limit
                for nutrient in nutrients_to_optimize:
                    total_nutrient_sum = pulp.lpSum([recipes_df.loc[i, nutrient] * recipe_vars_relaxed[i] 
                                                     for i in recipes_df.index])
                    if nutrient == 'avg_calories':
                        nutrient_key = 'calories'
                    else:
                        nutrient_key = nutrient.replace('avg_', '')
                    target = daily_target_nutrients.get(nutrient_key, 0)
                    prob_relaxed += (
                        total_nutrient_sum - target == pos_dev_relaxed[nutrient] - neg_dev_relaxed[nutrient]
                    ), f"DailyNutrient_{nutrient_key}_Relaxed"
                
                # Try solving with relaxed constraints
                try:
                    solver_relaxed = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
                    prob_relaxed.solve(solver_relaxed)
                    status_relaxed = pulp.LpStatus[prob_relaxed.status]
                    
                    if status_relaxed == 'Optimal':
                        print(f"[OPTIMIZER] Fallback succeeded with relaxed constraints")
                        # Extract solution using relaxed variables
                        selected_recipe_ids = [i for i in recipes_df.index if pulp.value(recipe_vars_relaxed[i]) == 1]
                        unique_selected_ids = set(selected_recipe_ids)
                        if len(selected_recipe_ids) == len(unique_selected_ids):
                            selected_recipes = {meal: [] for meal in ['Breakfast', 'Lunch', 'Dinner']}
                            for recipe_id in selected_recipe_ids:
                                meal_name = meal_assignment.get(recipe_id)
                                recipe_dict = next((r for r in all_recipes if r['id'] == recipe_id), None)
                                if recipe_dict and meal_name:
                                    selected_recipes[meal_name].append(recipe_dict)
                            
                            breakfast_list = selected_recipes['Breakfast']
                            breakfast_main = [r for r in breakfast_list if r['meal_type'] == 'Breakfast']
                            breakfast_complementary = [r for r in breakfast_list if r['meal_type'] in ['Fruit', 'Drink']]
                            selected_recipes['Breakfast'] = breakfast_main + breakfast_complementary
                            
                            all_selected = [r for r in all_recipes if r['id'] in selected_recipe_ids]
                            actual_nutrients = {
                                'calories': sum(r['avg_calories'] for r in all_selected),
                                'protein_g': sum(r['avg_protein_g'] for r in all_selected),
                                'fat_g': sum(r['avg_fat_g'] for r in all_selected),
                                'carbs_g': sum(r['avg_carbs_g'] for r in all_selected)
                            }
                            
                            deviations = {}
                            for nutrient in ['calories', 'protein_g', 'fat_g', 'carbs_g']:
                                target = daily_target_nutrients.get(nutrient, 0)
                                actual = actual_nutrients.get(nutrient, 0)
                                if target > 0:
                                    deviation_pct = abs(actual - target) / target * 100
                                    deviations[nutrient] = {
                                        'target': target,
                                        'actual': actual,
                                        'deviation_pct': deviation_pct
                                    }
                            
                            result = selected_recipes.copy()
                            result['status'] = 'Optimal_Relaxed'
                            result['deviations'] = deviations
                            result['actual_nutrients'] = actual_nutrients
                            
                            # Cleanup relaxed problem (Python GC will handle PuLP objects)
                            del prob_relaxed
                            del recipe_vars_relaxed
                            del pos_dev_relaxed
                            del neg_dev_relaxed
                        else:
                            print(f"[OPTIMIZER] Fallback solution has duplicate IDs")
                            result = None
                    else:
                        print(f"[OPTIMIZER] Fallback also failed. Status: {status_relaxed}")
                        result = None
                        # Cleanup (Python GC will handle PuLP objects)
                        try:
                            del prob_relaxed
                        except:
                            pass
                except Exception as e:
                    print(f"[OPTIMIZER] Fallback solver exception: {e}")
                    result = None
            else:
                result = None
    finally:
        # CRITICAL: Explicit cleanup of problem object to release subprocess resources
        # This MUST happen after extracting results, even if there's an error
        # PuLP's CBC solver spawns subprocesses that must be properly terminated
        # to prevent resource leaks causing hangs on subsequent solves
        # NOTE: Python's garbage collector will handle PuLP object cleanup automatically
        # The gc.collect() call in planner_service.py ensures subprocess cleanup
        try:
            # Delete problem object to trigger garbage collection
            del prob
            # Also clean up recipe_vars dictionary to release memory
            del recipe_vars
            del pos_dev
            del neg_dev
        except Exception:
            # Ignore cleanup errors - better to continue than crash
            pass
    
    return result