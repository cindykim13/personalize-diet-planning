# planner/planner_service.py

from .models import Recipe
from .ai_service import MealPlannerService
from .optimization_service import create_daily_plan_global
from django.db.models import Q
import random

# Define only the fields needed for optimization to minimize memory usage
OPTIMIZATION_FIELDS = [
    'id', 'name', 'meal_type',
    'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
]

# Define meal structure requirements (meal_type: count)
# This specifies exactly what types and quantities are required for each meal
MEAL_STRUCTURES = {
    'Breakfast': {
        'Breakfast': 1,      # Must have exactly 1 breakfast-specific item
        'Fruit': 0,          # Optional (can be Fruit OR Drink)
        'Drink': 0           # Optional (can be Fruit OR Drink)
        # Note: At least one of Fruit or Drink is required (handled in optimizer)
    },
    'Lunch': {
        'Main Course': 1,    # Must have exactly 1 main course
        'Side Dish': 0,      # Optional (1-2 complementary dishes allowed)
        'Salad': 0,          # Optional (1-2 complementary dishes allowed)
        'Soup': 0            # Optional (1-2 complementary dishes allowed)
        # Note: At least 1, at most 2 complementary dishes (handled in optimizer)
    },
    'Dinner': {
        'Main Course': 1,    # Must have exactly 1 main course
        'Side Dish': 0,      # Optional (1-2 complementary dishes allowed)
        'Salad': 0,          # Optional (1-2 complementary dishes allowed)
        'Soup': 0,           # Optional (1-2 complementary dishes allowed)
        'Dessert': 0         # Optional (max 1 per day, handled at daily level)
        # Note: At least 1, at most 2 complementary dishes (handled in optimizer)
    }
}


def get_meal_structure(meal_name: str) -> dict:
    """
    Returns the meal structure requirements for a specific meal.
    
    This defines the exact composition rules based on real-world eating patterns:
    - Breakfast: 1 Breakfast item + 1 Fruit (or Drink)
    - Lunch: 1 Main Course + 1 Side Dish (flexible complementary)
    - Dinner: 1 Main Course + 1 Side Dish (with optional Salad/Soup/Dessert)
    
    :param meal_name: Name of the meal ('Breakfast', 'Lunch', or 'Dinner')
    :return: Dictionary mapping meal_type to required count (0 = optional)
    """
    return MEAL_STRUCTURES.get(meal_name, {'Main Course': 1, 'Side Dish': 1})


def get_meal_complementary_rules(meal_name: str) -> list:
    """
    DEPRECATED: Use get_meal_structure() instead.
    
    Returns the allowed complementary dish types for a specific meal.
    Kept for backward compatibility but should not be used in new code.
    
    :param meal_name: Name of the meal ('Breakfast', 'Lunch', or 'Dinner')
    :return: List of allowed complementary meal types
    """
    meal_rules = {
        'Breakfast': ['Side', 'Side Dish', 'Salad', 'Fruit'],
        'Lunch': ['Side', 'Side Dish', 'Salad', 'Soup'],
        'Dinner': ['Side', 'Side Dish', 'Salad', 'Soup']
    }
    return meal_rules.get(meal_name, ['Side', 'Side Dish', 'Salad', 'Soup'])


def check_vegetable_inclusion(recipes: list) -> bool:
    """
    Checks if a meal includes a vegetable-based dish (Side, Salad, or Soup with vegetable focus).
    
    :param recipes: List of recipe dictionaries
    :return: True if meal includes a vegetable-based complementary dish
    """
    vegetable_types = ['Side', 'Side Dish', 'Salad', 'Soup']
    return any(r.get('meal_type') in vegetable_types for r in recipes)


