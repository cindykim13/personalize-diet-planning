# planner/management/commands/test_optimizer.py
from django.core.management.base import BaseCommand
from planner.models import Recipe
from planner.optimization_service import create_daily_plan_global

class Command(BaseCommand):
    help = 'Tests the optimization_service module using the new daily global optimization function'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 80)
        self.stdout.write("OPTIMIZATION SERVICE UNIT TEST")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Test the daily global optimization function")
        self.stdout.write("Note: This tests create_daily_plan_global, the current optimization")
        self.stdout.write("      function used by the main pipeline.")
        self.stdout.write("=" * 80)
        self.stdout.write("\n--- [START] Testing Optimization Service ---")

        # Prerequisite check: Ensure meal types are classified
        unclassified_count = Recipe.objects.filter(meal_type='Unknown').count()
        total_count = Recipe.objects.count()
        
        if total_count == 0:
            self.stdout.write(self.style.ERROR("Not enough recipes in the database to run the test."))
            return
        
        if unclassified_count == total_count:
            self.stdout.write(self.style.ERROR(f"All {total_count} recipes are unclassified. Please run 'python manage.py classify_meal_types' first."))
            return

        # 1. Create recipe pools for each meal type
        # Get recipes from Balanced cluster for testing
        base_queryset = Recipe.objects.filter(
            cluster_name="Balanced / High-Fiber"
        ).exclude(meal_type='Unknown')
        
        if base_queryset.count() < 20:
            self.stdout.write(self.style.ERROR("Not enough classified recipes in the database to run the test."))
            return

        # Build recipe pools for Breakfast, Lunch, Dinner
        recipe_pools = {}
        
        # Breakfast pool
        breakfast_recipes = list(base_queryset.filter(meal_type='Breakfast').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:150])
        fruit_recipes = list(base_queryset.filter(meal_type='Fruit').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:100])
        drink_recipes = list(base_queryset.filter(meal_type='Drink').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:100])
        recipe_pools['Breakfast'] = breakfast_recipes + fruit_recipes + drink_recipes
        
        # Lunch pool
        main_courses = list(base_queryset.filter(meal_type='Main Course').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:200])
        side_dishes = list(base_queryset.filter(meal_type='Side Dish').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:200])
        salads = list(base_queryset.filter(meal_type='Salad').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:100])
        soups = list(base_queryset.filter(meal_type='Soup').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:100])
        recipe_pools['Lunch'] = main_courses + side_dishes + salads + soups
        
        # Dinner pool (same as Lunch, plus Dessert)
        desserts = list(base_queryset.filter(meal_type='Dessert').values(
            'id', 'name', 'meal_type', 'avg_calories', 'avg_protein_g', 'avg_fat_g', 'avg_carbs_g'
        )[:50])
        recipe_pools['Dinner'] = main_courses + side_dishes + salads + soups + desserts

        self.stdout.write(f"Created recipe pools:")
        self.stdout.write(f"  Breakfast: {len(recipe_pools['Breakfast'])} recipes")
        self.stdout.write(f"  Lunch: {len(recipe_pools['Lunch'])} recipes")
        self.stdout.write(f"  Dinner: {len(recipe_pools['Dinner'])} recipes")

        # 2. Set daily nutritional targets
        target_nutrients = {
            'calories': 2000,
            'protein_g': 100,
            'fat_g': 67,
            'carbs_g': 250
        }
        self.stdout.write(f"\nTarget daily nutrients: {target_nutrients}")

        # 3. Call the daily global optimization function
        used_recipe_ids = set()
        result = create_daily_plan_global(
            recipe_pools=recipe_pools,
            daily_target_nutrients=target_nutrients,
            used_recipe_ids=used_recipe_ids,
            day_number=1,
            max_protein_deviation_pct=15.0
        )

        # 4. Check results
        self.stdout.write("\n--- [RESULT] ---")
        if result and result.get('status') in ['Optimal', 'Optimal_Relaxed']:
            self.stdout.write(self.style.SUCCESS(f"Successfully found an optimal plan (status: {result.get('status')})"))
            
            plan_summary = {
                'total_calories': 0, 'total_protein_g': 0,
                'total_fat_g': 0, 'total_carbs_g': 0
            }
            
            for meal_name in ['Breakfast', 'Lunch', 'Dinner']:
                meal_recipes = result.get(meal_name, [])
                if meal_recipes:
                    self.stdout.write(f"\n  {meal_name} ({len(meal_recipes)} recipes):")
                    for recipe in meal_recipes:
                        self.stdout.write(f"    - {recipe['name']} [{recipe.get('meal_type', 'Unknown')}] (Calories: {recipe['avg_calories']:.2f})")
                        plan_summary['total_calories'] += recipe['avg_calories']
                        plan_summary['total_protein_g'] += recipe['avg_protein_g']
                        plan_summary['total_fat_g'] += recipe['avg_fat_g']
                        plan_summary['total_carbs_g'] += recipe['avg_carbs_g']
            
            self.stdout.write("\n--- Plan Summary vs. Target ---")
            self.stdout.write(f"           Target -> Plan")
            self.stdout.write(f"Calories:  {target_nutrients['calories']} -> {plan_summary['total_calories']:.2f}")
            self.stdout.write(f"Protein:   {target_nutrients['protein_g']} -> {plan_summary['total_protein_g']:.2f}")
            self.stdout.write(f"Fat:       {target_nutrients['fat_g']} -> {plan_summary['total_fat_g']:.2f}")
            self.stdout.write(f"Carbs:     {target_nutrients['carbs_g']} -> {plan_summary['total_carbs_g']:.2f}")
            
            # Calculate deviations
            cal_dev = abs(plan_summary['total_calories'] - target_nutrients['calories']) / target_nutrients['calories'] * 100
            pro_dev = abs(plan_summary['total_protein_g'] - target_nutrients['protein_g']) / target_nutrients['protein_g'] * 100
            self.stdout.write(f"\nDeviations: Calories {cal_dev:.1f}%, Protein {pro_dev:.1f}%")
            
            if cal_dev < 20 and pro_dev < 20:
                self.stdout.write(self.style.SUCCESS("✓ Optimization test PASSED"))
            else:
                self.stdout.write(self.style.WARNING("⚠ Optimization test completed with significant deviations"))

        else:
            status = result.get('status', 'Unknown') if result else 'No result'
            self.stdout.write(self.style.ERROR(f"Could not find an optimal solution. Status: {status}"))

        self.stdout.write("\n--- [END] Optimization Service Test ---")