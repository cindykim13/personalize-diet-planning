# planner/management/commands/test_meal_composition.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, check_vegetable_inclusion

class Command(BaseCommand):
    help = 'Tests the hierarchical meal composition system with comprehensive validation'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 70)
        self.stdout.write("TESTING DAILY GLOBAL OPTIMIZATION SYSTEM")
        self.stdout.write("=" * 70)
        self.stdout.write("Architecture: Daily Global Optimization (all 3 meals optimized simultaneously)")
        self.stdout.write("Key Feature: Flexible nutrient distribution across meals using daily totals")
        self.stdout.write("=" * 70)
        
        # Prerequisite check: Ensure meal types are classified
        from planner.models import Recipe
        unclassified_count = Recipe.objects.filter(meal_type='Unknown').count()
        total_count = Recipe.objects.count()
        
        if total_count == 0:
            self.stdout.write(self.style.ERROR("\n[ERROR] No recipes found in database. Please run 'python manage.py load_recipes' first."))
            return
        
        if unclassified_count == total_count:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] All {total_count} recipes are unclassified. Please run 'python manage.py classify_meal_types' first."))
            return
        
        classified_pct = ((total_count - unclassified_count) / total_count * 100) if total_count > 0 else 0
        self.stdout.write(f"\n[INFO] Recipe classification: {total_count - unclassified_count}/{total_count} classified ({classified_pct:.1f}%)")
        
        # Check for Main Course availability
        main_course_count = Recipe.objects.filter(meal_type='Main Course').count()
        if main_course_count < 21:  # Need at least 1 per meal × 3 meals × 7 days
            self.stdout.write(self.style.WARNING(f"\n[WARNING] Only {main_course_count} Main Course recipes found. May not be enough for 7-day plan."))
        
        # Define realistic nutritional targets (for an active adult)
        # Daily: 2200 calories, 120g protein (flexible allocation across meals)
        # Weekly total: ~15,400 calories
        # NOTE: Using daily totals - optimizer can flexibly distribute across Breakfast/Lunch/Dinner
        user_request = {
            'number_of_days': 7,
            'target_nutrients': {
                'calories': 2200,      # Realistic daily target
                'protein_g': 120,      # Daily total (optimizer distributes flexibly)
                'fat_g': 73,           # ~30% of calories from fat
                'carbs_g': 200         # ~40% of calories from carbs
            },
            'allergies': [],
            'dislikes': []
        }
        
        self.stdout.write(f"\n[TEST] Generating {user_request['number_of_days']}-day meal plan...")
        self.stdout.write(f"[TEST] Daily targets: {user_request['target_nutrients']}")
        self.stdout.write(f"[TEST] Weekly totals: ~{user_request['target_nutrients']['calories'] * 7} calories, ~{user_request['target_nutrients']['protein_g'] * 7}g protein\n")
        
        # Generate the meal plan
        weekly_plan = generate_full_meal_plan(user_request)
        
        # === VALIDATION ===
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("VALIDATION RESULTS")
        self.stdout.write("=" * 70)
        
        if not weekly_plan:
            self.stdout.write(self.style.ERROR("\n[FAILED] No meal plan generated."))
            return
        
        # Validation tracking
        all_recipe_ids = set()
        validation_errors = []
        validation_warnings = []
        
        # Track nutritional totals
        total_calories = 0
        total_protein = 0
        total_fat = 0
        total_carbs = 0
        
        # Iterate through each day
        for day_key in sorted(weekly_plan.keys()):
            day_plan = weekly_plan[day_key]
            day_num = day_key.split()[-1]  # Extract day number
            
            self.stdout.write(f"\n--- {day_key} ---")
            
            day_calories = 0
            day_protein = 0
            day_fat = 0
            day_carbs = 0
            day_has_vegetable = False  # Track if day includes vegetables
            day_dessert_count = 0       # Track dessert count
            
            # Check each meal
            for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
                if meal_name not in day_plan:
                    validation_errors.append(f"{day_key} - {meal_name}: Missing meal")
                    continue
                
                meal_recipes = day_plan[meal_name]
                if not meal_recipes:
                    validation_errors.append(f"{day_key} - {meal_name}: Empty meal")
                    continue
                
                # Check meal structure based on meal type (Breakfast vs Lunch/Dinner)
                if meal_name == 'Breakfast':
                    # Breakfast should have: 1 Breakfast item + 1 Fruit (or Drink)
                    breakfast_items = [r for r in meal_recipes if r.get('meal_type') == 'Breakfast']
                    fruits = [r for r in meal_recipes if r.get('meal_type') == 'Fruit']
                    drinks = [r for r in meal_recipes if r.get('meal_type') == 'Drink']
                    complementary_items = fruits + drinks
                    
                    if len(breakfast_items) != 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Must have exactly 1 Breakfast item (found {len(breakfast_items)})")
                    
                    if len(complementary_items) < 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Missing Fruit or Drink (found {len(fruits)} fruits, {len(drinks)} drinks)")
                    elif len(complementary_items) > 1:
                        validation_warnings.append(f"{day_key} - {meal_name}: {len(complementary_items)} complementary items (expected 1 Fruit or Drink)")
                    
                    # Check for inappropriate items
                    main_courses = [r for r in meal_recipes if r.get('meal_type') == 'Main Course']
                    if len(main_courses) > 0:
                        validation_errors.append(f"{day_key} - {meal_name}: Contains {len(main_courses)} Main Course(s) - Breakfast should NOT have Main Courses!")
                
                else:
                    # Lunch/Dinner should have: 1 Main Course + 1 complementary dish
                    main_courses = [r for r in meal_recipes if r.get('meal_type') == 'Main Course']
                    complementary_dishes = [
                        r for r in meal_recipes 
                        if r.get('meal_type') in ['Side', 'Side Dish', 'Salad', 'Soup', 'Dessert']
                    ]
                    
                    if len(main_courses) != 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Must have exactly 1 Main Course (found {len(main_courses)})")
                    
                    if len(complementary_dishes) < 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Missing complementary dish (found {len(complementary_dishes)})")
                    elif len(complementary_dishes) > 2:
                        validation_warnings.append(f"{day_key} - {meal_name}: {len(complementary_dishes)} complementary dishes (expected 1-2)")
                    
                    # Check for inappropriate items
                    breakfast_items = [r for r in meal_recipes if r.get('meal_type') == 'Breakfast']
                    if len(breakfast_items) > 0:
                        validation_warnings.append(f"{day_key} - {meal_name}: Contains {len(breakfast_items)} Breakfast item(s) - typically not appropriate for {meal_name}")
                
                # NUTRITIONAL INTELLIGENCE VALIDATION: Meal-role appropriateness
                desserts_in_meal = [r for r in meal_recipes if r.get('meal_type') == 'Dessert']
                if len(desserts_in_meal) > 0:
                    day_dessert_count += len(desserts_in_meal)  # Track for daily total
                    if meal_name in ['Breakfast', 'Lunch']:
                        validation_errors.append(f"{day_key} - {meal_name}: Contains dessert '{desserts_in_meal[0]['name']}' (desserts not allowed for {meal_name})")
                    elif meal_name == 'Dinner' and len(desserts_in_meal) > 1:
                        validation_warnings.append(f"{day_key} - {meal_name}: Contains {len(desserts_in_meal)} desserts (max 1 recommended)")
                
                # Track vegetables for daily balance
                if check_vegetable_inclusion(meal_recipes):
                    day_has_vegetable = True
                
                # Check total recipes per meal (flexible: Breakfast=2, Lunch/Dinner=2-3)
                if meal_name == 'Breakfast':
                    if len(meal_recipes) != 2:
                        validation_warnings.append(f"{day_key} - {meal_name}: {len(meal_recipes)} recipes (expected 2)")
                else:  # Lunch/Dinner
                    if len(meal_recipes) < 2 or len(meal_recipes) > 3:
                        validation_warnings.append(f"{day_key} - {meal_name}: {len(meal_recipes)} recipes (expected 2-3)")
                
                # Display meal contents
                self.stdout.write(f"\n  {meal_name}:")
                for recipe in meal_recipes:
                    recipe_id = recipe['id']
                    recipe_name = recipe['name']
                    meal_type = recipe.get('meal_type', 'Unknown')
                    
                    # Check for repetition
                    if recipe_id in all_recipe_ids:
                        validation_errors.append(f"Recipe repetition: '{recipe_name}' (ID: {recipe_id}) appears multiple times")
                    all_recipe_ids.add(recipe_id)
                    
                    # Accumulate nutrition
                    day_calories += recipe.get('avg_calories', 0)
                    day_protein += recipe.get('avg_protein_g', 0)
                    day_fat += recipe.get('avg_fat_g', 0)
                    day_carbs += recipe.get('avg_carbs_g', 0)
                    
                    self.stdout.write(f"    - {recipe_name} [{meal_type}]")
                    self.stdout.write(f"      Calories: {recipe.get('avg_calories', 0):.1f}, "
                                    f"Protein: {recipe.get('avg_protein_g', 0):.1f}g")
            
            # Daily balance validation
            if not day_has_vegetable:
                validation_warnings.append(f"{day_key}: No vegetable-based dishes included (Side/Salad/Soup recommended)")
            
            if day_dessert_count > 1:
                validation_errors.append(f"{day_key}: {day_dessert_count} desserts (max 1 per day recommended)")
            elif day_dessert_count == 1:
                self.stdout.write(f"  ✓ Daily dessert count: {day_dessert_count} (within limit)")
            
            if day_has_vegetable:
                self.stdout.write(f"  ✓ Daily vegetable inclusion: Yes")
            
            # Daily nutritional totals
            total_calories += day_calories
            total_protein += day_protein
            total_fat += day_fat
            total_carbs += day_carbs
            
            self.stdout.write(f"\n  Daily Totals: {day_calories:.1f} kcal, "
                            f"{day_protein:.1f}g protein, {day_fat:.1f}g fat, {day_carbs:.1f}g carbs")
            
            # Check daily totals against targets (allow ±10% tolerance)
            target_cal = user_request['target_nutrients']['calories']
            target_pro = user_request['target_nutrients']['protein_g']
            target_fat = user_request['target_nutrients']['fat_g']
            target_carb = user_request['target_nutrients']['carbs_g']
            
            cal_diff_pct = abs(day_calories - target_cal) / target_cal * 100 if target_cal > 0 else 0
            pro_diff_pct = abs(day_protein - target_pro) / target_pro * 100 if target_pro > 0 else 0
            
            # Realistic validation thresholds for daily variation
            if cal_diff_pct > 30:
                validation_errors.append(f"{day_key}: Daily calories deviate by {cal_diff_pct:.1f}% (CRITICAL: >30%)")
            elif cal_diff_pct > 20:
                validation_warnings.append(f"{day_key}: Daily calories deviate by {cal_diff_pct:.1f}% (WARNING: 20-30%)")
            elif cal_diff_pct > 10:
                # Acceptable range, no warning needed
                pass
            
            if pro_diff_pct > 30:
                validation_errors.append(f"{day_key}: Daily protein deviate by {pro_diff_pct:.1f}% (CRITICAL: >30%)")
            elif pro_diff_pct > 20:
                validation_warnings.append(f"{day_key}: Daily protein deviate by {pro_diff_pct:.1f}% (WARNING: 20-30%)")
            elif pro_diff_pct > 10:
                # Acceptable range, no warning needed
                pass
        
        # === FINAL SUMMARY ===
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("VALIDATION SUMMARY")
        self.stdout.write("=" * 70)
        
        # Structure validation
        expected_meals = len(weekly_plan) * 3  # 3 meals per day
        actual_meals = sum(len(day_plan) for day_plan in weekly_plan.values())
        
        if actual_meals == expected_meals:
            self.stdout.write(self.style.SUCCESS(f"✓ Meal count: {actual_meals}/{expected_meals} meals generated"))
        else:
            validation_errors.append(f"Meal count mismatch: {actual_meals}/{expected_meals}")
        
        # Repetition check (flexible: 2 Breakfast + 2-3 Lunch + 2-3 Dinner = 6-8 per day)
        expected_unique_min = len(weekly_plan) * 6  # Minimum: 6 recipes per day
        expected_unique_max = len(weekly_plan) * 8  # Maximum: 8 recipes per day
        if expected_unique_min <= len(all_recipe_ids) <= expected_unique_max:
            self.stdout.write(self.style.SUCCESS(f"✓ No recipe repetition: {len(all_recipe_ids)} unique recipes (expected {expected_unique_min}-{expected_unique_max})"))
        else:
            validation_errors.append(f"Recipe count out of range: {len(all_recipe_ids)} unique recipes (expected {expected_unique_min}-{expected_unique_max})")
        
        # Check for actual repetition (should be 0 duplicates)
        if len(all_recipe_ids) < expected_unique_min:
            # Count duplicates
            all_ids_list = []
            for day_plan in weekly_plan.values():
                for meal_recipes in day_plan.values():
                    for recipe in meal_recipes:
                        all_ids_list.append(recipe['id'])
            duplicates = len(all_ids_list) - len(all_recipe_ids)
            if duplicates > 0:
                validation_errors.append(f"Recipe repetition detected: {duplicates} duplicate recipe(s) found")
        
        # Weekly nutritional totals
        target_weekly_cal = user_request['target_nutrients']['calories'] * user_request['number_of_days']
        target_weekly_pro = user_request['target_nutrients']['protein_g'] * user_request['number_of_days']
        
        cal_diff_pct = abs(total_calories - target_weekly_cal) / target_weekly_cal * 100 if target_weekly_cal > 0 else 0
        pro_diff_pct = abs(total_protein - target_weekly_pro) / target_weekly_pro * 100 if target_weekly_pro > 0 else 0
        
        self.stdout.write(f"\nWeekly Nutritional Totals:")
        self.stdout.write(f"  Calories: {total_calories:.1f} / {target_weekly_cal} target ({cal_diff_pct:.1f}% deviation)")
        self.stdout.write(f"  Protein:  {total_protein:.1f}g / {target_weekly_pro}g target ({pro_diff_pct:.1f}% deviation)")
        self.stdout.write(f"  Fat:      {total_fat:.1f}g")
        self.stdout.write(f"  Carbs:    {total_carbs:.1f}g")
        
        # Quality assessment
        self.stdout.write(f"\nNutritional Accuracy Assessment:")
        self.stdout.write(f"  Thresholds: Excellent (<10%), Good (10-20%), Warning (20-30%), Critical (>30%)")
        
        # Realistic validation thresholds for weekly totals
        # Excellent: <10%, Good: 10-20%, Warning: 20-30%, Critical: >30%
        
        if cal_diff_pct > 30:
            validation_errors.append(f"CRITICAL: Weekly calories deviate by {cal_diff_pct:.1f}% (unacceptable: >30%)")
        elif cal_diff_pct > 20:
            validation_warnings.append(f"Weekly calories deviate by {cal_diff_pct:.1f}% (WARNING: 20-30%)")
        elif cal_diff_pct > 10:
            # Good range, no warning
            pass
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Weekly calories accuracy: {cal_diff_pct:.1f}% deviation (EXCELLENT: <10%)"))
        
        # Protein deviation validation (key improvement metric)
        if pro_diff_pct > 30:
            validation_errors.append(f"CRITICAL: Weekly protein deviation {pro_diff_pct:.1f}% (unacceptable: >30%)")
        elif pro_diff_pct > 20:
            validation_warnings.append(f"Weekly protein deviation {pro_diff_pct:.1f}% (WARNING: 20-30%)")
        elif pro_diff_pct > 10:
            # Good range (10-20%), acceptable
            self.stdout.write(self.style.SUCCESS(f"✓ Weekly protein accuracy: {pro_diff_pct:.1f}% deviation (GOOD: 10-20%)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Weekly protein accuracy: {pro_diff_pct:.1f}% deviation (EXCELLENT: <10%)"))
        
        # Report errors and warnings
        if validation_warnings:
            self.stdout.write(self.style.WARNING(f"\n⚠ Warnings ({len(validation_warnings)}):"))
            for warning in validation_warnings[:10]:  # Limit output
                self.stdout.write(f"  - {warning}")
            if len(validation_warnings) > 10:
                self.stdout.write(f"  ... and {len(validation_warnings) - 10} more warnings")
        
        if validation_errors:
            self.stdout.write(self.style.ERROR(f"\n✗ Critical Errors ({len(validation_errors)}):"))
            for error in validation_errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            self.stdout.write(self.style.ERROR("\n[FAILED] Validation failed due to critical errors (>30% deviation or structural issues)."))
        else:
            # Determine overall status based on warnings and nutritional accuracy
            if validation_warnings:
                status_msg = "PASSED (with warnings)"
                status_style = self.style.WARNING
            else:
                status_msg = "PASSED (excellent)"
                status_style = self.style.SUCCESS
            
            self.stdout.write(status_style(f"\n✓ Validation {status_msg}!"))
            self.stdout.write(self.style.SUCCESS("  ✓ Structural integrity:"))
            self.stdout.write(self.style.SUCCESS("    - Breakfast: Each contains 1 Breakfast item + 1 Fruit/Drink (NOT Main Course)"))
            self.stdout.write(self.style.SUCCESS("    - Lunch/Dinner: Each contains 1 Main Course + 1-2 complementary dishes"))
            self.stdout.write(self.style.SUCCESS("    - No recipe repetition (intra-day or inter-day)"))
            self.stdout.write(self.style.SUCCESS("    - All meals properly structured with meal-appropriate items"))
            self.stdout.write(self.style.SUCCESS("  ✓ Semantic rules: No desserts for breakfast/lunch, max 1 dessert/day"))
            self.stdout.write(self.style.SUCCESS("  ✓ Nutritional accuracy: Within realistic, achievable thresholds"))
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("TEST COMPLETE")
        self.stdout.write("=" * 70 + "\n")
