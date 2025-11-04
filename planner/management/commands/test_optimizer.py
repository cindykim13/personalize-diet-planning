# planner/management/commands/test_optimizer.py
from django.core.management.base import BaseCommand
from planner.models import Recipe
from planner.optimization_service import create_meal_plan
import pandas as pd

class Command(BaseCommand):
    help = 'Tests the optimization_service module'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- [START] Testing Optimization Service ---")

        # 1. Tạo một bể công thức giả lập từ database
        # Lấy 500 công thức cân bằng làm bể ứng viên
        recipe_pool = list(Recipe.objects.filter(cluster_name="Balanced / High-Fiber").values())[:500]
        if len(recipe_pool) < 10:
            self.stdout.write(self.style.ERROR("Not enough recipes in the database to run the test."))
            return

        self.stdout.write(f"Created a recipe pool with {len(recipe_pool)} candidate recipes.")

        # 2. Đặt một mục tiêu dinh dưỡng
        target_nutrients = {
            'calories': 1500,
            'protein_g': 110,
            'fat_g': 50,
            'carbs_g': 150
        }
        self.stdout.write(f"Target daily nutrients: {target_nutrients}")

        # 3. Gọi hàm tối ưu hóa
        selected_recipes = create_meal_plan(recipe_pool, target_nutrients)

        # 4. Kiểm tra kết quả
        self.stdout.write("\n--- [RESULT] ---")
        if selected_recipes:
            self.stdout.write(self.style.SUCCESS(f"Successfully found an optimal plan with {len(selected_recipes)} meals:"))
            
            plan_summary = {
                'total_calories': 0, 'total_protein_g': 0,
                'total_fat_g': 0, 'total_carbs_g': 0
            }
            for recipe in selected_recipes:
                self.stdout.write(f"  - {recipe['name']} (Calories: {recipe['avg_calories']:.2f})")
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

        else:
            self.stdout.write(self.style.ERROR("Could not find an optimal solution."))

        self.stdout.write("\n--- [END] Optimization Service Test ---")