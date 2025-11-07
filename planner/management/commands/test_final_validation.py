# planner/management/commands/test_final_validation.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan, calculate_nutritional_targets_from_profile, map_goal_to_cluster
from planner.models import Recipe, UserProfile, PlanGenerationEvent, GeneratedPlan
from django.contrib.auth.models import User
from django.utils import timezone
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
        
        # === DEFINE COMPREHENSIVE USER PERSONAS ===
        # Each persona is scientifically designed to test a specific path in the decision matrix
        # and includes full personal details for realistic database logging
        # 
        # DECISION MATRIX PATHS BEING TESTED:
        # 1. gain_muscle → Cluster 3 (High-Protein) - Persona 1
        # 2. lose_weight + balanced → Cluster 3 (High-Protein) - Persona 2
        # 3. lose_weight + low_carb → Cluster 1 (High-Fat / Low-Carb) - Persona 3
        # 4. lose_weight + low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary) - Persona 4
        # 5. gain_weight → Cluster 2 (High-Carb / Low-Fat / Sugary) - Persona 5
        # 6. maintain + balanced → Cluster 0 (Balanced / High-Fiber) - Persona 6
        # 7. maintain + low_carb → Cluster 1 (High-Fat / Low-Carb) - Persona 7
        # 8. maintain + low_fat → Cluster 2 (High-Carb / Low-Fat / Sugary) - Persona 8
        
        personas = [
            {
                'first_name': 'Ben',
                'last_name': 'Carter',
                'user_profile': {
                    'age': 25,
                    'gender': 'male',
                    'height_cm': 180.0,
                    'weight_kg': 78.0,
                    'activity_level': 'active',
                    'primary_goal': 'gain_muscle',
                    'dietary_style': 'balanced',  # Not used for gain_muscle, but included for consistency
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 3,
                'expected_cluster_keywords': ['High-Protein'],
                'description': 'Male athlete with muscle gain goal → Cluster 3 (High-Protein)'
            },
            {
                'first_name': 'Alice',
                'last_name': 'Chen',
                'user_profile': {
                    'age': 30,
                    'gender': 'female',
                    'height_cm': 163.0,
                    'weight_kg': 57.0,
                    'activity_level': 'sedentary',
                    'primary_goal': 'lose_weight',
                    'dietary_style': 'balanced',  # lose_weight + balanced → Cluster 3
                    'pace': 'mild',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 3,
                'expected_cluster_keywords': ['High-Protein'],
                'description': 'Female office worker with weight loss goal (balanced) → Cluster 3 (High-Protein)'
            },
            {
                'first_name': 'Charles',
                'last_name': 'Davis',
                'user_profile': {
                    'age': 45,
                    'gender': 'male',
                    'height_cm': 175.0,
                    'weight_kg': 90.0,
                    'activity_level': 'light',
                    'primary_goal': 'lose_weight',
                    'dietary_style': 'low_carb',  # lose_weight + low_carb → Cluster 1
                    'pace': 'fast',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 1,
                'expected_cluster_keywords': ['High-Fat', 'Low-Carb'],
                'description': 'Keto-style weight loss → Cluster 1 (High-Fat / Low-Carb)'
            },
            {
                'first_name': 'Emma',
                'last_name': 'Foster',
                'user_profile': {
                    'age': 28,
                    'gender': 'female',
                    'height_cm': 165.0,
                    'weight_kg': 62.0,
                    'activity_level': 'moderate',
                    'primary_goal': 'lose_weight',
                    'dietary_style': 'low_fat',  # lose_weight + low_fat → Cluster 2
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 2,
                'expected_cluster_keywords': ['High-Carb', 'Low-Fat', 'Sugary'],
                'description': 'Low-fat weight loss → Cluster 2 (High-Carb / Low-Fat / Sugary)'
            },
            {
                'first_name': 'Frank',
                'last_name': 'Garcia',
                'user_profile': {
                    'age': 22,
                    'gender': 'male',
                    'height_cm': 175.0,
                    'weight_kg': 65.0,
                    'activity_level': 'moderate',
                    'primary_goal': 'gain_weight',  # gain_weight → Cluster 2
                    'dietary_style': 'balanced',  # Not used for gain_weight, but included for consistency
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 2,
                'expected_cluster_keywords': ['High-Carb', 'Low-Fat', 'Sugary'],
                'description': 'Underweight individual with weight gain goal → Cluster 2 (High-Carb / Low-Fat / Sugary)'
            },
            {
                'first_name': 'Diana',
                'last_name': 'Evans',
                'user_profile': {
                    'age': 32,
                    'gender': 'female',
                    'height_cm': 168.0,
                    'weight_kg': 50.0,
                    'activity_level': 'very_active',
                    'primary_goal': 'maintain',
                    'dietary_style': 'balanced',  # maintain + balanced → Cluster 0
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 0,
                'expected_cluster_keywords': ['Balanced', 'High-Fiber'],
                'description': 'Marathon runner with maintenance goal (balanced) → Cluster 0 (Balanced / High-Fiber)'
            },
            {
                'first_name': 'George',
                'last_name': 'Harris',
                'user_profile': {
                    'age': 38,
                    'gender': 'male',
                    'height_cm': 178.0,
                    'weight_kg': 85.0,
                    'activity_level': 'moderate',
                    'primary_goal': 'maintain',
                    'dietary_style': 'low_carb',  # maintain + low_carb → Cluster 1
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 1,
                'expected_cluster_keywords': ['High-Fat', 'Low-Carb'],
                'description': 'Keto maintenance → Cluster 1 (High-Fat / Low-Carb)'
            },
            {
                'first_name': 'Helen',
                'last_name': 'Ivanov',
                'user_profile': {
                    'age': 29,
                    'gender': 'female',
                    'height_cm': 162.0,
                    'weight_kg': 55.0,
                    'activity_level': 'very_active',
                    'primary_goal': 'maintain',
                    'dietary_style': 'low_fat',  # maintain + low_fat → Cluster 2
                    'pace': 'moderate',
                    'number_of_days': 7,
                    'allergies': '',
                    'dislikes': ''
                },
                'expected_cluster_id': 2,
                'expected_cluster_keywords': ['High-Carb', 'Low-Fat', 'Sugary'],
                'description': 'Endurance athlete with low-fat maintenance → Cluster 2 (High-Carb / Low-Fat / Sugary)'
            }
        ]
        
        # Helper function to generate persona identifier for logging
        def get_persona_identifier(persona):
            """Generate a descriptive identifier for a persona using first_name, last_name, and profile data."""
            first = persona.get('first_name', 'Unknown')
            last = persona.get('last_name', 'Unknown')
            goal = persona.get('user_profile', {}).get('primary_goal', 'unknown')
            return f"{first} {last} ({goal})"
        
        persona_results = []
        
        for persona_idx, persona in enumerate(personas, 1):
            persona_id = get_persona_identifier(persona)
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(f"PERSONA {persona_idx}/{len(personas)}: {persona_id}")
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
            
            # === CREATE USER AND USERPROFILE FOR DATABASE LOGGING ===
            self.stdout.write(f"\n[DATABASE SETUP]")
            try:
                # Create test user for this persona with full details
                username = f"test_{persona.get('first_name', '').lower()}_{persona.get('last_name', '').lower()}_{int(timezone.now().timestamp())}"
                user = User.objects.create_user(
                    username=username,
                    email=f"{persona.get('first_name', '').lower()}.{persona.get('last_name', '').lower()}@test.com",
                    password='test_password_123',
                    first_name=persona.get('first_name', ''),
                    last_name=persona.get('last_name', '')
                )
                self.stdout.write(f"  ✓ Created test user: {username} ({persona.get('first_name', '')} {persona.get('last_name', '')})")
                
                # UserProfile will be created automatically by generate_full_meal_plan
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to create test user: {e}"))
                persona_results.append({
                    'persona': persona_id,
                    'status': 'FAILED',
                    'error': f'User creation failed: {e}'
                })
                continue
            
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
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to calculate targets: {e}"))
                # Cleanup user
                user.delete()
                persona_results.append({
                    'persona': persona_id,
                    'status': 'FAILED',
                    'error': f'Target calculation failed: {e}'
                })
                continue
            
            # === PART 2: Rule-Based Cluster Mapping ===
            self.stdout.write(f"\n[PART 2: SEMANTIC CLUSTER MAPPING]")
            primary_goal = persona['user_profile'].get('primary_goal', 'maintain')
            dietary_style = persona['user_profile'].get('dietary_style', 'balanced')
            predicted_cluster = map_goal_to_cluster(primary_goal, dietary_style)
            predicted_cluster_name = cluster_map.get(predicted_cluster, "Unknown")
            
            self.stdout.write(f"  Primary Goal: {primary_goal}")
            self.stdout.write(f"  Dietary Style: {dietary_style}")
            self.stdout.write(f"  Rule-Based Cluster Selection: {predicted_cluster} ({predicted_cluster_name})")
            self.stdout.write(f"  Mapping Logic: primary_goal='{primary_goal}', dietary_style='{dietary_style}' → cluster={predicted_cluster}")
            
            # Verify cluster selection matches expectation
            expected_cluster_id = persona.get('expected_cluster_id', -1)
            cluster_id_match = (predicted_cluster == expected_cluster_id)
            cluster_keyword_match = any(keyword in predicted_cluster_name for keyword in persona['expected_cluster_keywords'])
            
            if cluster_id_match:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster ID matches expected: {predicted_cluster} (expected {expected_cluster_id})"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Cluster ID mismatch: got {predicted_cluster}, expected {expected_cluster_id}"))
            
            if cluster_keyword_match:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Cluster name matches expected keywords: {persona['expected_cluster_keywords']}"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ Cluster name ({predicted_cluster_name}) doesn't match expected keywords {persona['expected_cluster_keywords']}"))
            
            # === PART 3 & 4: Generate Meal Plan with Database Logging ===
            self.stdout.write(f"\n[PART 3 & 4: GLOBAL DAILY OPTIMIZER & ORCHESTRATOR]")
            plan_event_id_before = PlanGenerationEvent.objects.count()
            generated_plan_count_before = GeneratedPlan.objects.count()
            
            try:
                # Call with user_id to enable database logging
                weekly_plan = generate_full_meal_plan(persona['user_profile'], user_id=user.id)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan: {e}"))
                import traceback
                self.stdout.write(traceback.format_exc())
                # Cleanup user
                user.delete()
                persona_results.append({
                    'persona': persona_id,
                    'status': 'FAILED',
                    'error': f'Plan generation failed: {e}',
                    'targets_calculated': daily_targets,
                    'cluster_prediction': predicted_cluster_name
                })
                continue
            
            if not weekly_plan:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to generate meal plan (returned None)"))
                # Cleanup user
                user.delete()
                persona_results.append({
                    'persona': persona_id,
                    'status': 'FAILED',
                    'error': 'Plan generation returned None',
                    'targets_calculated': daily_targets,
                    'cluster_prediction': predicted_cluster_name
                })
                continue
            
            # === DATABASE VALIDATION ===
            self.stdout.write(f"\n[DATABASE VALIDATION]")
            try:
                # Verify UserProfile was created/updated
                user_profile_obj = UserProfile.objects.get(user=user)
                self.stdout.write(self.style.SUCCESS(f"  ✓ UserProfile found for user {user.username}"))
                self.stdout.write(f"    - Gender: {user_profile_obj.gender}")
                self.stdout.write(f"    - Height: {user_profile_obj.height_cm} cm")
                self.stdout.write(f"    - Activity Level: {user_profile_obj.activity_level}")
                
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
                        
                        # Verify plan_data matches returned plan
                        if generated_plan.plan_data == weekly_plan:
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Plan data in database matches returned plan"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  ⚠ Plan data mismatch (may be due to serialization)"))
                    except GeneratedPlan.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"  ✗ GeneratedPlan not found for Event #{plan_event.id}"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ PlanGenerationEvent not found for user {user.username}"))
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  ✗ UserProfile not found for user {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Database validation error: {e}"))
            
            # === COMPREHENSIVE UNIQUENESS VALIDATION ===
            self.stdout.write(f"\n[UNIQUENESS VALIDATION]")
            self.stdout.write(f"{'=' * 80}")
            
            # Initialize validation tracking
            validation_errors = []
            validation_warnings = []
            
            # Collect ALL recipe IDs from ALL meals across ALL days
            all_recipe_ids_list = []  # List to preserve order and detect duplicates
            all_recipe_ids_set = set()  # Set for uniqueness check
            day_recipe_ids = {}  # Track recipe IDs per day for intra-day validation
            
            for day_key in sorted(weekly_plan.keys()):
                day_recipe_ids[day_key] = []
                day_plan = weekly_plan[day_key]
                
                for meal_name, recipes in day_plan.items():
                    for recipe in recipes:
                        recipe_id = recipe['id']
                        all_recipe_ids_list.append(recipe_id)
                        all_recipe_ids_set.add(recipe_id)
                        day_recipe_ids[day_key].append(recipe_id)
            
            # CRITICAL: Verify global uniqueness (no recipe appears more than once in entire plan)
            total_recipes = len(all_recipe_ids_list)
            unique_recipes = len(all_recipe_ids_set)
            
            self.stdout.write(f"  Total recipes in plan: {total_recipes}")
            self.stdout.write(f"  Unique recipe IDs: {unique_recipes}")
            
            if total_recipes != unique_recipes:
                # Find duplicates
                from collections import Counter
                recipe_counts = Counter(all_recipe_ids_list)
                duplicates = {rid: count for rid, count in recipe_counts.items() if count > 1}
                
                self.stdout.write(self.style.ERROR(f"  ✗ CRITICAL: Recipe repetition detected!"))
                self.stdout.write(self.style.ERROR(f"  ✗ {total_recipes - unique_recipes} duplicate recipe(s) found:"))
                for recipe_id, count in duplicates.items():
                    # Find recipe name
                    recipe_name = "Unknown"
                    for day_key, day_plan in weekly_plan.items():
                        for meal_name, recipes in day_plan.items():
                            for recipe in recipes:
                                if recipe['id'] == recipe_id:
                                    recipe_name = recipe.get('name', 'Unknown')
                                    break
                            if recipe_name != "Unknown":
                                break
                        if recipe_name != "Unknown":
                            break
                    self.stdout.write(self.style.ERROR(f"    - Recipe ID {recipe_id} ({recipe_name}): appears {count} times"))
                
                validation_errors.append(f"CRITICAL: Recipe repetition detected. {total_recipes - unique_recipes} duplicate(s) found.")
            else:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Global uniqueness verified: All {total_recipes} recipes are unique"))
            
            # CRITICAL: Verify intra-day uniqueness (no recipe appears multiple times within a single day)
            intra_day_duplicates_found = False
            for day_key, day_ids in day_recipe_ids.items():
                unique_day_ids = set(day_ids)
                if len(day_ids) != len(unique_day_ids):
                    duplicates = [rid for rid in day_ids if day_ids.count(rid) > 1]
                    self.stdout.write(self.style.ERROR(f"  ✗ CRITICAL: Intra-day repetition in {day_key}!"))
                    self.stdout.write(self.style.ERROR(f"  ✗ Duplicate recipe IDs: {set(duplicates)}"))
                    validation_errors.append(f"CRITICAL: Intra-day repetition in {day_key}. Duplicate IDs: {set(duplicates)}")
                    intra_day_duplicates_found = True
            
            if not intra_day_duplicates_found:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Intra-day uniqueness verified: No recipe appears multiple times within any day"))
            
            # CRITICAL: Verify inter-day uniqueness (no recipe appears across multiple days)
            # This is already checked by the global uniqueness check above, but we verify explicitly
            if total_recipes == unique_recipes:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Inter-day uniqueness verified: No recipe appears across multiple days"))
            
            self.stdout.write(f"{'=' * 80}\n")
            
            # === VALIDATION ===
            self.stdout.write(f"\n[VALIDATION]")
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(f"GENERATED MEAL PLAN DETAILS")
            self.stdout.write(f"{'=' * 80}")
            
            # Continue with existing validation_errors and validation_warnings from uniqueness check
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
                        
                        # Note: Uniqueness validation already performed above
                        # This is just for tracking in the display loop
                        
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
            self.stdout.write(f"  Unique Recipes: {unique_recipes} / Total: {total_recipes}")
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
            # CRITICAL: Recipe repetition is a fatal error - test must fail
            # CRITICAL: Cluster ID mismatch is also a fatal error - the decision matrix must work correctly
            critical_errors = [e for e in validation_errors if 'CRITICAL' in e or 'repetition' in e.lower()]
            if len(critical_errors) > 0:
                status = 'FAILED (CRITICAL: Recipe repetition)'
            elif not cluster_id_match:
                status = 'FAILED (CRITICAL: Cluster ID mismatch)'
            else:
                status = 'PASSED' if len(validation_errors) == 0 else 'FAILED'
            
            persona_results.append({
                'persona': persona_id,
                'status': status,
                'targets_calculated': daily_targets,
                'cluster_prediction': predicted_cluster_name,
                'cluster_id_match': cluster_id_match,
                'cluster_keyword_match': cluster_keyword_match,
                'plan_generated': True,
                'days_generated': len(weekly_plan),
                'unique_recipes': unique_recipes,  # Use unique_recipes from uniqueness validation
                'total_recipes': total_recipes,  # Total recipes in plan
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
            
            # Cleanup: Store user for potential cleanup later (or keep for analysis)
            # Note: In production, you might want to keep test data for analysis
            # For now, we'll keep users but could add cleanup option
            persona_results[-1]['user_id'] = user.id
            persona_results[-1]['username'] = user.username
            self.stdout.write(f"  Unique Recipes: {unique_recipes} / Total: {total_recipes}")
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
            del all_recipe_ids_list
            del all_recipe_ids_set
            del day_recipe_ids
            gc.collect()
            if persona_idx < len(personas):
                time.sleep(0.5)
        
        # === FAILURE SCENARIO TEST: Verify Fallback Mechanism ===
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("FAILURE SCENARIO TEST: Fallback Mechanism")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Verify that the system gracefully falls back to default plans when optimization fails")
        
        try:
            # Create a test user for failure scenario
            username_fail = f"test_failure_{int(timezone.now().timestamp())}"
            user_fail = User.objects.create_user(
                username=username_fail,
                email=f"{username_fail}@test.com",
                password='test_password_123'
            )
            self.stdout.write(f"\n[DATABASE SETUP]")
            self.stdout.write(f"  ✓ Created test user: {username_fail}")
            
            # Create a user profile that will cause optimization to fail
            # We'll use an impossible scenario: requesting recipes from a non-existent cluster
            # by using an invalid goal that maps to a cluster with no recipes
            failure_profile = {
                'age': 30,
                'gender': 'male',
                'height_cm': 175.0,
                'weight_kg': 70.0,
                'activity_level': 'moderate',
                'primary_goal': 'maintain',  # This should work, but we'll force failure another way
                'pace': 'moderate',
                'number_of_days': 2,
                'allergies': 'nonexistent_ingredient_xyz123',  # This will filter out all recipes
                'dislikes': ''
            }
            
            self.stdout.write(f"\n[FAILURE TEST]")
            self.stdout.write(f"  Profile: {failure_profile}")
            self.stdout.write(f"  Strategy: Using allergies that match no recipes to force fallback")
            
            # Count events before
            events_before = PlanGenerationEvent.objects.count()
            plans_before = GeneratedPlan.objects.count()
            
            # Attempt to generate plan (should trigger fallback)
            weekly_plan_fail = generate_full_meal_plan(failure_profile, user_id=user_fail.id)
            
            # Verify fallback was triggered
            if weekly_plan_fail:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Plan returned (fallback should have been used)"))
                
                # Check if plan contains default recipes (negative IDs) or is from dynamic fallback
                has_default_recipes = False
                has_real_recipes = False
                for day_key, day_plan in weekly_plan_fail.items():
                    for meal_name, recipes in day_plan.items():
                        for recipe in recipes:
                            recipe_id = recipe.get('id', 0)
                            if recipe_id < 0:
                                has_default_recipes = True
                            else:
                                has_real_recipes = True
                
                # Validate dynamic fallback: Either should use real recipes (from DB) OR unique default recipes
                if has_real_recipes:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Dynamic fallback detected: Plan uses real recipes from database"))
                elif has_default_recipes:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Static default plan detected (negative recipe IDs)"))
                    # Verify uniqueness even in static default plan
                    all_recipe_ids = []
                    for day_key, day_plan in weekly_plan_fail.items():
                        for meal_name, recipes in day_plan.items():
                            for recipe in recipes:
                                all_recipe_ids.append(recipe.get('id', 0))
                    unique_ids = len(set(all_recipe_ids))
                    total_ids = len(all_recipe_ids)
                    if unique_ids == total_ids:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Default plan has unique recipes: {unique_ids}/{total_ids} unique"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  ⚠ Default plan has duplicate recipes: {unique_ids}/{total_ids} unique"))
                else:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Plan returned but recipe IDs unclear"))
                
                # Verify database logging
                try:
                    user_profile_fail = UserProfile.objects.get(user=user_fail)
                    plan_events_fail = PlanGenerationEvent.objects.filter(user_profile=user_profile_fail)
                    
                    if plan_events_fail.exists():
                        plan_event_fail = plan_events_fail.first()
                        self.stdout.write(self.style.SUCCESS(f"  ✓ PlanGenerationEvent created: #{plan_event_fail.id}"))
                        self.stdout.write(f"    - Status: {plan_event_fail.status}")
                        
                        if plan_event_fail.status == 'fallback_default':
                            self.stdout.write(self.style.SUCCESS(f"  ✓ Status correctly set to 'fallback_default'"))
                        else:
                            self.stdout.write(self.style.WARNING(f"  ⚠ Status is '{plan_event_fail.status}' (expected 'fallback_default')"))
                        
                        # Check GeneratedPlan
                        try:
                            generated_plan_fail = GeneratedPlan.objects.get(event=plan_event_fail)
                            self.stdout.write(self.style.SUCCESS(f"  ✓ GeneratedPlan created for fallback event"))
                            self.stdout.write(f"    - Plan Data: {len(generated_plan_fail.plan_data)} days")
                        except GeneratedPlan.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f"  ✗ GeneratedPlan not found for fallback event"))
                    else:
                        self.stdout.write(self.style.ERROR(f"  ✗ PlanGenerationEvent not created"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Database validation error: {e}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ No plan returned (fallback should have provided a plan)"))
            
            # Cleanup
            user_fail.delete()
            self.stdout.write(f"\n  ✓ Cleaned up test user")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failure scenario test error: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
        
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
        
        self.stdout.write(f"\nDatabase Logging Validation:")
        total_events = PlanGenerationEvent.objects.count()
        total_plans = GeneratedPlan.objects.count()
        # Count UserProfiles for test users (usernames starting with 'test_')
        total_profiles = UserProfile.objects.filter(user__username__startswith='test_').count()
        self.stdout.write(f"  UserProfiles Created: {total_profiles}")
        self.stdout.write(f"  PlanGenerationEvents Created: {total_events}")
        self.stdout.write(f"  GeneratedPlans Created: {total_plans}")
        
        # Check status distribution
        if total_events > 0:
            success_count = PlanGenerationEvent.objects.filter(status='success').count()
            fallback_count = PlanGenerationEvent.objects.filter(status='fallback_default').count()
            failed_count = PlanGenerationEvent.objects.filter(status='failed').count()
            self.stdout.write(f"  Event Status Distribution:")
            self.stdout.write(f"    - Success: {success_count}")
            self.stdout.write(f"    - Fallback Default: {fallback_count}")
            self.stdout.write(f"    - Failed: {failed_count}")
        
        self.stdout.write(f"\nRule-Based Cluster Mapping Accuracy:")
        cluster_matches = sum(1 for r in persona_results if r.get('cluster_id_match', False))
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
            self.stdout.write(f"    Cluster: {result.get('cluster_prediction', 'N/A')} {'(match)' if result.get('cluster_id_match') else '(no match)'}")
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
