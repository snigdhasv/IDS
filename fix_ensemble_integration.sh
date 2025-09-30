#!/bin/bash
# Quick fix script to update ML pipeline to use ensemble

echo "🔧 Fixing ML Pipeline to use Adaptive Ensemble..."

# First, fix the initialization
sed -i '57,60c\
        # Adaptive Ensemble Model configuration\
        self.rf2017_path = "/home/ifscr/SE_02_2025/IDS/ML Models/random_forest_model_2017.joblib"\
        self.lgb2018_path = "/home/ifscr/SE_02_2025/IDS/ML Models/lgb_model_2018.joblib"\
        self.ensemble_predictor = AdaptiveEnsemblePredictor(self.rf2017_path, self.lgb2018_path)\
        self.scaler = StandardScaler()' ml_enhanced_ids_pipeline.py

# Replace the load function
cat > temp_load_function.py << 'EOF'
    def load_ml_model(self) -> bool:
        """Load the adaptive ensemble models (RF2017 + LGB2018)"""
        try:
            print(f"{Colors.YELLOW}🧠 Loading Adaptive Ensemble Models...{Colors.END}")
            print(f"  RF(2017): {self.rf2017_path}")
            print(f"  LGB(2018): {self.lgb2018_path}")
            
            if not self.ensemble_predictor.load_models():
                print(f"{Colors.RED}❌ Failed to load ensemble models{Colors.END}")
                return False
                
            print(f"{Colors.GREEN}✓ Adaptive Ensemble loaded successfully{Colors.END}")
            
            # Display model information
            info = self.ensemble_predictor.get_model_info()
            print(f"  RF(2017): {info['rf2017']['type']} with {info['rf2017']['n_features']} features")
            print(f"  LGB(2018): {info['lgb2018']['type']} with {info['lgb2018']['n_features']} features")
            print(f"  Unified classes: {info['ensemble']['total_classes']} classes")
            print(f"  Attack types: {info['ensemble']['unified_classes']}")
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error loading ensemble models: {e}{Colors.END}")
            return False
EOF

# Replace lines 117-134 (the old load function) with the new one
sed -i '117,134d' ml_enhanced_ids_pipeline.py
sed -i '116r temp_load_function.py' ml_enhanced_ids_pipeline.py

# Clean up
rm temp_load_function.py

echo "✅ ML Pipeline updated to use Adaptive Ensemble"
echo "🧪 Testing the fix..."
python3 -c "
from ml_enhanced_ids_pipeline import MLEnhancedIDSPipeline
pipeline = MLEnhancedIDSPipeline()
success = pipeline.load_ml_model()
if success:
    print('🎉 Ensemble integration successful!')
else:
    print('❌ Still having issues...')
"