def construct_funnel_pool(meal_name: str, meal_structure: dict, primary_cluster: int,
                           meal_target_nutrients: dict, used_recipe_ids: set,
                           max_pool_size: int = 500) -> list:
    """
    Multi-Stage Funnel Filtering: Constructs a diverse yet bounded recipe pool for optimization.
    
    PERFORMANCE-OPTIMIZED STRATEGY:
    1. Coarse filtering: Build lazy QuerySets filtered by cluster and used recipes
    2. Stratified guaranteed fetching: Fetch fixed, limited samples per meal_type
    3. Pool construction: Combine samples with strict size cap
    4. Result: Diverse pool (300-500 recipes) that's computationally tractable
    
    This eliminates computational explosion while maintaining solution quality.
    
    :param meal_name: Name of the meal ('Breakfast', 'Lunch', 'Dinner')
    :param meal_structure: Dictionary mapping meal_type to required count
    :param primary_cluster: Primary predicted cluster ID (e.g., 3 for High-Protein)
    :param meal_target_nutrients: Target nutritional values (for future prioritization)
    :param used_recipe_ids: Set of already-used recipe IDs (to avoid repetition)
    :param max_pool_size: Maximum total recipes in pool (default 500)
    :return: List of recipe dictionaries with OPTIMIZATION_FIELDS
    """
    # Define stratified sampling limits per meal_type (justified in strategy doc)
    # These limits ensure diversity while keeping pool size manageable
    STRATIFIED_LIMITS = {
        'Breakfast': {
            'Breakfast': 150,  # Primary: breakfast items
            'Fruit': 100,      # Complementary option 1
            'Drink': 100       # Complementary option 2
        },
        'Lunch': {
            'Main Course': 200,  # Primary: main courses (needs most variety)
            'Side Dish': 200,    # Most common complementary
            'Salad': 100,        # Alternative complementary
            'Soup': 100          # Alternative complementary
        },
        'Dinner': {
            'Main Course': 200,  # Primary: main courses
            'Side Dish': 200,    # Most common complementary
            'Salad': 100,        # Alternative complementary
            'Soup': 100,         # Alternative complementary
            'Dessert': 50        # Optional dessert (rare, smaller sample)
        }
    }
    
    # Get meal-specific limits
    meal_limits = STRATIFIED_LIMITS.get(meal_name, {
        'Main Course': 200,
        'Side Dish': 200,
        'Salad': 100,
        'Soup': 100
    })
    
    # Determine which meal_types to fetch (from structure: required or optional)
    # For flexible structures (Fruit OR Drink, Side OR Salad OR Soup), fetch all options
    meal_types_to_fetch = [mt for mt in meal_structure.keys() if meal_limits.get(mt, 0) > 0]
    
    pool = []
    type_counts = {}
    
    # STAGE 1: Coarse filtering - Build base queryset (lazy, not evaluated)
    base_queryset = Recipe.objects.filter(
        cluster=primary_cluster  # Start with primary cluster
    ).exclude(
        id__in=used_recipe_ids
    ).exclude(
        meal_type='Unknown'
    )
    
    # STAGE 2: Stratified guaranteed fetching
    # For each meal_type, fetch a fixed, limited sample from primary cluster
    print(f"  [POOL] Stage 2: Stratified fetching from cluster {primary_cluster}")
    
    for meal_type in meal_types_to_fetch:
        limit = meal_limits.get(meal_type, 0)
        if limit == 0:
            continue
        
        # Query for this specific meal_type (still lazy)
        type_qs = base_queryset.filter(meal_type=meal_type)
        
        # Check availability
        available = type_qs.count()
        
        if available == 0:
            print(f"  [POOL] WARNING: No '{meal_type}' recipes in primary cluster {primary_cluster}")
            # Try expanding to all clusters for this type
            expanded_qs = Recipe.objects.exclude(
                id__in=used_recipe_ids
            ).exclude(
                meal_type='Unknown'
            ).filter(meal_type=meal_type)
            
            expanded_available = expanded_qs.count()
            if expanded_available > 0:
                print(f"  [POOL] Expanding '{meal_type}' search to all clusters ({expanded_available} available)")
                type_qs = expanded_qs
                available = expanded_available
            else:
                print(f"  [POOL] ERROR: No '{meal_type}' recipes available at all")
                continue
        
        # Fetch limited sample (stratified sampling)
        sample_size = min(limit, available)
        type_recipes = list(
            type_qs.order_by('?').values(*OPTIMIZATION_FIELDS)[:sample_size]
        )
        
        pool.extend(type_recipes)
        type_counts[meal_type] = len(type_recipes)
        print(f"  [POOL] Fetched {len(type_recipes)} '{meal_type}' recipes (limit: {limit}, available: {available})")
    
    # STAGE 3: Pool construction with size cap
    # Ensure pool doesn't exceed max_pool_size (trim if necessary, prioritizing required types)
    if len(pool) > max_pool_size:
        print(f"  [POOL] Pool size {len(pool)} exceeds limit {max_pool_size}, trimming...")
        # Keep all required types, trim optional types proportionally
        required_types = {mt: count for mt, count in meal_structure.items() if count > 0}
        
        required_recipes = []
        optional_recipes = []
        
        for recipe in pool:
            if recipe.get('meal_type') in required_types:
                required_recipes.append(recipe)
            else:
                optional_recipes.append(recipe)
        
        # Calculate how many optional recipes we can keep
        remaining_slots = max_pool_size - len(required_recipes)
        
        if remaining_slots > 0:
            # Keep proportionally from optional recipes
            optional_keep = optional_recipes[:remaining_slots]
            pool = required_recipes + optional_keep
        else:
            # Keep only required (shouldn't happen with proper limits)
            pool = required_recipes
        
        print(f"  [POOL] Trimmed to {len(pool)} recipes")
    
    # Final validation and reporting
    final_type_counts = {}
    for meal_type in meal_types_to_fetch:
        count = sum(1 for r in pool if r.get('meal_type') == meal_type)
        final_type_counts[meal_type] = count
    
    print(f"  [POOL] Final pool: {len(pool)} recipes, distribution: {final_type_counts}")
    
    return pool


