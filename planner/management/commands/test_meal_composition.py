# planner/management/commands/test_meal_composition.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, calculate_nutritional_targets_from_profile, map_goal_to_cluster
from planner.models import Recipe, UserProfile, PlanGenerationEvent, GeneratedPlan
from django.contrib.auth.models import User
from django.utils import timezone

class Command(BaseCommand):
    help = 'TIER 1: Fast, targeted integration test for High-Carb cluster with database logging'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 80)
        self.stdout.write("TIER 1: HIGH-CARB CLUSTER INTEGRATION TEST")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Fast, targeted validation of High-Carb nutritional cluster")
        self.stdout.write("Use Case: Quick developer feedback + Data flywheel contribution")
        self.stdout.write("Target: High-Carb / Low-Fat / Sugary cluster (Cluster 2)")
        self.stdout.write("=" * 80)
        
        # Prerequisite check: Ensure meal types are classified
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
        
        # Get cluster mapping for validation
        cluster_map = dict(Recipe.objects.values_list('cluster', 'cluster_name').distinct())
        
        # === HIGH-CARB PERSONA DESIGN ===
        # Scientific rationale: To target "High-Carb / Low-Fat / Sugary" cluster (Cluster 2), we need:
        # Based on the comprehensive decision matrix:
        # - maintain + low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary)
        # - lose_weight + low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary)
        # - gain_weight → Cluster 2 (High-Carb / Low-Fat / Sugary)
        # We'll use maintain + low_fat for a realistic endurance athlete profile
        
        user_profile = {
            'age': 30,  # Young, active adult
            'gender': 'male',
            'height_cm': 180.0,  # Average height
            'weight_kg': 75.0,  # Lean, athletic build
            'activity_level': 'very_active',  # Maximizes TDEE and carb needs
            'primary_goal': 'gain muscle',
            'dietary_style': 'balanced',  # Key parameter: low_fat dietary style maps to High-Carb cluster
            'pace': 'moderate',
            'number_of_days': 3,  # Quick test with 3 days
            'allergies': '',
            'dislikes': ''
        }
        
        self.stdout.write(f"\n[TEST PERSONA: HIGH-CARB TARGET]")
        self.stdout.write(f"  Name: Endurance Athlete (High-Carb Profile)")
        self.stdout.write(f"  Age: {user_profile['age']}, Gender: {user_profile['gender']}")
        self.stdout.write(f"  Height: {user_profile['height_cm']} cm, Weight: {user_profile['weight_kg']} kg")
        self.stdout.write(f"  Activity: {user_profile['activity_level']} (very active - maximizes carb needs)")
        self.stdout.write(f"  Goal: {user_profile['primary_goal']}")
        self.stdout.write(f"  Dietary Style: {user_profile.get('dietary_style', 'balanced')} (maps to High-Carb cluster)")
        self.stdout.write(f"  Days: {user_profile['number_of_days']}")
        self.stdout.write(f"  Expected Cluster: High-Carb / Low-Fat / Sugary (Cluster 2)")
        
        # === CREATE TEST USER FOR DATABASE LOGGING ===
        self.stdout.write(f"\n[DATABASE SETUP]")
        try:
            username = f"test_higcarb_{int(timezone.now().timestamp())}"
            test_user = User.objects.create_user(
                username=username,
                email=f"higcarb_test_{int(timezone.now().timestamp())}@test.com",
                password='test_password_123',
                first_name='Endurance',
                last_name='Athlete'
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created test user: {username}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed to create test user: {e}"))
            return
        
        # === PART 1: Calculate Nutritional Targets ===
        self.stdout.write(f"\n[PART 1: USER REQUEST ANALYZER]")
        try:
            daily_targets = calculate_nutritional_targets_from_profile(user_profile)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Nutritional targets calculated successfully"))
            
            # Calculate actual macro ratios to verify high-carb profile
            total_calories = daily_targets['calories']
            protein_cal = daily_targets['protein_g'] * 4  # 4 kcal per gram
            fat_cal = daily_targets['fat_g'] * 9  # 9 kcal per gram
            carbs_cal = daily_targets['carbs_g'] * 4  # 4 kcal per gram
            
            protein_ratio = (protein_cal / total_calories * 100) if total_calories > 0 else 0
            fat_ratio = (fat_cal / total_calories * 100) if total_calories > 0 else 0
            carbs_ratio = (carbs_cal / total_calories * 100) if total_calories > 0 else 0
            
            self.stdout.write(f"  Daily Targets: {daily_targets}")
            self.stdout.write(f"  Macro Ratios: Protein {protein_ratio:.1f}%, Fat {fat_ratio:.1f}%, Carbs {carbs_ratio:.1f}%")
            
            # Verify high-carb profile
            if carbs_ratio >= 50:
                self.stdout.write(self.style.SUCCESS(f"  ✓ High-carb profile confirmed: {carbs_ratio:.1f}% carbs (target: ≥50%)"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ Carbs at {carbs_ratio:.1f}% (expected ≥50% for high-carb profile)"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Calculation failed: {e}"))
            test_user.delete()
            return
        
        # === PART 2: Rule-Based Cluster Mapping ===
        self.stdout.write(f"\n[PART 2: SEMANTIC CLUSTER MAPPING]")
        primary_goal = user_profile.get('primary_goal', 'maintain')
        dietary_style = user_profile.get('dietary_style', 'balanced')
        predicted_cluster = map_goal_to_cluster(primary_goal, dietary_style)
        predicted_cluster_name = cluster_map.get(predicted_cluster, "Unknown")
        
        self.stdout.write(f"  Primary Goal: {primary_goal}")
        self.stdout.write(f"  Dietary Style: {dietary_style}")
        self.stdout.write(f"  Rule-Based Cluster Selection: {predicted_cluster} ({predicted_cluster_name})")
        self.stdout.write(f"  Mapping Logic: primary_goal='{primary_goal}', dietary_style='{dietary_style}' → cluster={predicted_cluster}")
        
        # Check if cluster matches High-Carb expectation (Cluster 2)
        target_cluster_id = 2
        target_cluster_keywords = ['High-Carb', 'Low-Fat', 'Sugary']
        cluster_id_match = (predicted_cluster == target_cluster_id)
        cluster_keyword_match = any(keyword.lower() in predicted_cluster_name.lower() for keyword in target_cluster_keywords)
        
        if cluster_id_match:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster ID matches High-Carb target: {predicted_cluster} (expected {target_cluster_id})"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Cluster ID mismatch: got {predicted_cluster}, expected {target_cluster_id}"))
        
        if cluster_keyword_match:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster name matches High-Carb target: {predicted_cluster_name}"))
        else:
            self.stdout.write(self.style.WARNING(f"  ⚠ Cluster name doesn't match High-Carb keywords. Got: {predicted_cluster_name}"))
        
        # === PART 3 & 4: Generate Meal Plan with Database Logging ===
        self.stdout.write(f"\n[PART 3 & 4: GLOBAL DAILY OPTIMIZER & ORCHESTRATOR]")
        self.stdout.write(f"  Generating meal plan with database logging enabled...")
        
        try:
            # Call with user_id to enable database logging
            weekly_plan = generate_full_meal_plan(user_profile, user_id=test_user.id)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            test_user.delete()
            return
        
        if not weekly_plan:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan (returned None)"))
            test_user.delete()
            return
        
        self.stdout.write(self.style.SUCCESS(f"  ✓ Meal plan generated successfully: {len(weekly_plan)} days"))
        
        # === DATABASE LOGGING VALIDATION ===
        self.stdout.write(f"\n[DATABASE LOGGING VALIDATION]")
        database_logging_success = False
        try:
            # Verify UserProfile was created/updated
            user_profile_obj = UserProfile.objects.get(user=test_user)
            self.stdout.write(self.style.SUCCESS(f"  ✓ UserProfile found for user {test_user.username}"))
            
            # Verify PlanGenerationEvent was created
            plan_events = PlanGenerationEvent.objects.filter(user_profile=user_profile_obj).order_by('-created_at')
            if plan_events.exists():
                plan_event = plan_events.first()
                self.stdout.write(self.style.SUCCESS(f"  ✓ PlanGenerationEvent #{plan_event.id} created"))
                self.stdout.write(f"    - Status: {plan_event.status}")
                self.stdout.write(f"    - Primary Goal: {plan_event.primary_goal}")
                self.stdout.write(f"    - Predicted Cluster: {plan_event.predicted_cluster_name}")
                self.stdout.write(f"    - Calculated Targets: {plan_event.calculated_targets}")
                
                # Verify GeneratedPlan was created
                try:
                    generated_plan = GeneratedPlan.objects.get(event=plan_event)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ GeneratedPlan created for Event #{plan_event.id}"))
                    self.stdout.write(f"    - Plan Data: {len(generated_plan.plan_data)} days")
                    self.stdout.write(f"    - Nutritional Summary: {generated_plan.final_nutritional_summary}")
                    database_logging_success = True
                except GeneratedPlan.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"  ✗ GeneratedPlan not found for Event #{plan_event.id}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ PlanGenerationEvent not found for user {test_user.username}"))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"  ✗ UserProfile not found for user {test_user.username}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Database validation error: {e}"))
        
        # === VALIDATION ===
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("VALIDATION RESULTS")
        self.stdout.write("=" * 80)
        
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
            
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(f"DAY {day_num}")
            self.stdout.write(f"{'=' * 80}")
            
            day_calories = 0
            day_protein = 0
            day_fat = 0
            day_carbs = 0
            day_has_vegetable = False
            day_dessert_count = 0
            day_structural_valid = True
            
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
            
            if day_cal_deviation <= 20 and day_pro_deviation <= 20:
                day_validation_notes.append("✓ Nutritional accuracy OK")
            elif day_cal_deviation <= 30 and day_pro_deviation <= 30:
                day_validation_notes.append("⚠ Nutritional accuracy acceptable")
            else:
                day_validation_notes.append("✗ Nutritional accuracy poor")
            
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
        
        # Calculate actual macro ratios from generated plan
        actual_protein_cal = total_protein * 4
        actual_fat_cal = total_fat * 9
        actual_carbs_cal = total_carbs * 4
        actual_total_cal = actual_protein_cal + actual_fat_cal + actual_carbs_cal
        
        actual_protein_ratio = (actual_protein_cal / actual_total_cal * 100) if actual_total_cal > 0 else 0
        actual_fat_ratio = (actual_fat_cal / actual_total_cal * 100) if actual_total_cal > 0 else 0
        actual_carbs_ratio = (actual_carbs_cal / actual_total_cal * 100) if actual_total_cal > 0 else 0
        
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
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("VALIDATION SUMMARY")
        self.stdout.write("-" * 80)
        
        self.stdout.write(f"\n[CLUSTER VALIDATION]")
        self.stdout.write(f"  Predicted Cluster: {predicted_cluster} ({predicted_cluster_name})")
        self.stdout.write(f"  Target Cluster: High-Carb / Low-Fat / Sugary (Cluster 2)")
        if cluster_id_match:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster prediction matches High-Carb target (Cluster 2)"))
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Cluster prediction doesn't match High-Carb target. Expected Cluster 2, got {predicted_cluster}"))
        
        self.stdout.write(f"\n[MACRONUTRIENT VALIDATION]")
        self.stdout.write(f"  Target Ratios: Protein {protein_ratio:.1f}%, Fat {fat_ratio:.1f}%, Carbs {carbs_ratio:.1f}%")
        self.stdout.write(f"  Actual Ratios: Protein {actual_protein_ratio:.1f}%, Fat {actual_fat_ratio:.1f}%, Carbs {actual_carbs_ratio:.1f}%")
        if actual_carbs_ratio >= 45:  # Allow some deviation
            self.stdout.write(self.style.SUCCESS(f"  ✓ High-carb profile confirmed: {actual_carbs_ratio:.1f}% carbs"))
        else:
            self.stdout.write(self.style.WARNING(f"  ⚠ Carbs at {actual_carbs_ratio:.1f}% (expected ≥45% for high-carb profile)"))
        
        self.stdout.write(f"\n[STRUCTURAL VALIDATION]")
        self.stdout.write(f"  Days Generated: {len(weekly_plan)}/{user_profile['number_of_days']}")
        self.stdout.write(f"  Unique Recipes: {len(all_recipe_ids)}")
        self.stdout.write(f"  Structural Errors: {len([e for e in validation_errors if 'Missing' in e or 'Must have' in e])}")
        
        self.stdout.write(f"\n[NUTRITIONAL ACCURACY]")
        self.stdout.write(f"  Calories: {total_calories:.0f} / {target_calories:.0f} ({cal_deviation:.1f}% deviation)")
        self.stdout.write(f"  Protein: {total_protein:.1f}g / {target_protein:.1f}g ({pro_deviation:.1f}% deviation)")
        self.stdout.write(f"  Fat: {total_fat:.1f}g / {target_fat:.1f}g ({fat_deviation:.1f}% deviation)")
        self.stdout.write(f"  Carbs: {total_carbs:.1f}g / {target_carbs:.1f}g ({carbs_deviation:.1f}% deviation)")
        
        self.stdout.write(f"\n[DATABASE LOGGING]")
        if database_logging_success:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Database logging successful"))
            self.stdout.write(f"    - UserProfile: Created/Updated")
            self.stdout.write(f"    - PlanGenerationEvent: Created")
            self.stdout.write(f"    - GeneratedPlan: Created")
        else:
            self.stdout.write(self.style.ERROR(f"  ✗ Database logging failed"))
            validation_errors.append("Database logging failed - data not persisted")
        
        if validation_errors:
            self.stdout.write(f"\n✗ Errors ({len(validation_errors)}):")
            for error in validation_errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        
        if validation_warnings:
            self.stdout.write(f"\n⚠ Warnings ({len(validation_warnings)}):")
            for warning in validation_warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
        
        # Final status
        self.stdout.write("\n" + "=" * 80)
        test_passed = len(validation_errors) == 0 and database_logging_success and cluster_id_match
        
        if test_passed:
            if len(validation_warnings) == 0:
                self.stdout.write(self.style.SUCCESS("✓ TEST PASSED (Excellent)"))
                self.stdout.write(self.style.SUCCESS("  - High-Carb cluster test completed successfully"))
                self.stdout.write(self.style.SUCCESS("  - Database logging verified"))
            else:
                self.stdout.write(self.style.SUCCESS("✓ TEST PASSED (with warnings)"))
                self.stdout.write(self.style.SUCCESS("  - High-Carb cluster test completed with minor warnings"))
                self.stdout.write(self.style.SUCCESS("  - Database logging verified"))
        else:
            self.stdout.write(self.style.ERROR("✗ TEST FAILED"))
            if not cluster_id_match:
                self.stdout.write(self.style.ERROR("  - Cluster prediction mismatch (expected Cluster 2)"))
            if not database_logging_success:
                self.stdout.write(self.style.ERROR("  - Database logging failed"))
            if len(validation_errors) > 0:
                self.stdout.write(self.style.ERROR(f"  - {len(validation_errors)} validation error(s)"))
        
        self.stdout.write("=" * 80 + "\n")
        
        # Cleanup: Optionally delete test user (comment out to keep for analysis)
        # test_user.delete()
