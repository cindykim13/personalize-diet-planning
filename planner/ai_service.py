# planner/ai_service.py (PHIÊN BẢN CẢI TIẾN VỚI KIỂM TRA ĐƯỜNG DẪN)

import os
import joblib
import numpy as np
import pandas as pd
from tensorflow import keras
from django.conf import settings
import threading

class MealPlannerService:
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        if hasattr(self, '_models_loaded'): return
        
        self.scaler = None
        self.model = None
        self.training_features = ['protein_percent', 'fat_percent', 'carbs_percent', 'avg_sugar_g', 'avg_fiber_g']
        self._models_loaded = False
        
        # Gọi hàm tải mô hình ngay khi khởi tạo
        self._load_artifacts()

    def _load_artifacts(self):
        print("[INFO] Attempting to load AI artifacts...")
        base_dir = settings.BASE_DIR
        scaler_path = os.path.join(base_dir, 'saved_models', 'robust_scaler.joblib')
        model_path = os.path.join(base_dir, 'saved_models', 'recipe_cluster_classifier.keras')

        # --- KIỂM TRA SỰ TỒN TẠI CỦA FILE TRƯỚC ---
        if not os.path.exists(scaler_path):
            print(f"[CRITICAL ERROR] Scaler file does not exist at the expected path: {scaler_path}")
            return # Dừng lại ngay lập tức

        if not os.path.exists(model_path):
            print(f"[CRITICAL ERROR] Keras model file does not exist at the expected path: {model_path}")
            return # Dừng lại ngay lập tức

        # Tải Scaler
        try:
            self.scaler = joblib.load(scaler_path)
            print(f"[SUCCESS] Scaler loaded from '{scaler_path}'")
        except Exception as e:
            print(f"[ERROR] Failed to load scaler file: {e}")
            return # Dừng lại nếu không tải được

        # Tải Model
        try:
            self.model = keras.models.load_model(model_path)
            print(f"[SUCCESS] Keras model loaded from '{model_path}'")
            self.model.predict(np.zeros((1, len(self.training_features))), verbose=0)
            print("[INFO] Model warmed up.")
        except Exception as e:
            print(f"[ERROR] Failed to load Keras model file: {e}")
            return # Dừng lại nếu không tải được
        
        self._models_loaded = True

    @staticmethod
    def get_instance():
        if MealPlannerService._instance is None:
            with MealPlannerService._lock:
                if MealPlannerService._instance is None:
                    print("[INFO] Creating new MealPlannerService instance...")
                    MealPlannerService._instance = MealPlannerService()
        return MealPlannerService._instance

    def predict_cluster(self, nutritional_info: dict) -> int:
        # Trong phiên bản này, mô hình đã được tải ở __init__
        # nên chúng ta chỉ cần kiểm tra
        if not self._models_loaded:
            print("[ERROR] Cannot predict because models are not loaded.")
            return -1

        try:
            input_df = pd.DataFrame([nutritional_info], columns=self.training_features)
            scaled_vector = self.scaler.transform(input_df)
            prediction_probabilities = self.model.predict(scaled_vector, verbose=0)
            predicted_cluster = np.argmax(prediction_probabilities, axis=1)[0]
            return int(predicted_cluster)
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during prediction: {e}")
            return -1

# Chúng ta sẽ không khởi tạo instance ở đây để tránh lỗi import tuần hoàn
# Việc khởi tạo sẽ được thực hiện trong file test hoặc view.