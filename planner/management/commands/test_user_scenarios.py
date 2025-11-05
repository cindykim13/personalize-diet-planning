# planner/management/commands/test_user_scenarios.py

from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan
from planner.models import Recipe

class Command(BaseCommand):
    help = 'Tests meal plan generation for different user personas and nutritional scenarios'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 70)
        self.stdout.write("USER SCENARIO TESTING SUITE")
        self.stdout.write("=" * 70)
        
        # Prerequisite check
        total_recipes = Recipe.objects.count()
        main_course_count = Recipe.objects.filter(meal_type='Main Course').count()
        classified_count = Recipe.objects.exclude(meal_type='Unknown').count()
        
        if total_recipes == 0:
            self.stdout.write(self.style.ERROR("\n[ERROR] No recipes found. Run 'python manage.py load_recipes' first."))
            return
        
        classification_pct = (classified_count / total_recipes * 100) if total_recipes > 0 else 0
        
        self.stdout.write(f"\n[INFO] Database: {total_recipes} recipes, {main_course_count} Main Courses, {classification_pct:.1f}% classified\n")
        
        # Test scenarios
        scenarios = [
            {
                'name': 'Active Adult - Muscle Gain',
                'target_nutrients': {'calories': 2600, 'protein_g': 180, 'fat_g': 87, 'carbs_g': 260},
                'number_of_days': 7
            },
            {
                'name': 'Standard Adult - Balanced Diet',
                'target_nutrients': {'calories': 2200, 'protein_g': 120, 'fat_g': 73, 'carbs_g': 200},
                'number_of_days': 7
            },
            {
                'name': 'Short-Term Plan (3 Days)',
                'target_nutrients': {'calories': 2200, 'protein_g': 120, 'fat_g': 73, 'carbs_g': 200},
                'number_of_days': 3
            }
        ]
        
        results = []
        for scenario_idx, scenario in enumerate(scenarios, 1):
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(f"SCENARIO {scenario_idx}: {scenario['name']}")
            self.stdout.write(f"{'=' * 70}")
            
            user_request = {
                'number_of_days': scenario['number_of_days'],
                'target_nutrients': scenario['target_nutrients'],
                'allergies': [],
                'dislikes': []
            }
            
            self.stdout.write(f"\n[TEST] Generating {scenario['number_of_days']}-day plan...")
            weekly_plan = generate_full_meal_plan(user_request)
            
            if not weekly_plan:
                self.stdout.write(self.style.ERROR(f"[FAILED] Plan generation failed"))
                results.append({'scenario': scenario['name'], 'status': 'FAILED'})
                continue
            
            # Basic validation
            all_recipe_ids = set()
            validation_errors = []
            
            for day_key, day_plan in weekly_plan.items():
                for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
                    if meal_name not in day_plan or not day_plan[meal_name]:
                        validation_errors.append(f"{day_key} - Missing/empty {meal_name}")
                        continue
                    
                    for recipe in day_plan[meal_name]:
                        recipe_id = recipe['id']
                        if recipe_id in all_recipe_ids:
                            validation_errors.append(f"Recipe repetition: '{recipe['name']}'")
                        all_recipe_ids.add(recipe_id)
            
            if validation_errors:
                self.stdout.write(self.style.ERROR(f"[FAILED] {len(validation_errors)} error(s)"))
                results.append({'scenario': scenario['name'], 'status': 'FAILED'})
            else:
                self.stdout.write(self.style.SUCCESS(f"[PASSED] {len(weekly_plan)} days, {len(all_recipe_ids)} unique recipes"))
                results.append({'scenario': scenario['name'], 'status': 'PASSED'})
        
        # Summary
        passed = sum(1 for r in results if r['status'] == 'PASSED')
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(f"SUMMARY: {passed}/{len(results)} scenarios passed")
        self.stdout.write("=" * 70 + "\n")
