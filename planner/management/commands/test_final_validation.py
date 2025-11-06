# planner/management/commands/test_final_validation.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, calculate_nutritional_targets_from_profile, map_goal_to_cluster
from planner.models import Recipe
import gc
import time

class Command(BaseCommand):
    help = 'TIER 2: Comprehensive multi-scenario validation suite testing diverse user personas'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 80)
        self.stdout.write("TIER 2: MULTI-SCENARIO VALIDATION SUITE")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Comprehensive stress test across diverse user profiles")
        self.stdout.write("Use Case: Deep validation of rule-based personalization and optimization logic")
        self.stdout.write("=" * 80)
        
        # Prerequisite checks
        from planner.models import Recipe
        unclassified_count = Recipe.objects.filter(meal_type='Unknown').count()
        total_count = Recipe.objects.count()
        
        if total_count == 0:
            self.stdout.write(self.style.ERROR("\n[ERROR] No recipes found in database. Please run 'python manage.py load_recipes' first."))
            return
        
        if unclassified_count == total_count:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] All {total_count} recipes are unclassified. Please run 'python manage.py classify_meal_types' first."))
            return
        
        # Get cluster mapping for validation
        cluster_map = dict(Recipe.objects.values_list('cluster', 'cluster_name').distinct())
        
        # === DEFINE DIVERSE USER PERSONAS ===
        # Each persona is designed to test different nutritional clusters
        # Note: The system uses goal-based macro distributions:
        #   - lose_weight: 40% protein, 30% fat, 30% carbs
        #   - maintain: 20% protein, 30% fat, 50% carbs
        #   - gain_muscle: 40% protein, 20% fat, 40% carbs
        # Personas are reverse-engineered to produce macro ratios that map to specific clusters
        
        personas = [
            {
                'name': 'High-Protein / Muscle Gain',
                'user_profile': {
                    # System macro distribution for gain_muscle: 40% Protein, 20% Fat, 40% Carbs
                    # Reverse-engineered: Young, active male with muscle gain goal
                    # This should produce ~40% protein ratio, mapping to High-Protein cluster
                    'age': 25,
                    'gender': 'male',
                    'height_cm': 165.0,
                    'weight_kg': 55.0,
                    'activity_level': 'very_active',
                    'primary_goal': 'gain_muscle',
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'target_macro_ratios': {'protein': 0.40, 'fat': 0.20, 'carbs': 0.40},
                'expected_cluster_keywords': ['High-Protein'],
                'description': 'Active young male with muscle gain goal → 40% protein → High-Protein cluster'
            },
            {
                'name': 'Balanced / DASH Diet Style',
                'user_profile': {
                    # System macro distribution for maintain: 20% Protein, 30% Fat, 50% Carbs
                    # Reverse-engineered: Middle-aged person with maintenance goal
                    # This should produce balanced ratios, mapping to Balanced/High-Fiber cluster
                    'age': 40,
                    'gender': 'female',
                    'height_cm': 155.0,
                    'weight_kg': 49.0,
                    'activity_level': 'moderate',
                    'primary_goal': 'maintain',
                    'pace': 'moderate',
                    'number_of_days': 3,
                    'allergies': '',
                    'dislikes': ''
                },
                'target_macro_ratios': {'protein': 0.20, 'fat': 0.30, 'carbs': 0.50},
                'expected_cluster_keywords': ['Balanced'],
                'description': 'Balanced maintenance diet → 50% carbs, balanced macros → Balanced cluster'
            },
            {
                'name': 'High-Protein / Weight Loss',
                'user_profile': {
                    # System macro distribution for lose_weight: 40% Protein, 30% Fat, 30% Carbs
                    # Reverse-engineered: Person with weight loss goal
                    # This should produce high protein ratio, mapping to High-Protein cluster
                    'age': 35,
                    'gender': 'female',
                    'height_cm': 160.0,
                    'weight_kg': 70.0,
                    'activity_level': 'moderate',
                    'primary_goal': 'lose_weight',
                    'pace': 'moderate',
                    'number_of_days': 3,
                    'allergies': '',
                    'dislikes': ''
                },
                'target_macro_ratios': {'protein': 0.40, 'fat': 0.30, 'carbs': 0.30},
                'expected_cluster_keywords': ['High-Protein'],
                'description': 'Weight loss profile → 40% protein → High-Protein cluster'
            },
            {
                'name': 'Active Maintenance / High-Carb',
                'user_profile': {
                    # System macro distribution for maintain: 20% Protein, 30% Fat, 50% Carbs
                    # Reverse-engineered: Active person with maintenance goal
                    # This should produce 50% carbs (highest in system), potentially mapping to High-Carb cluster
                    'age': 30,
                    'gender': 'male',
                    'height_cm': 175.0,
                    'weight_kg': 70.0,
                    'activity_level': 'active',
                    'primary_goal': 'maintain',
                    'pace': 'moderate',
                    'number_of_days': 3,
                    'allergies': '',
                    'dislikes': ''
                },
                'target_macro_ratios': {'protein': 0.20, 'fat': 0.30, 'carbs': 0.50},
                'expected_cluster_keywords': ['Balanced', 'High-Carb'],
                'description': 'Active maintenance → 50% carbs (system max) → Balanced or High-Carb cluster'
            }
        ]
        
        persona_results = []
        
        for persona_idx, persona in enumerate(personas, 1):
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(f"PERSONA {persona_idx}/{len(personas)}: {persona['name']}")
            self.stdout.write("=" * 80)
            self.stdout.write(f"Description: {persona['description']}")
            self.stdout.write(f"\n[USER PROFILE]")
            self.stdout.write(f"  Age: {persona['user_profile']['age']}, Gender: {persona['user_profile']['gender']}")
            self.stdout.write(f"  Height: {persona['user_profile']['height_cm']} cm, Weight: {persona['user_profile']['weight_kg']} kg")
            self.stdout.write(f"  Activity: {persona['user_profile']['activity_level']}")
            self.stdout.write(f"  Goal: {persona['user_profile']['primary_goal']} (pace: {persona['user_profile']['pace']})")
            if persona['user_profile'].get('allergies'):
                self.stdout.write(f"  Allergies: {persona['user_profile']['allergies']}")
            if persona['user_profile'].get('dislikes'):
                self.stdout.write(f"  Dislikes: {persona['user_profile']['dislikes']}")
            
            # === PART 1: Calculate Nutritional Targets ===
            self.stdout.write(f"\n[PART 1: USER REQUEST ANALYZER]")
            try:
                daily_targets = calculate_nutritional_targets_from_profile(persona['user_profile'])
                self.stdout.write(self.style.SUCCESS(f"  ✓ Nutritional targets calculated successfully"))
                
                # Calculate actual macro ratios from targets
                total_calories = daily_targets['calories']
                protein_cal = daily_targets['protein_g'] * 4
                fat_cal = daily_targets['fat_g'] * 9
                carbs_cal = daily_targets['carbs_g'] * 4
                
                actual_protein_ratio = protein_cal / total_calories if total_calories > 0 else 0
                actual_fat_ratio = fat_cal / total_calories if total_calories > 0 else 0
                actual_carbs_ratio = carbs_cal / total_calories if total_calories > 0 else 0
                
                self.stdout.write(f"  Daily Targets: {daily_targets}")
                self.stdout.write(f"  Actual Macro Ratios: Protein {actual_protein_ratio*100:.1f}%, Fat {actual_fat_ratio*100:.1f}%, Carbs {actual_carbs_ratio*100:.1f}%")
                
                # Compare with target ratios
                target_ratios = persona.get('target_macro_ratios', {})
                if target_ratios:
                    self.stdout.write(f"  Target Macro Ratios: Protein {target_ratios.get('protein', 0)*100:.0f}%, Fat {target_ratios.get('fat', 0)*100:.0f}%, Carbs {target_ratios.get('carbs', 0)*100:.0f}%")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to calculate targets: {e}"))
                persona_results.append({
                    'persona': persona['name'],
                    'status': 'FAILED',
                    'error': f'Target calculation failed: {e}'
                })
                continue
            
            # === PART 2: Rule-Based Cluster Mapping ===
            self.stdout.write(f"\n[PART 2: SEMANTIC CLUSTER MAPPING]")
            primary_goal = persona['user_profile'].get('primary_goal', 'maintain')
            predicted_cluster = map_goal_to_cluster(primary_goal)
            predicted_cluster_name = cluster_map.get(predicted_cluster, "Unknown")
            
            self.stdout.write(f"  Primary Goal: {primary_goal}")
            self.stdout.write(f"  Rule-Based Cluster Selection: {predicted_cluster} ({predicted_cluster_name})")
            self.stdout.write(f"  Mapping Logic: primary_goal='{primary_goal}' → cluster={predicted_cluster}")
            
            # Verify cluster selection matches expectation
            cluster_match = any(keyword in predicted_cluster_name for keyword in persona['expected_cluster_keywords'])
            if cluster_match:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster selection matches expected: {persona['expected_cluster_keywords']}"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ Cluster selection ({predicted_cluster_name}) differs from expected {persona['expected_cluster_keywords']}"))
            
            # === PART 3 & 4: Generate Meal Plan ===
            self.stdout.write(f"\n[PART 3 & 4: GLOBAL DAILY OPTIMIZER & ORCHESTRATOR]")
            try:
                weekly_plan = generate_full_meal_plan(persona['user_profile'])
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan: {e}"))
                import traceback
                self.stdout.write(traceback.format_exc())
                persona_results.append({
                    'persona': persona['name'],
                    'status': 'FAILED',
                    'error': f'Plan generation failed: {e}',
                    'targets_calculated': daily_targets,
                    'cluster_prediction': predicted_cluster_name
                })
                continue
            
            if not weekly_plan:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan (returned None)"))
                persona_results.append({
                    'persona': persona['name'],
                    'status': 'FAILED',
                    'error': 'Plan generation returned None',
                    'targets_calculated': daily_targets,
                    'cluster_prediction': predicted_cluster_name
                })
                continue
            
            # === VALIDATION ===
            self.stdout.write(f"\n[VALIDATION]")
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(f"GENERATED MEAL PLAN DETAILS")
            self.stdout.write(f"{'=' * 80}")
            
            all_recipe_ids = set()
            validation_errors = []
            validation_warnings = []
            total_calories = 0
            total_protein = 0
            desserts_in_dinner = 0
            days_with_vegetables = 0
            
            # Calculate meal allocation ratios for target display
            meal_allocation_ratios = {
                'Breakfast': 0.25,
                'Lunch': 0.40,
                'Dinner': 0.35
            }
            
            for day_key in sorted(weekly_plan.keys()):
                day_plan = weekly_plan[day_key]
                day_num = day_key.split()[-1]
                day_has_vegetable = False
                
                self.stdout.write(f"\n{'=' * 80}")
                self.stdout.write(f"DAY {day_num}")
                self.stdout.write(f"{'=' * 80}")
                
                day_calories = 0
                day_protein = 0
                day_fat = 0
                day_carbs = 0
                day_dessert_count = 0
                
                # Check meal structure
                for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
                    if meal_name not in day_plan:
                        validation_errors.append(f"{day_key} - {meal_name}: Missing")
                        continue
                    
                    meal_recipes = day_plan[meal_name]
                    if not meal_recipes:
                        validation_errors.append(f"{day_key} - {meal_name}: Empty")
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
                        
                        # Track desserts in dinner
                        if meal_name == 'Dinner' and recipe_type == 'Dessert':
                            desserts_in_dinner += 1
                            day_dessert_count += 1
                        
                        # Track vegetables
                        if recipe_type in ['Side Dish', 'Salad', 'Soup']:
                            day_has_vegetable = True
                    
                    # Display meal totals
                    self.stdout.write(f"  Meal Totals: {meal_calories:.0f} kcal, {meal_protein:.1f}g protein")
                    
                    # Validate meal structure
                    if meal_name == 'Breakfast':
                        breakfast_items = [r for r in meal_recipes if r.get('meal_type') == 'Breakfast']
                        complementary = [r for r in meal_recipes if r.get('meal_type') in ['Fruit', 'Drink']]
                        if len(breakfast_items) != 1:
                            validation_errors.append(f"{day_key} - {meal_name}: Must have 1 Breakfast item (found {len(breakfast_items)})")
                        if len(complementary) < 1:
                            validation_errors.append(f"{day_key} - {meal_name}: Missing Fruit/Drink")
                    else:  # Lunch/Dinner
                        main_courses = [r for r in meal_recipes if r.get('meal_type') == 'Main Course']
                        if len(main_courses) != 1:
                            validation_errors.append(f"{day_key} - {meal_name}: Must have 1 Main Course (found {len(main_courses)})")
                
                # Daily nutrition summary with target comparison
                total_calories += day_calories
                total_protein += day_protein
                
                # Calculate daily deviations
                target_cal = daily_targets['calories']
                target_pro = daily_targets['protein_g']
                
                day_cal_deviation = abs(day_calories - target_cal) / target_cal * 100 if target_cal > 0 else 0
                day_pro_deviation = abs(day_protein - target_pro) / target_pro * 100 if target_pro > 0 else 0
                
                # Display daily totals
                self.stdout.write(f"\n  [DAY {day_num} TOTALS]")
                self.stdout.write(f"    Actual: {day_calories:.0f} kcal, {day_protein:.1f}g protein")
                self.stdout.write(f"    Target: {target_cal:.0f} kcal, {target_pro:.1f}g protein")
                self.stdout.write(f"    Deviation: {day_cal_deviation:.1f}% (Cal), {day_pro_deviation:.1f}% (Pro)")
                
                # Daily validation status
                day_validation_notes = []
                # Check for structural errors for this day
                day_structural_errors = [e for e in validation_errors if day_key in e and ('Missing' in e or 'Must have' in e)]
                if not day_structural_errors:
                    day_validation_notes.append("✓ Structural integrity OK")
                else:
                    day_validation_notes.append("✗ Structural issues detected")
                
                day_validation_notes.append("✓ Includes vegetables" if day_has_vegetable else "⚠ No vegetables")
                day_validation_notes.append(f"✓ Dessert count OK ({day_dessert_count})" if day_dessert_count <= 1 else f"✗ {day_dessert_count} desserts (max 1)")
                if day_cal_deviation <= 20 and day_pro_deviation <= 20:
                    day_validation_notes.append("✓ Nutritional accuracy OK")
                elif day_cal_deviation <= 30 and day_pro_deviation <= 30:
                    day_validation_notes.append("⚠ Nutritional accuracy acceptable")
                else:
                    day_validation_notes.append("✗ Nutritional accuracy poor")
                
                self.stdout.write(f"  [DAY {day_num} VALIDATION] {', '.join(day_validation_notes)}")
                
                if day_has_vegetable:
                    days_with_vegetables += 1
            
            # Weekly totals summary
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(f"WEEKLY TOTALS SUMMARY")
            self.stdout.write(f"{'=' * 80}")
            
            # Check nutritional accuracy
            target_calories = daily_targets['calories'] * len(weekly_plan)
            target_protein = daily_targets['protein_g'] * len(weekly_plan)
            cal_deviation = abs(total_calories - target_calories) / target_calories * 100 if target_calories > 0 else 0
            pro_deviation = abs(total_protein - target_protein) / target_protein * 100 if target_protein > 0 else 0
            
            self.stdout.write(f"\n  Actual Total: {total_calories:.0f} kcal, {total_protein:.1f}g protein")
            self.stdout.write(f"  Target Total: {target_calories:.0f} kcal, {target_protein:.1f}g protein")
            self.stdout.write(f"  Deviation: {cal_deviation:.1f}% (Cal), {pro_deviation:.1f}% (Pro)")
            self.stdout.write(f"  Unique Recipes: {len(all_recipe_ids)}")
            self.stdout.write(f"  Days with Vegetables: {days_with_vegetables}/{len(weekly_plan)}")
            self.stdout.write(f"  Desserts in Dinner: {desserts_in_dinner}")
            
            if cal_deviation > 30:
                validation_errors.append(f"Calorie deviation too high: {cal_deviation:.1f}%")
            elif cal_deviation > 20:
                validation_warnings.append(f"Calorie deviation: {cal_deviation:.1f}%")
            
            if pro_deviation > 30:
                validation_errors.append(f"Protein deviation too high: {pro_deviation:.1f}%")
            elif pro_deviation > 20:
                validation_warnings.append(f"Protein deviation: {pro_deviation:.1f}%")
            
            # Check dessert availability
            if desserts_in_dinner == 0:
                validation_warnings.append("No desserts found in any dinner")
            
            # Persona result
            status = 'PASSED' if len(validation_errors) == 0 else 'FAILED'
            persona_results.append({
                'persona': persona['name'],
                'status': status,
                'targets_calculated': daily_targets,
                'cluster_prediction': predicted_cluster_name,
                'cluster_match': cluster_match,
                'plan_generated': True,
                'days_generated': len(weekly_plan),
                'unique_recipes': len(all_recipe_ids),
                'errors': len(validation_errors),
                'warnings': len(validation_warnings),
                'desserts_in_dinner': desserts_in_dinner,
                'days_with_vegetables': days_with_vegetables,
                'cal_deviation': cal_deviation,
                'pro_deviation': pro_deviation
            })
            
            # Report results
            self.stdout.write(f"  Status: {status}")
            self.stdout.write(f"  Days Generated: {len(weekly_plan)}/{persona['user_profile']['number_of_days']}")
            self.stdout.write(f"  Unique Recipes: {len(all_recipe_ids)}")
            self.stdout.write(f"  Days with Vegetables: {days_with_vegetables}/{len(weekly_plan)}")
            self.stdout.write(f"  Desserts in Dinner: {desserts_in_dinner}")
            self.stdout.write(f"  Nutritional Accuracy: Calories {cal_deviation:.1f}%, Protein {pro_deviation:.1f}%")
            
            if validation_errors:
                self.stdout.write(self.style.ERROR(f"  Errors ({len(validation_errors)}):"))
                for error in validation_errors[:5]:
                    self.stdout.write(self.style.ERROR(f"    - {error}"))
            
            if validation_warnings:
                self.stdout.write(self.style.WARNING(f"  Warnings ({len(validation_warnings)}):"))
                for warning in validation_warnings[:3]:
                    self.stdout.write(self.style.WARNING(f"    - {warning}"))
            
            if status == 'PASSED':
                self.stdout.write(self.style.SUCCESS(f"  ✓ Persona PASSED"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Persona FAILED"))
            
            # Cleanup between personas
            del weekly_plan
            del all_recipe_ids
            gc.collect()
            if persona_idx < len(personas):
                time.sleep(0.5)
        
        # === FINAL SUMMARY REPORT ===
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("FINAL VALIDATION SUMMARY")
        self.stdout.write("=" * 80)
        
        passed = sum(1 for r in persona_results if r['status'] == 'PASSED')
        failed = len(persona_results) - passed
        
        self.stdout.write(f"\nTest Summary:")
        self.stdout.write(f"  Total Personas: {len(persona_results)}")
        self.stdout.write(f"  Passed: {passed}")
        self.stdout.write(f"  Failed: {failed}")
        
        self.stdout.write(f"\nAI Cluster Prediction Accuracy:")
        cluster_matches = sum(1 for r in persona_results if r.get('cluster_match', False))
        self.stdout.write(f"  Correct Cluster Predictions: {cluster_matches}/{len(persona_results)}")
        
        self.stdout.write(f"\nDessert Pool Validation:")
        desserts_found = sum(1 for r in persona_results if r.get('desserts_in_dinner', 0) > 0)
        self.stdout.write(f"  Scenarios with Desserts in Dinner: {desserts_found}/{len(persona_results)}")
        
        self.stdout.write(f"\nDetailed Results:")
        for result in persona_results:
            status_icon = "✓" if result['status'] == 'PASSED' else "✗"
            self.stdout.write(f"  {status_icon} {result['persona']}: {result['status']}")
            if result.get('targets_calculated'):
                targets = result['targets_calculated']
                self.stdout.write(f"    Targets: {targets['calories']:.0f} kcal, {targets['protein_g']:.0f}g protein")
            self.stdout.write(f"    Cluster: {result.get('cluster_prediction', 'N/A')} {'(match)' if result.get('cluster_match') else '(no match)'}")
            self.stdout.write(f"    Recipes: {result.get('unique_recipes', 0)} unique, {result.get('errors', 0)} errors, {result.get('warnings', 0)} warnings")
        
        # Overall Status
        self.stdout.write("\n" + "-" * 80)
        if failed == 0 and cluster_matches == len(persona_results):
            self.stdout.write(self.style.SUCCESS("OVERALL STATUS: ✅ ALL VALIDATIONS PASSED - SYSTEM READY"))
        elif failed == 0:
            self.stdout.write(self.style.WARNING("OVERALL STATUS: ⚠️ PLANS GENERATED BUT SOME CLUSTER PREDICTIONS UNEXPECTED"))
        else:
            self.stdout.write(self.style.ERROR(f"OVERALL STATUS: ❌ {failed} PERSONA(S) FAILED - REVIEW REQUIRED"))
        
        self.stdout.write("=" * 80 + "\n")
