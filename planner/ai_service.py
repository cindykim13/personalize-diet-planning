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
        
        # DO NOT load artifacts in __init__ - use lazy loading
        # This prevents TensorFlow initialization during Django app startup

    def _load_artifacts(self):
        """
        Load AI models lazily on first use.
        This prevents hangs during Django startup on Apple Silicon.
        Uses thread-safe double-checked locking pattern.
        """
        # Double-checked locking: check again after acquiring lock
        if self._models_loaded:
            return
        
        # Thread-safe: acquire lock before loading
        with MealPlannerService._lock:
            # Check again inside lock (double-checked locking pattern)
            if self._models_loaded:
                return
            
            print("[INFO] Attempting to load AI artifacts...")
            base_dir = settings.BASE_DIR
            scaler_path = os.path.join(base_dir, 'saved_models', 'robust_scaler.joblib')
            model_path = os.path.join(base_dir, 'saved_models', 'recipe_cluster_classifier.keras')

            # Check file existence with absolute path resolution
            if not os.path.exists(scaler_path):
                abs_path = os.path.abspath(scaler_path)
                print(f"[CRITICAL ERROR] Scaler file does not exist at: {abs_path}")
                print(f"[INFO] BASE_DIR is: {base_dir}")
                # Mark as attempted to prevent infinite retries
                self._models_loaded = True  # Prevent retry loops
                return

            if not os.path.exists(model_path):
                abs_path = os.path.abspath(model_path)
                print(f"[CRITICAL ERROR] Keras model file does not exist at: {abs_path}")
                print(f"[INFO] BASE_DIR is: {base_dir}")
                # Mark as attempted to prevent infinite retries
                self._models_loaded = True  # Prevent retry loops
                return

            # Load Scaler
            try:
                self.scaler = joblib.load(scaler_path)
                print(f"[SUCCESS] Scaler loaded from '{scaler_path}'")
            except Exception as e:
                print(f"[ERROR] Failed to load scaler file: {e}")
                print(f"[INFO] Traceback: {type(e).__name__}: {str(e)}")
                # Mark as attempted to prevent infinite retries
                self._models_loaded = True  # Prevent retry loops
                return

            # Load Model
            try:
                self.model = keras.models.load_model(model_path)
                print(f"[SUCCESS] Keras model loaded from '{model_path}'")
                # Warm up model to verify it works
                warmup_input = np.zeros((1, len(self.training_features)))
                self.model.predict(warmup_input, verbose=0)
                print("[INFO] Model warmed up successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to load Keras model file: {e}")
                print(f"[INFO] Traceback: {type(e).__name__}: {str(e)}")
                # Mark as attempted to prevent infinite retries
                self._models_loaded = True  # Prevent retry loops
                return
            
            # Success: mark as loaded
            self._models_loaded = True
            print("[SUCCESS] All AI artifacts loaded successfully.")

    @staticmethod
    def get_instance():
        if MealPlannerService._instance is None:
            with MealPlannerService._lock:
                if MealPlannerService._instance is None:
                    print("[INFO] Creating new MealPlannerService instance...")
                    MealPlannerService._instance = MealPlannerService()
        return MealPlannerService._instance

    def predict_cluster(self, nutritional_info: dict) -> int:
        """
        Predict the nutritional cluster for a given nutritional profile.
        This triggers lazy loading of models on first use.
        """
        # Lazy load: load models on first use if not already loaded
        if not self._models_loaded:
            self._load_artifacts()
        
        if self.scaler is None or self.model is None:
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