def allocate_nutrients_to_meals(daily_targets: dict) -> dict:
    """
    Allocates daily nutritional targets to individual meals using standard meal distribution ratios.
    
    Standard allocation (based on nutrition science):
    - Breakfast: 25% of daily calories/nutrients (light start to the day)
    - Lunch: 40% of daily calories/nutrients (largest meal, midday energy)
    - Dinner: 35% of daily calories/nutrients (evening meal)
    
    :param daily_targets: Dictionary with keys 'calories', 'protein_g', 'fat_g', 'carbs_g'.
    :return: Dictionary with structure: {'Breakfast': {...}, 'Lunch': {...}, 'Dinner': {...}}
    """
    meal_allocation_ratios = {
        'Breakfast': 0.25,
        'Lunch': 0.40,
        'Dinner': 0.35
    }
    
    meal_targets = {}
    for meal_name, ratio in meal_allocation_ratios.items():
        meal_targets[meal_name] = {
            'calories': round(daily_targets.get('calories', 0) * ratio, 1),
            'protein_g': round(daily_targets.get('protein_g', 0) * ratio, 1),
            'fat_g': round(daily_targets.get('fat_g', 0) * ratio, 1),
            'carbs_g': round(daily_targets.get('carbs_g', 0) * ratio, 1)
        }
    
    return meal_targets


