#!/usr/bin/env python3
"""
Accuracy Metrics Calculator for ML Predictions

Reads CSV predictions from realtime_ensemble_consumer_with_csv.py and calculates:
- Accuracy, Precision, Recall, F1 Score
- Confusion Matrix
- Per-attack-type accuracy
- Model voting agreement statistics
- Confidence calibration

Usage:
    python3 calculate_accuracy_metrics.py \
        --predictions predictions.csv \
        --output metrics_report.json

    # With detailed analysis
    python3 calculate_accuracy_metrics.py \
        --predictions predictions.csv \
        --output metrics_report.json \
        --detailed \
        --plot-confusion-matrix
"""

import argparse
import csv
import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter
import statistics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available (optional). Continuing without statistical tests.")

try:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, roc_auc_score, roc_curve
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Installing basic metrics only.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class AccuracyMetricsCalculator:
    """Calculate comprehensive accuracy metrics from prediction CSV"""
    
    def __init__(self, predictions_csv: str):
        self.csv_file = Path(predictions_csv)
        if not self.csv_file.exists():
            raise FileNotFoundError(f"Predictions file not found: {predictions_csv}")
        
        self.predictions = []
        self.ground_truths = []
        self.confidences = []
        self.agreement_ratios = []
        self.model_predictions = defaultdict(list)
        
        logger.info(f"📁 Reading predictions from: {predictions_csv}")
        self._load_predictions()
    
    def _load_predictions(self):
        """Load predictions from CSV"""
        count = 0
        errors = 0
        
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Skip rows with missing ground truth
                    if not row.get('ground_truth') or row['ground_truth'] == '':
                        continue
                    
                    gt = row['ground_truth'].strip().upper()
                    pred = row['ensemble_prediction'].strip().upper()
                    conf = float(row['ensemble_confidence'])
                    agree = float(row['agreement_ratio'])
                    
                    self.ground_truths.append(gt)
                    self.predictions.append(pred)
                    self.confidences.append(conf)
                    self.agreement_ratios.append(agree)
                    
                    # Store per-model predictions
                    for col, val in row.items():
                        if col.startswith('model_') and col.endswith('_pred'):
                            model_name = col.replace('model_', '').replace('_pred', '')
                            if val:  # Only if not empty
                                self.model_predictions[model_name].append(val.upper())
                    
                    count += 1
                
                except (ValueError, KeyError) as e:
                    errors += 1
                    continue
        
        if not self.predictions:
            raise ValueError("No valid predictions with ground truth found in CSV")
        
        logger.info(f"✓ Loaded {count} predictions")
        if errors > 0:
            logger.warning(f"⚠️  {errors} rows had errors and were skipped")
    
    def calculate_basic_metrics(self) -> Dict:
        """Calculate basic accuracy metrics"""
        if not SKLEARN_AVAILABLE:
            return self._calculate_basic_metrics_manual()
        
        metrics = {}
        
        # Overall accuracy
        metrics['accuracy'] = accuracy_score(self.ground_truths, self.predictions)
        
        # Get unique labels
        labels = sorted(set(self.ground_truths + self.predictions))
        
        # Weighted metrics (account for class imbalance)
        metrics['precision'] = precision_score(
            self.ground_truths, self.predictions, 
            average='weighted', zero_division=0
        )
        metrics['recall'] = recall_score(
            self.ground_truths, self.predictions,
            average='weighted', zero_division=0
        )
        metrics['f1'] = f1_score(
            self.ground_truths, self.predictions,
            average='weighted', zero_division=0
        )
        
        # Per-class metrics
        metrics['per_class'] = {}
        for label in labels:
            y_true_binary = [1 if x == label else 0 for x in self.ground_truths]
            y_pred_binary = [1 if x == label else 0 for x in self.predictions]
            
            metrics['per_class'][label] = {
                'precision': precision_score(y_true_binary, y_pred_binary, zero_division=0),
                'recall': recall_score(y_true_binary, y_pred_binary, zero_division=0),
                'f1': f1_score(y_true_binary, y_pred_binary, zero_division=0),
                'support': sum(y_true_binary),
            }
        
        # Confusion matrix
        cm = confusion_matrix(self.ground_truths, self.predictions, labels=labels)
        metrics['confusion_matrix'] = {
            'labels': labels,
            'matrix': cm.tolist()
        }
        
        return metrics
    
    def _calculate_basic_metrics_manual(self) -> Dict:
        """Calculate basic metrics without sklearn"""
        metrics = {}
        
        # Accuracy
        correct = sum(1 for gt, pred in zip(self.ground_truths, self.predictions) 
                     if gt == pred)
        metrics['accuracy'] = correct / len(self.predictions)
        
        # Per-class metrics
        labels = sorted(set(self.ground_truths + self.predictions))
        metrics['per_class'] = {}
        metrics['confusion_matrix'] = {'labels': labels, 'matrix': []}
        
        for label in labels:
            tp = sum(1 for gt, pred in zip(self.ground_truths, self.predictions)
                    if gt == label and pred == label)
            fp = sum(1 for gt, pred in zip(self.ground_truths, self.predictions)
                    if gt != label and pred == label)
            fn = sum(1 for gt, pred in zip(self.ground_truths, self.predictions)
                    if gt == label and pred != label)
            
            support = tp + fn
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics['per_class'][label] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': support,
            }
        
        logger.warning("⚠️  Calculating without scikit-learn (results may differ slightly)")
        return metrics
    
    def calculate_confidence_metrics(self) -> Dict:
        """Calculate confidence and agreement metrics"""
        metrics = {}
        
        # Confidence statistics
        metrics['confidence'] = {
            'mean': statistics.mean(self.confidences),
            'median': statistics.median(self.confidences),
            'stdev': statistics.stdev(self.confidences) if len(self.confidences) > 1 else 0,
            'min': min(self.confidences),
            'max': max(self.confidences),
        }
        
        # Agreement statistics
        metrics['agreement'] = {
            'mean': statistics.mean(self.agreement_ratios),
            'median': statistics.median(self.agreement_ratios),
            'stdev': statistics.stdev(self.agreement_ratios) if len(self.agreement_ratios) > 1 else 0,
            'min': min(self.agreement_ratios),
            'max': max(self.agreement_ratios),
        }
        
        # Agreement distribution
        agree_dist = {
            'high (>=0.80)': sum(1 for a in self.agreement_ratios if a >= 0.80),
            'medium (0.60-0.80)': sum(1 for a in self.agreement_ratios if 0.60 <= a < 0.80),
            'low (<0.60)': sum(1 for a in self.agreement_ratios if a < 0.60),
        }
        metrics['agreement_distribution'] = agree_dist
        
        # Accuracy by confidence level
        metrics['accuracy_by_confidence'] = {}
        confidence_buckets = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0)]
        for low, high in confidence_buckets:
            indices = [i for i, c in enumerate(self.confidences) 
                      if low <= c < high]
            if indices:
                bucket_acc = sum(1 for i in indices 
                               if self.ground_truths[i] == self.predictions[i]) / len(indices)
                metrics['accuracy_by_confidence'][f'{low:.1f}-{high:.1f}'] = bucket_acc
        
        return metrics
    
    def calculate_voting_metrics(self) -> Dict:
        """Analyze individual model voting patterns"""
        metrics = {}
        
        logger.info(f"🗳️  Analyzing voting from {len(self.model_predictions)} models...")
        
        for model_name, predictions in self.model_predictions.items():
            if not predictions:
                continue
            
            # Count predictions
            pred_counts = Counter(predictions)
            metrics[model_name] = {
                'predictions': dict(pred_counts),
                'total': len(predictions),
            }
        
        return metrics
    
    def print_report(self, metrics: Dict):
        """Pretty-print metrics report"""
        print("\n" + "="*70)
        print("ACCURACY METRICS REPORT")
        print("="*70)
        
        # Basic metrics
        print("\n📊 OVERALL METRICS:")
        print(f"   Accuracy:     {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
        if 'precision' in metrics:
            print(f"   Precision:    {metrics['precision']:.4f}")
            print(f"   Recall:       {metrics['recall']:.4f}")
            print(f"   F1 Score:     {metrics['f1']:.4f}")
        
        # Per-class metrics
        if 'per_class' in metrics:
            print("\n📈 PER-CLASS METRICS:")
            for label, stats in metrics['per_class'].items():
                print(f"\n   {label}:")
                print(f"      Precision: {stats['precision']:.4f}")
                print(f"      Recall:    {stats['recall']:.4f}")
                print(f"      F1:        {stats['f1']:.4f}")
                print(f"      Support:   {stats['support']}")
        
        # Confusion matrix
        if 'confusion_matrix' in metrics:
            cm = metrics['confusion_matrix']
            print("\n🔢 CONFUSION MATRIX:")
            labels = cm['labels']
            matrix = cm['matrix']
            print(f"    {'':10s}", end='')
            for label in labels:
                print(f"{label:>10s}", end='')
            print()
            for i, label in enumerate(labels):
                print(f"   {label:>8s}", end='')
                for j in range(len(labels)):
                    print(f"{matrix[i][j]:>10d}", end='')
                print()
        
        # Confidence metrics
        conf_metrics = metrics.get('confidence_metrics', {})
        if conf_metrics:
            print("\n🎯 CONFIDENCE METRICS:")
            c = conf_metrics.get('confidence', {})
            print(f"   Mean:      {c.get('mean', 0):.4f}")
            print(f"   Median:    {c.get('median', 0):.4f}")
            print(f"   Stdev:     {c.get('stdev', 0):.4f}")
            print(f"   Min/Max:   {c.get('min', 0):.4f} / {c.get('max', 0):.4f}")
            
            print("\n   AGREEMENT DISTRIBUTION:")
            agree_dist = conf_metrics.get('agreement_distribution', {})
            for level, count in agree_dist.items():
                pct = 100 * count / len(self.predictions)
                print(f"      {level:20s} {count:6d} ({pct:5.1f}%)")
        
        print("\n" + "="*70 + "\n")
    
    def generate_report(self, output_json: Optional[str] = None) -> Dict:
        """Generate complete report"""
        logger.info("🔍 Calculating metrics...")
        
        report = {
            'timestamp': str(Path(self.csv_file).stat().st_mtime),
            'total_predictions': len(self.predictions),
            'total_with_ground_truth': len(self.predictions),
            'basic_metrics': self.calculate_basic_metrics(),
            'confidence_metrics': self.calculate_confidence_metrics(),
            'voting_metrics': self.calculate_voting_metrics(),
        }
        
        # Print to console
        self.print_report(report)
        
        # Save to JSON
        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Make JSON serializable
            json_report = self._make_json_serializable(report)
            
            with open(output_path, 'w') as f:
                json.dump(json_report, f, indent=2)
            
            logger.info(f"✓ Report saved to: {output_json}")
        
        return report
    
    @staticmethod
    def _make_json_serializable(obj):
        """Convert numpy/complex types to JSON-serializable"""
        if isinstance(obj, dict):
            return {k: AccuracyMetricsCalculator._make_json_serializable(v) 
                   for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AccuracyMetricsCalculator._make_json_serializable(item) 
                   for item in obj]
        elif isinstance(obj, np.ndarray) if NUMPY_AVAILABLE else False:
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)) if NUMPY_AVAILABLE else False:
            return obj.item()
        else:
            return obj
    
    def plot_confusion_matrix(self, output_png: str):
        """Plot confusion matrix"""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("⚠️  matplotlib not available. Skipping confusion matrix plot.")
            return
        
        metrics = self.calculate_basic_metrics()
        cm = np.array(metrics['confusion_matrix']['matrix'])
        labels = metrics['confusion_matrix']['labels']
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=labels, yticklabels=labels)
        plt.title('Confusion Matrix')
        plt.ylabel('Ground Truth')
        plt.xlabel('Prediction')
        plt.tight_layout()
        plt.savefig(output_png, dpi=150)
        logger.info(f"✓ Confusion matrix saved to: {output_png}")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate accuracy metrics from ML predictions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic accuracy report
  python3 calculate_accuracy_metrics.py --predictions predictions.csv

  # Save JSON report and confusion matrix plot
  python3 calculate_accuracy_metrics.py \\
      --predictions predictions.csv \\
      --output metrics_report.json \\
      --confusion-matrix confusion_matrix.png
        """
    )
    
    parser.add_argument('--predictions', type=str, required=True,
                       help='Path to predictions CSV file')
    parser.add_argument('--output', type=str, default=None,
                       help='Output JSON file for metrics report')
    parser.add_argument('--confusion-matrix', type=str, default=None,
                       help='Output PNG file for confusion matrix plot')
    
    args = parser.parse_args()
    
    try:
        # Create calculator
        calculator = AccuracyMetricsCalculator(args.predictions)
        
        # Generate report
        report = calculator.generate_report(output_json=args.output)
        
        # Plot confusion matrix
        if args.confusion_matrix:
            calculator.plot_confusion_matrix(args.confusion_matrix)
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
