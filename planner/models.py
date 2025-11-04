# planner/models.py
from django.db import models

class Recipe(models.Model):
    # Thông tin định danh và hiển thị
    name = models.CharField(max_length=500)
    steps = models.JSONField(default=list)
    ingredients_list = models.JSONField(default=list)
    meal_type = models.CharField(max_length=50, default='Unknown')

    # Các đặc trưng dinh dưỡng (từ EDA)
    protein_percent = models.FloatField(default=0.0)
    fat_percent = models.FloatField(default=0.0)
    carbs_percent = models.FloatField(default=0.0)
    avg_sugar_g = models.FloatField(default=0.0)
    avg_fiber_g = models.FloatField(default=0.0)
    
    # Nhãn cụm
    cluster = models.IntegerField()
    cluster_name = models.CharField(max_length=100)

    # Giá trị calo trung bình (để tham khảo và tối ưu hóa)
    avg_calories = models.FloatField(default=0.0)
    
    # Các giá trị gram trung bình (để tham khảo)
    avg_protein_g = models.FloatField(default=0.0)
    avg_fat_g = models.FloatField(default=0.0)
    avg_carbs_g = models.FloatField(default=0.0)


    def __str__(self):
        return self.name

    class Meta:
        # Tên bảng trong PostgreSQL sẽ là 'planner_recipe'
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"