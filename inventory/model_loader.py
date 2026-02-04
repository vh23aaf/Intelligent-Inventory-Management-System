"""
Model loader for using pre-trained best model from notebook.
Loads the best model trained and saved by model_training.ipynb
"""

import os
import json
import joblib
import logging

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models_saved')


class PreTrainedModelLoader:
    """Load and use the best pre-trained model."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PreTrainedModelLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.metadata = None
        self._load_model()
    
    def _load_model(self):
        """Load the pre-trained model and supporting files."""
        try:
            model_path = os.path.join(MODELS_DIR, 'best_demand_model.pkl')
            scaler_path = os.path.join(MODELS_DIR, 'feature_scaler.pkl')
            features_path = os.path.join(MODELS_DIR, 'feature_columns.pkl')
            metadata_path = os.path.join(MODELS_DIR, 'model_metadata.json')
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_columns = joblib.load(features_path)
                
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                
                logger.info(f"✓ Loaded best model: {self.metadata['model_name']}")
                logger.info(f"  MAE: {self.metadata['mae']:.4f}, R²: {self.metadata['r2']:.4f}")
            else:
                logger.warning(f"Model file not found at {model_path}")
        except Exception as e:
            logger.error(f"Error loading pre-trained model: {str(e)}")
    
    def is_available(self):
        """Check if model is loaded and ready."""
        return self.model is not None
    
    def predict(self, features_array):
        """
        Make prediction using pre-trained model.
        
        Args:
            features_array: numpy array with features in correct order
            
        Returns:
            float: Predicted demand value
        """
        if not self.is_available():
            return None
        
        try:
            # Scale features
            scaled_features = self.scaler.transform(features_array)
            # Predict
            prediction = self.model.predict(scaled_features)
            return float(prediction[0]) if len(prediction) > 0 else None
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            return None
    
    def get_model_info(self):
        """Get model metadata."""
        if self.metadata:
            return {
                'name': self.metadata['model_name'],
                'mae': self.metadata['mae'],
                'rmse': self.metadata['rmse'],
                'r2': self.metadata['r2'],
                'trained_on': f"{self.metadata['training_samples']} samples"
            }
        return None


# Singleton instance
best_model_loader = PreTrainedModelLoader()
