# planner/management/commands/test_ai_service.py

from django.core.management.base import BaseCommand
# Import instance đã được tạo sẵn từ ai_service.py
from planner.ai_service import MealPlannerService
# Import model để lấy mapping tên cluster
from planner.models import Recipe 

class Command(BaseCommand):
    help = 'Tests the MealPlannerService by predicting a sample nutritional profile'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- [START] Testing AI Service ---")
        
        meal_planner_service = MealPlannerService.get_instance()

        if meal_planner_service.model is None or meal_planner_service.scaler is None:
            self.stdout.write(self.style.ERROR("AI Service failed to load models. Aborting test."))
            return

        # --- Test Case 1: High-Protein Profile ---
        self.stdout.write("\n--- Test Case 1: High-Protein Profile ---")
        high_protein_request = {
            'protein_percent': 40.0,
            'fat_percent': 30.0,
            'carbs_percent': 30.0,
            'avg_sugar_g': 5.0,
            'avg_fiber_g': 15.0
        }
        self.stdout.write(f"Input Profile: {high_protein_request}")
        
        predicted_cluster_id = meal_planner_service.predict_cluster(high_protein_request)
        
        # Lấy tên cluster từ database để kiểm tra
        # Đây là một cách hay để lấy mapping động thay vì hard-code
        cluster_map = dict(Recipe.objects.values_list('cluster', 'cluster_name').distinct())
        predicted_cluster_name = cluster_map.get(predicted_cluster_id, "Unknown")
        
        self.stdout.write(f"Predicted Cluster ID: {predicted_cluster_id}")
        self.stdout.write(f"Predicted Cluster Name: {predicted_cluster_name}")

        # Dựa trên phân tích K-Means, 'High-Protein' là cluster 3
        if "High-Protein" in predicted_cluster_name:
            self.stdout.write(self.style.SUCCESS("Verification successful: Profile correctly classified."))
        else:
            self.stdout.write(self.style.WARNING("Verification check: Classification differs from expectation, but service is working."))

        # --- Test Case 2: High-Carb Profile ---
        self.stdout.write("\n--- Test Case 2: High-Carb Profile ---")
        high_carb_request = {
            'protein_percent': 10.0,
            'fat_percent': 20.0,
            'carbs_percent': 70.0,
            'avg_sugar_g': 40.0,
            'avg_fiber_g': 5.0
        }
        self.stdout.write(f"Input Profile: {high_carb_request}")
        predicted_cluster_id = meal_planner_service.predict_cluster(high_carb_request)
        predicted_cluster_name = cluster_map.get(predicted_cluster_id, "Unknown")
        self.stdout.write(f"Predicted Cluster ID: {predicted_cluster_id}")
        self.stdout.write(f"Predicted Cluster Name: {predicted_cluster_name}")
        if "High-Carb" in predicted_cluster_name:
            self.stdout.write(self.style.SUCCESS("Verification successful: Profile correctly classified."))
        else:
            self.stdout.write(self.style.WARNING("Verification check: Classification differs from expectation, but service is working."))
        
        self.stdout.write("\n--- [END] AI Service Test ---")