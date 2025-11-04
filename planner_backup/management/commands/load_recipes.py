# planner/management/commands/load_recipes.py (PHIÊN BẢN HOÀN CHỈNH, ĐÃ SỬA LỖI)
import pandas as pd
import numpy as np # Import numpy
from django.core.management.base import BaseCommand
from planner.models import Recipe
import os

class Command(BaseCommand):
    help = 'Loads recipes from the final processed Parquet file into the database'

    def handle(self, *args, **kwargs):
        parquet_path = 'data_validation/final_recipes_with_clusters.parquet'
        
        if not os.path.exists(parquet_path):
            self.stdout.write(self.style.ERROR(f"File not found at: {parquet_path}"))
            return

        self.stdout.write(f"Reading data from '{parquet_path}'...")
        df = pd.read_parquet(parquet_path)
        
        # --- BƯỚC KIỂM TRA MỚI ---
        # Kiểm tra kiểu dữ liệu của các cột JSON trước khi xử lý
        self.stdout.write("Verifying data types for JSON fields...")
        if not df.empty:
            first_row = df.iloc[0]
            self.stdout.write(f"  - Type of 'steps': {type(first_row['steps'])}")
            self.stdout.write(f"  - Type of 'ingredients_list': {type(first_row['ingredients_list'])}")
        
        self.stdout.write("Deleting old recipe data from the database...")
        count_before = Recipe.objects.count()
        Recipe.objects.all().delete()
        self.stdout.write(f"Successfully deleted {count_before} old records.")
        
        self.stdout.write(f"Preparing to load {len(df)} new recipes...")
        
        # Tạo danh sách các đối tượng Recipe để chèn hàng loạt
        recipes_to_create = []
        for row in df.to_dict('records'):
            # --- THAY ĐỔI CỐT LÕI NẰM Ở ĐÂY ---
            # Đảm bảo rằng các trường JSONField nhận được list Python chuẩn
            steps_list = row['steps'].tolist() if isinstance(row['steps'], np.ndarray) else row['steps']
            ingredients_list_data = row['ingredients_list'].tolist() if isinstance(row['ingredients_list'], np.ndarray) else row['ingredients_list']

            recipe_obj = Recipe(
                name=row['name'],
                # Không còn name_original và description
                steps=steps_list,
                ingredients_list=ingredients_list_data,
                protein_percent=row['protein_percent'],
                fat_percent=row['fat_percent'],
                carbs_percent=row['carbs_percent'],
                avg_sugar_g=row['avg_sugar_g'],
                avg_fiber_g=row['avg_fiber_g'],
                cluster=row['cluster'],
                cluster_name=row['cluster_name'],
                avg_calories=row['avg_calories'],
                avg_protein_g=row['avg_protein_g'],
                avg_fat_g=row['avg_fat_g'],
                avg_carbs_g=row['avg_carbs_g'],
            )
            recipes_to_create.append(recipe_obj)

        self.stdout.write("Loading data in batches using bulk_create... (This may take a few minutes)")
        Recipe.objects.bulk_create(recipes_to_create, batch_size=1000)
        
        # Kiểm tra cuối cùng
        count_after = Recipe.objects.count()
        if count_after == len(df):
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {count_after} recipes into the database."))
        else:
            self.stdout.write(self.style.WARNING(f"Data loading mismatch! Expected {len(df)} but loaded {count_after} records."))