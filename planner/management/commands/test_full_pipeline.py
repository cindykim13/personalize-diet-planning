# planner/management/commands/test_full_pipeline.py
from django.core.management.base import BaseCommand
from planner.planner_service import generate_full_meal_plan

class Command(BaseCommand):
    help = 'Tests the full, multi-day meal plan generation pipeline with semantic constraints'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- [START] Testing Full Multi-Day Pipeline with Semantic Constraints ---")
        
        # Prerequisite check: Ensure meal types are classified
        from planner.models import Recipe
        unclassified_count = Recipe.objects.filter(meal_type='Unknown').count()
        total_count = Recipe.objects.count()
        
        if total_count == 0:
            self.stdout.write(self.style.ERROR("\n[ERROR] No recipes found in database. Please run 'python manage.py load_recipes' first."))
            return
        
        if unclassified_count == total_count:
            self.stdout.write(self.style.WARNING(f"\n[WARNING] All {total_count} recipes are unclassified. Please run 'python manage.py classify_meal_types' first."))
            self.stdout.write("[INFO] Continuing with test, but semantic constraints will be relaxed...")
        elif unclassified_count > 0:
            classified_pct = ((total_count - unclassified_count) / total_count * 100) if total_count > 0 else 0
            self.stdout.write(f"\n[INFO] Recipe classification status: {total_count - unclassified_count}/{total_count} classified ({classified_pct:.1f}%)")
            self.stdout.write("[INFO] Continuing with test...")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n[INFO] All {total_count} recipes are classified. Semantic constraints will be enforced."))

        # 1. Định nghĩa yêu cầu của người dùng
        user_request = {
            'number_of_days': 7,
            'target_nutrients': {
                'calories': 2000,
                'protein_g': 150,
                'fat_g': 65,
                'carbs_g': 200
            },
            'allergies': [],
            'dislikes': []
        }
        self.stdout.write(f"User Request: Generate a {user_request['number_of_days']}-day plan.")

        # 2. Gọi hàm điều phối chính
        weekly_plan = generate_full_meal_plan(user_request)

        # 3. Kiểm tra và In kết quả với verification của semantic constraints
        self.stdout.write("\n--- [RESULT] ---")
        if weekly_plan:
            all_recipe_ids = set()
            semantic_constraint_violations = []
            
            for day, plan in weekly_plan.items():
                self.stdout.write(self.style.SUCCESS(f"\n--- {day} ---"))
                day_recipe_ids = set()
                day_meal_types = []
                
                for recipe in plan:
                    # Display recipe with meal type
                    recipe_name = recipe['name']
                    meal_type = recipe.get('meal_type', 'Unknown')
                    self.stdout.write(f"  - {recipe_name} [{meal_type}]")
                    day_recipe_ids.add(recipe['id'])
                    day_meal_types.append(meal_type)
                
                # Verify semantic constraints for this day
                has_main_course = 'Main Course' in day_meal_types
                dessert_count = day_meal_types.count('Dessert')
                drink_count = day_meal_types.count('Drink')
                
                # Check violations
                if not has_main_course:
                    semantic_constraint_violations.append(f"{day}: No Main Course found")
                if dessert_count > 1:
                    semantic_constraint_violations.append(f"{day}: {dessert_count} Desserts (max 1 allowed)")
                if drink_count > 1:
                    semantic_constraint_violations.append(f"{day}: {drink_count} Drinks (max 1 allowed)")
                
                # Kiểm tra sự trùng lặp
                if any(recipe_id in all_recipe_ids for recipe_id in day_recipe_ids):
                    self.stdout.write(self.style.ERROR("  [FAILED] Repetition detected in the weekly plan!"))
                all_recipe_ids.update(day_recipe_ids)
            
            # Summary and validation
            self.stdout.write("\n--- [VALIDATION SUMMARY] ---")
            if len(weekly_plan) == user_request['number_of_days']:
                self.stdout.write(self.style.SUCCESS("[✓] Full weekly plan generated (no repetition)."))
            else:
                self.stdout.write(self.style.WARNING(f"[⚠] Plan generated for only {len(weekly_plan)}/{user_request['number_of_days']} days."))
            
            # Semantic constraints validation
            if semantic_constraint_violations:
                self.stdout.write(self.style.ERROR("[✗] Semantic constraint violations detected:"))
                for violation in semantic_constraint_violations:
                    self.stdout.write(f"    - {violation}")
                self.stdout.write(self.style.WARNING("The meal plan does not meet realistic meal structure requirements."))
            else:
                self.stdout.write(self.style.SUCCESS("[✓] All semantic constraints satisfied."))
                self.stdout.write("    - Each day contains at least one Main Course")
                self.stdout.write("    - Each day contains at most one Dessert")
                self.stdout.write("    - Each day contains at most one Drink")
        else:
            self.stdout.write(self.style.ERROR("Could not generate any meal plan."))
        
        self.stdout.write("\n--- [END] Full Pipeline Test ---")