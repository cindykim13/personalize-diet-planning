# planner/management/commands/test_meal_composition.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, calculate_nutritional_targets_from_profile

class Command(BaseCommand):
    help = 'TIER 1: Quick single-scenario integration test for end-to-end pipeline validation'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 70)
        self.stdout.write("TIER 1: SINGLE SCENARIO INTEGRATION TEST")
        self.stdout.write("=" * 70)
        self.stdout.write("Purpose: Quick validation of complete end-to-end pipeline")
        self.stdout.write("Use Case: Fast developer feedback after code changes")
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
        
        # === SINGLE DEFAULT USER PROFILE ===
        # Standard "Balanced" diet persona for quick validation
        user_profile = {
            'age': 30,
            'gender': 'male',
            'height_cm': 175.0,
            'weight_kg': 75.0,
            'activity_level': 'moderate',
            'primary_goal': 'maintain',
            'pace': 'moderate',
            'number_of_days': 3,  # Quick test with 3 days
            'allergies': '',
            'dislikes': ''
        }
        
        self.stdout.write(f"\n[TEST] Single User Profile:")
        self.stdout.write(f"  Age: {user_profile['age']}, Gender: {user_profile['gender']}")
        self.stdout.write(f"  Height: {user_profile['height_cm']} cm, Weight: {user_profile['weight_kg']} kg")
        self.stdout.write(f"  Activity: {user_profile['activity_level']}, Goal: {user_profile['primary_goal']}")
        self.stdout.write(f"  Days: {user_profile['number_of_days']}\n")
        
        # === PART 1: Calculate Nutritional Targets ===
        self.stdout.write("[STEP 1] Calculating nutritional targets from user profile...")
        try:
            daily_targets = calculate_nutritional_targets_from_profile(user_profile)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Targets calculated: {daily_targets['calories']:.0f} kcal, {daily_targets['protein_g']:.0f}g protein"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Calculation failed: {e}"))
            return
        
        # === PART 2-4: Generate Meal Plan ===
        self.stdout.write("\n[STEP 2-4] Generating meal plan (rule-based cluster mapping + optimization)...")
        weekly_plan = generate_full_meal_plan(user_profile)
        
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
        
        # Calculate meal allocation ratios for target display
        meal_allocation_ratios = {
            'Breakfast': 0.25,
            'Lunch': 0.40,
            'Dinner': 0.35
        }
        
        # Iterate through each day
        for day_key in sorted(weekly_plan.keys()):
            day_plan = weekly_plan[day_key]
            day_num = day_key.split()[-1]  # Extract day number
            
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"DAY {day_num}")
            self.stdout.write(f"{'=' * 70}")
            
            day_calories = 0
            day_protein = 0
            day_fat = 0
            day_carbs = 0
            day_has_vegetable = False
            day_dessert_count = 0
            day_structural_valid = True
            day_semantic_valid = True
            
            # Check each meal
            for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
                if meal_name not in day_plan:
                    validation_errors.append(f"{day_key} - {meal_name}: Missing meal")
                    day_structural_valid = False
                    continue
                
                meal_recipes = day_plan[meal_name]
                if not meal_recipes:
                    validation_errors.append(f"{day_key} - {meal_name}: Empty")
                    day_structural_valid = False
                    continue
                
                # Calculate meal target (approximate allocation)
                meal_target_calories = daily_targets['calories'] * meal_allocation_ratios.get(meal_name, 0.33)
                meal_target_protein = daily_targets['protein_g'] * meal_allocation_ratios.get(meal_name, 0.33)
                
                # Display meal with targets
                self.stdout.write(f"\n  {meal_name} (Target: ~{meal_target_calories:.0f} kcal, ~{meal_target_protein:.0f}g protein):")
                
                # Track meal nutrition
                meal_calories = 0
                meal_protein = 0
                meal_fat = 0
                meal_carbs = 0
                
                # Display each recipe with full name and meal_type
                for recipe in meal_recipes:
                    recipe_name = recipe.get('name', 'Unknown Recipe')
                    recipe_type = recipe.get('meal_type', 'Unknown')
                    recipe_id = recipe['id']
                    
                    # Display recipe
                    self.stdout.write(f"    - {recipe_name} [{recipe_type}]")
                    
                    # Check for repetition
                    if recipe_id in all_recipe_ids:
                        validation_errors.append(f"Recipe repetition: {recipe_name} (ID: {recipe_id})")
                        day_structural_valid = False
                    all_recipe_ids.add(recipe_id)
                    
                    # Track nutrition
                    recipe_cal = recipe.get('avg_calories', 0)
                    recipe_pro = recipe.get('avg_protein_g', 0)
                    recipe_fat = recipe.get('avg_fat_g', 0)
                    recipe_carbs = recipe.get('avg_carbs_g', 0)
                    
                    meal_calories += recipe_cal
                    meal_protein += recipe_pro
                    meal_fat += recipe_fat
                    meal_carbs += recipe_carbs
                    
                    day_calories += recipe_cal
                    day_protein += recipe_pro
                    day_fat += recipe_fat
                    day_carbs += recipe_carbs
                    
                    # Track vegetables
                    if recipe_type in ['Side Dish', 'Salad', 'Soup']:
                        day_has_vegetable = True
                    
                    # Track desserts
                    if recipe_type == 'Dessert':
                        day_dessert_count += 1
                
                # Display meal totals
                self.stdout.write(f"  Meal Totals: {meal_calories:.0f} kcal, {meal_protein:.1f}g protein")
                
                # Validate meal structure
                if meal_name == 'Breakfast':
                    breakfast_items = [r for r in meal_recipes if r.get('meal_type') == 'Breakfast']
                    complementary = [r for r in meal_recipes if r.get('meal_type') in ['Fruit', 'Drink']]
                    if len(breakfast_items) != 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Must have 1 Breakfast item (found {len(breakfast_items)})")
                        day_structural_valid = False
                    if len(complementary) < 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Missing Fruit/Drink")
                        day_structural_valid = False
                else:  # Lunch/Dinner
                    main_courses = [r for r in meal_recipes if r.get('meal_type') == 'Main Course']
                    if len(main_courses) != 1:
                        validation_errors.append(f"{day_key} - {meal_name}: Must have 1 Main Course (found {len(main_courses)})")
                        day_structural_valid = False
            
            # Daily nutrition summary with target comparison
            total_calories += day_calories
            total_protein += day_protein
            total_fat += day_fat
            total_carbs += day_carbs
            
            # Calculate daily deviations
            target_cal = daily_targets['calories']
            target_pro = daily_targets['protein_g']
            target_fat_day = daily_targets['fat_g']
            target_carbs_day = daily_targets['carbs_g']
            
            day_cal_deviation = abs(day_calories - target_cal) / target_cal * 100 if target_cal > 0 else 0
            day_pro_deviation = abs(day_protein - target_pro) / target_pro * 100 if target_pro > 0 else 0
            day_fat_deviation = abs(day_fat - target_fat_day) / target_fat_day * 100 if target_fat_day > 0 else 0
            day_carbs_deviation = abs(day_carbs - target_carbs_day) / target_carbs_day * 100 if target_carbs_day > 0 else 0
            
            # Display daily totals
            self.stdout.write(f"\n  [DAY {day_num} TOTALS]")
            self.stdout.write(f"    Actual: {day_calories:.0f} kcal, {day_protein:.1f}g protein, {day_fat:.1f}g fat, {day_carbs:.1f}g carbs")
            self.stdout.write(f"    Target: {target_cal:.0f} kcal, {target_pro:.1f}g protein, {target_fat_day:.1f}g fat, {target_carbs_day:.1f}g carbs")
            self.stdout.write(f"    Deviation: {day_cal_deviation:.1f}% (Cal), {day_pro_deviation:.1f}% (Pro), {day_fat_deviation:.1f}% (Fat), {day_carbs_deviation:.1f}% (Carbs)")
            
            # Daily validation status
            day_validation_notes = []
            if day_structural_valid:
                day_validation_notes.append("✓ Structural integrity OK")
            else:
                day_validation_notes.append("✗ Structural issues detected")
            
            if day_has_vegetable:
                day_validation_notes.append("✓ Includes vegetables")
            else:
                day_validation_notes.append("⚠ No vegetables")
            
            if day_dessert_count <= 1:
                day_validation_notes.append("✓ Dessert count OK")
            else:
                day_validation_notes.append(f"✗ {day_dessert_count} desserts (max 1)")
                day_semantic_valid = False
            
            if day_cal_deviation <= 20 and day_pro_deviation <= 20:
                day_validation_notes.append("✓ Nutritional accuracy OK")
            elif day_cal_deviation <= 30 and day_pro_deviation <= 30:
                day_validation_notes.append("⚠ Nutritional accuracy acceptable")
            else:
                day_validation_notes.append("✗ Nutritional accuracy poor")
                day_semantic_valid = False
            
            self.stdout.write(f"  [DAY {day_num} VALIDATION] {', '.join(day_validation_notes)}")
            
            # Semantic checks (for warnings/errors tracking)
            if not day_has_vegetable:
                validation_warnings.append(f"{day_key}: No vegetable-based dishes")
            if day_dessert_count > 1:
                validation_errors.append(f"{day_key}: {day_dessert_count} desserts (max 1 allowed)")
        
        # Weekly nutrition validation
        target_calories = daily_targets['calories'] * len(weekly_plan)
        target_protein = daily_targets['protein_g'] * len(weekly_plan)
        target_fat = daily_targets['fat_g'] * len(weekly_plan)
        target_carbs = daily_targets['carbs_g'] * len(weekly_plan)
        
        cal_deviation = abs(total_calories - target_calories) / target_calories * 100 if target_calories > 0 else 0
        pro_deviation = abs(total_protein - target_protein) / target_protein * 100 if target_protein > 0 else 0
        fat_deviation = abs(total_fat - target_fat) / target_fat * 100 if target_fat > 0 else 0
        carbs_deviation = abs(total_carbs - target_carbs) / target_carbs * 100 if target_carbs > 0 else 0
        
        # Validation thresholds
        if cal_deviation > 30:
            validation_errors.append(f"Calorie deviation too high: {cal_deviation:.1f}% (target: <30%)")
        elif cal_deviation > 20:
            validation_warnings.append(f"Calorie deviation: {cal_deviation:.1f}%")
        
        if pro_deviation > 30:
            validation_errors.append(f"Protein deviation too high: {pro_deviation:.1f}% (target: <30%)")
        elif pro_deviation > 20:
            validation_warnings.append(f"Protein deviation: {pro_deviation:.1f}%")
        
        # === FINAL REPORT ===
        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("VALIDATION SUMMARY")
        self.stdout.write("-" * 70)
        
        self.stdout.write(f"\nStructural Validation:")
        self.stdout.write(f"  Days Generated: {len(weekly_plan)}/{user_profile['number_of_days']}")
        self.stdout.write(f"  Unique Recipes: {len(all_recipe_ids)}")
        self.stdout.write(f"  Structural Errors: {len([e for e in validation_errors if 'Missing' in e or 'Must have' in e])}")
        
        self.stdout.write(f"\nNutritional Accuracy:")
        self.stdout.write(f"  Calories: {total_calories:.0f} / {target_calories:.0f} ({cal_deviation:.1f}% deviation)")
        self.stdout.write(f"  Protein: {total_protein:.1f}g / {target_protein:.1f}g ({pro_deviation:.1f}% deviation)")
        self.stdout.write(f"  Fat: {total_fat:.1f}g / {target_fat:.1f}g ({fat_deviation:.1f}% deviation)")
        self.stdout.write(f"  Carbs: {total_carbs:.1f}g / {target_carbs:.1f}g ({carbs_deviation:.1f}% deviation)")
        
        if validation_errors:
            self.stdout.write(f"\n✗ Errors ({len(validation_errors)}):")
            for error in validation_errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        
        if validation_warnings:
            self.stdout.write(f"\n⚠ Warnings ({len(validation_warnings)}):")
            for warning in validation_warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
        
        # Final status
        self.stdout.write("\n" + "=" * 70)
        if len(validation_errors) == 0:
            if len(validation_warnings) == 0:
                self.stdout.write(self.style.SUCCESS("✓ TEST PASSED (Excellent)"))
            else:
                self.stdout.write(self.style.SUCCESS("✓ TEST PASSED (with warnings)"))
        else:
            self.stdout.write(self.style.ERROR("✗ TEST FAILED (critical errors)"))
        self.stdout.write("=" * 70 + "\n")