def generate_full_meal_plan(user_request: dict):
    """
    Main orchestrator function that generates a complete multi-day meal plan with structured meals.
    
    MEMORY-OPTIMIZED VERSION:
    - Keeps QuerySets lazy until absolutely necessary
    - Fetches only minimal fields needed for optimization
    - Uses database-level filtering to avoid loading large datasets
    - Limits recipe pool size per optimization to prevent memory overflow
    
    This function implements a hierarchical optimization approach:
    1. Allocates daily nutritional targets to Breakfast, Lunch, and Dinner
    2. For each day, generates Breakfast, Lunch, and Dinner separately
    3. Each meal is optimized to include at least 1 Main Course and 1 complementary dish
    4. Tracks used recipes globally to ensure no repetition across the entire plan
    
    :param user_request: Dictionary containing:
        - 'target_nutrients': dict with 'calories', 'protein_g', 'fat_g', 'carbs_g'
        - 'number_of_days': int (e.g., 7)
        - 'allergies': list of strings (future use)
        - 'dislikes': list of strings (future use)
    :return: Dictionary with structure:
        {
            'Day 1': {
                'Breakfast': [recipe_dict1, recipe_dict2],
                'Lunch': [recipe_dict3, recipe_dict4],
                'Dinner': [recipe_dict5, recipe_dict6]
            },
            'Day 2': {...},
            ...
        }
    """
    
    # Step 1: Predict nutritional cluster using ANN
    # (For now, using a simplified approach - can be enhanced with actual ANN prediction)
    predicted_cluster = 3  # High-Protein cluster (can be made dynamic)
    
    # Step 2: Build base QuerySet (LAZY - no data loaded yet)
    # Filter at database level, exclude unknown meal types
    base_queryset = Recipe.objects.filter(
        cluster=predicted_cluster
    ).exclude(
        meal_type='Unknown'
    )
    
    # TODO: Add allergy and dislike filtering here (database-level)
    # if user_request.get('allergies'):
    #     base_queryset = base_queryset.exclude(...)
    
    # Check if we have enough recipes (using count() - still lazy, just a DB query)
    total_available = base_queryset.count()
    if total_available < 6:  # Need at least 2 recipes per meal × 3 meals
        print(f"[PLANNER] ERROR: Not enough recipes in pool ({total_available}). Need at least 6.")
        return None
    
    print(f"[PLANNER] Found {total_available} available recipes in cluster {predicted_cluster}")
    
    # Step 3: Get daily targets (NO PER-MEAL ALLOCATION - Daily Global Optimization uses daily totals)
    daily_targets = user_request.get('target_nutrients', {})
    
    # Step 4: Generate multi-day plan using Daily Global Optimization
    # CRITICAL: Keep used_recipe_ids as a set for O(1) lookups
    weekly_plan = {}
    used_recipe_ids = set()
    
    number_of_days = user_request.get('number_of_days', 1)
    
    # Configuration: Limit recipe pool size per meal to prevent memory issues
    MAX_RECIPES_PER_MEAL_POOL = 500  # Per-meal pool limit (total day pool will be ~1500)
    
    for day in range(1, number_of_days + 1):
        print(f"\n[PLANNER] Generating Day {day} (Daily Global Optimization)...")
        print(f"[PLANNER] Recipes used so far: {len(used_recipe_ids)}")
        
        # Build recipe pools for all 3 meals for this day
        recipe_pools = {}
        all_pools_valid = True
        
        for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
            meal_structure = get_meal_structure(meal_name)
            
            # MULTI-STAGE FUNNEL FILTERING: Build bounded, stratified pool per meal
            meal_recipe_pool = construct_funnel_pool(
                meal_name=meal_name,
                meal_structure=meal_structure,
                primary_cluster=predicted_cluster,
                meal_target_nutrients=daily_targets,  # Pass daily targets for reference (not used for allocation)
                used_recipe_ids=used_recipe_ids,
                max_pool_size=MAX_RECIPES_PER_MEAL_POOL
            )
            
            if not meal_recipe_pool:
                print(f"  [PLANNER] ERROR: Could not construct pool for {meal_name} on Day {day}.")
                all_pools_valid = False
                break
            
            recipe_pools[meal_name] = meal_recipe_pool
            print(f"  [PLANNER] {meal_name} pool: {len(meal_recipe_pool)} recipes")
        
        if not all_pools_valid:
            print(f"[PLANNER] ERROR: Failed to construct recipe pools for Day {day}.")
            break
        
        # DAILY GLOBAL OPTIMIZATION: Optimize all 3 meals simultaneously with daily totals
        print(f"  [PLANNER] Optimizing all 3 meals simultaneously for Day {day}...")
        
        daily_plan_result = create_daily_plan_global(
            recipe_pools=recipe_pools,
            daily_target_nutrients=daily_targets,  # DAILY totals, not per-meal
            used_recipe_ids=used_recipe_ids,
            day_number=day,
            max_protein_deviation_pct=15.0  # Can be relaxed if needed
        )
        
        if not daily_plan_result:
            print(f"[PLANNER] ERROR: Daily global optimization failed for Day {day}.")
            break
        
        # Extract results
        day_plan = {
            'Breakfast': daily_plan_result.get('Breakfast', []),
            'Lunch': daily_plan_result.get('Lunch', []),
            'Dinner': daily_plan_result.get('Dinner', [])
        }
        
        status = daily_plan_result.get('status', 'Unknown')
        deviations = daily_plan_result.get('deviations', {})
        actual_nutrients = daily_plan_result.get('actual_nutrients', {})
        
        # Log optimization status
        if status == 'Optimal':
            print(f"  [PLANNER] ✓ Day {day} optimized successfully (status: {status})")
        else:
            print(f"  [PLANNER] ⚠ Day {day} optimization status: {status}")
        
        # Log deviations
        for nutrient, dev_info in deviations.items():
            dev_pct = dev_info.get('deviation_pct', 0)
            if dev_pct > 10:  # Log significant deviations
                print(f"    [PLANNER] {nutrient}: {dev_pct:.1f}% deviation (target: {dev_info['target']:.1f}, actual: {dev_info['actual']:.1f})")
        
        # Track used recipes
        total_recipes_selected = 0
        day_has_vegetable = False
        day_dessert_count = 0
        
        for meal_name, recipes in day_plan.items():
            total_recipes_selected += len(recipes)
            
            for recipe in recipes:
                used_recipe_ids.add(recipe['id'])
            
            if check_vegetable_inclusion(recipes):
                day_has_vegetable = True
            
            meal_dessert_count = sum(1 for r in recipes if r.get('meal_type') == 'Dessert')
            day_dessert_count += meal_dessert_count
            
            print(f"    [PLANNER] {meal_name}: {len(recipes)} recipes")
        
        # Validate daily balance
        if not day_has_vegetable:
            print(f"  [PLANNER] WARNING: Day {day} does not include any vegetable-based dishes.")
        
        if day_dessert_count > 1:
            print(f"  [PLANNER] WARNING: Day {day} has {day_dessert_count} desserts (max 1 recommended).")
        
        # Store the day plan
        weekly_plan[f"Day {day}"] = day_plan
        print(f"[PLANNER] Day {day} completed: {total_recipes_selected} recipes total")
        
        # Clean up pools
        del recipe_pools
    
    if not weekly_plan:
        print("[PLANNER] ERROR: Could not generate any complete days.")
        return None
    
    return weekly_plan