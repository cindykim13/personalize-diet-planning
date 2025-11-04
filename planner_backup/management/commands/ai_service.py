# planner/ai_service.py

import os
import joblib
import numpy as np
import tensorflow as tf
from tensorflow import keras
from django.conf import settings

class MealPlannerService:
    _instance = None
    
    # --- Phần Khởi tạo và Tải Mô hình ---
    
    def __init__(self):
        # Ngăn việc khởi tạo lại đối tượng một cách không cần thiết
        if MealPlannerService._instance is not None:
            raise Exception("This is a singleton class. Use get_instance() to get the object.")
        
        self.scaler = None
        self.model = None
        self.training_features = ['protein_percent', 'fat_percent', 'carbs_percent', 'avg_sugar_g', 'avg_fiber_g']
        
        # Tải các tài sản AI ngay khi đối tượng được tạo
        self._load_artifacts()

    def _load_artifacts(self):
        """Tải đối tượng scaler và mô hình Keras đã được huấn luyện."""
        base_dir = settings.BASE_DIR
        scaler_path = os.path.join(base_dir, 'saved_models', 'robust_scaler.joblib')
        model_path = os.path.join(base_dir, 'saved_models', 'recipe_cluster_classifier.keras')
        
        # Tải Scaler
        try:
            self.scaler = joblib.load(scaler_path)
            print(f"[INFO] Scaler loaded successfully from '{scaler_path}'")
        except FileNotFoundError:
            print(f"[ERROR] Scaler file not found at {scaler_path}. Predictions will fail.")
        
        # Tải Model
        try:
            self.model = keras.models.load_model(model_path)
            print(f"[INFO] Keras model loaded successfully from '{model_path}'")
            # Chạy một dự đoán "khởi động" để tối ưu hóa lần gọi đầu tiên
            self.model.predict(np.zeros((1, len(self.training_features))), verbose=0)
            print("[INFO] Model warmed up.")
        except (IOError, FileNotFoundError):
            print(f"[ERROR] Keras model file not found at {model_path}. Predictions will fail.")

    @staticmethod
    def get_instance():
        """
        Phương thức static để lấy đối tượng duy nhất của class (Singleton Pattern).
        """
        if MealPlannerService._instance is None:
            print("[INFO] Creating new MealPlannerService instance...")
            MealPlannerService._instance = MealPlannerService()
        return MealPlannerService._instance

    # --- Phần Logic Dự đoán ---

    def predict_cluster(self, nutritional_info: dict) -> int:
        """
        Dự đoán cluster phù hợp nhất từ một dictionary chứa thông tin dinh dưỡng.
        
        :param nutritional_info: Dictionary, ví dụ {'protein_percent': 30, ...}
        :return: ID của cluster được dự đoán (int), hoặc -1 nếu có lỗi.
        """
        if self.scaler is None or self.model is None:
            print("[ERROR] Cannot predict because scaler or model is not loaded.")
            return -1

        try:
            # 1. Tạo vector đặc trưng theo đúng thứ tự mà mô hình đã học
            feature_vector = np.array([nutritional_info[feature] for feature in self.training_features])
            
            # 2. Chuẩn hóa vector. Scaler transform yêu cầu đầu vào 2D.
            scaled_vector = self.scaler.transform(feature_vector.reshape(1, -1))
            
            # 3. Thực hiện dự đoán
            prediction_probabilities = self.model.predict(scaled_vector, verbose=0)
            
            # 4. Lấy ra chỉ số của cluster có xác suất cao nhất
            predicted_cluster = np.argmax(prediction_probabilities, axis=1)[0]
            
            return int(predicted_cluster)

        except KeyError as e:
            print(f"[ERROR] Missing nutritional feature in input dictionary: {e}")
            return -1
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during prediction: {e}")
            return -1

# --- Khởi tạo Instance Toàn cục ---
# Dòng này sẽ chỉ chạy một lần khi Django khởi động server.
# Nó tạo ra một đối tượng 'meal_planner_service' duy nhất mà chúng ta có thể import và sử dụng ở bất kỳ đâu.
#meal_planner_service = MealPlannerService.get_instance()