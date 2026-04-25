# planner/ai_service.py (LAZY LOADING VERSION - FIXES STARTUP HANG)

import os
import joblib
import numpy as np
import pandas as pd
# CRITICAL FIX: TensorFlow import moved to lazy loading to prevent startup hang
# from tensorflow import keras  # ❌ REMOVED: Causes hang during Django startup
from django.conf import settings
import threading

class MealPlannerService:
    _instance = None
    _lock = threading.Lock()
    _loading_lock = threading.Lock()  # Separate lock for model loading
    
    def __init__(self):
        # CRITICAL FIX: Do NOT load models in __init__ - use lazy loading instead
        # This prevents blocking during Django startup/import
        self.scaler = None
        self.model = None
        self.training_features = ['protein_percent', 'fat_percent', 'carbs_percent', 'avg_sugar_g', 'avg_fiber_g']
        self._models_loaded = False
        self._loading = False  # Flag to prevent concurrent loading attempts

    def _load_if_needed(self):
        """
        Thread-safe lazy loading of AI artifacts.
        Only loads models when actually needed (first call to predict_cluster).
        Uses double-checked locking pattern for efficiency.
        """
        # First check: Fast path if already loaded (no lock needed)
        if self._models_loaded:
            return True
        
        # Second check: Acquire lock and check again (double-checked locking)
        with self._loading_lock:
            # Check again after acquiring lock (another thread may have loaded)
            if self._models_loaded:
                return True
            
            # Check if another thread is already loading
            if self._loading:
                # Another thread is loading, release lock and wait
                # Return False - caller should retry
                return False
            
            # Mark that we're loading BEFORE releasing lock
            self._loading = True
        
        # Load artifacts outside lock to avoid blocking other threads
        result = False
        try:
            result = self._load_artifacts()
            return result
        finally:
            # Release loading flag (always, even on exception)
            with self._loading_lock:
                self._loading = False
                # Also set _models_loaded if successful
                if result:
                    self._models_loaded = True

    def _load_artifacts(self):
        """
        Loads TensorFlow/Keras model and scikit-learn scaler from disk.
        This method is called on-demand, not during initialization.
        """
        print("[INFO] Attempting to load AI artifacts (lazy loading)...")
        
        # CRITICAL FIX: Lazy import TensorFlow only when actually needed
        try:
            from tensorflow import keras
        except ImportError as e:
            print(f"[ERROR] Failed to import TensorFlow: {e}")
            return False
        
        base_dir = settings.BASE_DIR
        scaler_path = os.path.join(base_dir, 'saved_models', 'robust_scaler.joblib')
        model_path = os.path.join(base_dir, 'saved_models', 'recipe_cluster_classifier.keras')

        # --- KIỂM TRA SỰ TỒN TẠI CỦA FILE TRƯỚC ---
        if not os.path.exists(scaler_path):
            print(f"[CRITICAL ERROR] Scaler file does not exist at the expected path: {scaler_path}")
            return False

        if not os.path.exists(model_path):
            print(f"[CRITICAL ERROR] Keras model file does not exist at the expected path: {model_path}")
            return False

        # Tải Scaler
        try:
            self.scaler = joblib.load(scaler_path)
            print(f"[SUCCESS] Scaler loaded from '{scaler_path}'")
        except Exception as e:
            print(f"[ERROR] Failed to load scaler file: {e}")
            return False

        # Tải Model
        try:
            self.model = keras.models.load_model(model_path)
            print(f"[SUCCESS] Keras model loaded from '{model_path}'")
            # Warm up model with dummy prediction
            self.model.predict(np.zeros((1, len(self.training_features))), verbose=0)
            print("[INFO] Model warmed up.")
        except Exception as e:
            print(f"[ERROR] Failed to load Keras model file: {e}")
            return False
        
        # Note: _models_loaded flag is set by _load_if_needed() in its finally block
        return True

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
        Predicts the nutritional cluster for given nutritional information.
        
        CRITICAL FIX: Models are loaded lazily on first call, not during initialization.
        This prevents Django startup hang.
        """
        # CRITICAL FIX: Load models on-demand (lazy loading)
        if not self._load_if_needed():
            print("[ERROR] Cannot predict because models failed to load.")
            return -1

        if not self._models_loaded or self.scaler is None or self.model is None:
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

# CRITICAL FIX: No module-level initialization to prevent startup hang
# The singleton instance is created lazily via get_instance() when needed
# Models are loaded even more lazily via _load_if_needed() on first prediction call