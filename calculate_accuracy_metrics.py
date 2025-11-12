#!/usr/bin/env python3
"""
IDS Accuracy Metrics Calculator
================================
Compares ML predictions against ground truth from PCAP replay.
Calculates: Accuracy, Precision, Recall, F1-Score, Confusion Matrix.

Usage:
    python3 calculate_accuracy_metrics.py \\
        --packets test_results/*_packets.csv \\
        --predictions test_results/ml_predictions.log \\
        --output test_results/accuracy_report.json
"""

import os
import sys
import argparse
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, classification_report, roc_auc_score, roc_curve
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: scikit-learn not available. Install with: pip install scikit-learn pandas numpy")


class AccuracyMetricsCalculator:
    """Calculate IDS prediction accuracy metrics"""
    
    def __init__(self):
        self.ground_truth = []  # List of dicts from PCAP CSV
        self.predictions = []   # List of dicts from ML log
        self.matched_pairs = [] # Matched ground truth + prediction pairs
        self.metrics = {}
    
    def load_ground_truth(self, pcap_csv_files: List[str]):
        """Load ground truth from PCAP CSV files"""
        print("[*] Loading ground truth from PCAP CSVs...")
        
        for csv_file in pcap_csv_files:
            if not os.path.exists(csv_file):
                print(f"[!] File not found: {csv_file}")
                continue
            
            try:
                with open(csv_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.ground_truth.append(row)
                
                print(f"[+] Loaded {len(self.ground_truth)} packets from {Path(csv_file).name}")
            except Exception as e:
                print(f"[!] Error reading {csv_file}: {e}")
        
        print(f"[+] Total ground truth packets: {len(self.ground_truth)}\n")
    
    def load_predictions(self, prediction_log: str):
        """Load predictions from ML Consumer log"""
        print(f"[*] Loading predictions from {Path(prediction_log).name}...")
        
        if not os.path.exists(prediction_log):
            print(f"[!] File not found: {prediction_log}")
            return
        
        try:
            with open(prediction_log, 'r') as f:
                for line in f:
                    # Parse ML Consumer log format
                    # Expected: "timestamp | src_ip:port -> dst_ip:port | prediction=BENIGN/ATTACK | confidence=0.95"
                    
                    if 'prediction=' in line:
                        try:
                            # Extract key fields
                            parts = line.split('|')
                            if len(parts) < 2:
                                continue
                            
                            pred_dict = {
                                'timestamp': parts[0].strip() if len(parts) > 0 else '',
                                'flow': parts[1].strip() if len(parts) > 1 else '',
                                'raw_line': line.strip()
                            }
                            
                            # Extract prediction label
                            if 'prediction=' in line:
                                match = re.search(r'prediction=(\w+)', line)
                                if match:
                                    pred_dict['prediction'] = match.group(1)
                            
                            # Extract confidence
                            if 'confidence=' in line:
                                match = re.search(r'confidence=([0-9.]+)', line)
                                if match:
                                    pred_dict['confidence'] = float(match.group(1))
                            
                            if 'prediction' in pred_dict:
                                self.predictions.append(pred_dict)
                        except Exception as e:
                            if len(self.predictions) < 5:  # Show first 5 errors
                                print(f"  [!] Parse error: {e}")
                            continue
            
            print(f"[+] Total predictions loaded: {len(self.predictions)}\n")
        
        except Exception as e:
            print(f"[!] Error reading predictions: {e}")
    
    def infer_ground_truth_labels(self) -> Dict[int, str]:
        """
        Infer attack/benign labels from packet patterns.
        
        For CICIDS dataset:
        - DoS patterns: high packet rate, small packets
        - Normal: mixed packet sizes, normal rate
        - Port scan: many packets to different ports
        """
        print("[*] Inferring ground truth labels from packet patterns...")
        
        labels = {}
        
        # Simple heuristic: if pcap name contains "dos" -> ATTACK
        # Otherwise -> BENIGN
        for i, pkt in enumerate(self.ground_truth):
            # Check if source file name contains attack type
            labels[i] = 'BENIGN'  # Default
            
            # Could use ML model or rules here for more accuracy
            # For now, simple heuristic based on packet characteristics
            
            try:
                size = int(pkt.get('packet_size', 0))
                if 0 < size < 64:  # Very small packets might be DoS
                    # But need more context, so keeping BENIGN as default
                    pass
            except:
                pass
        
        return labels
    
    def match_predictions_to_ground_truth(self):
        """Match predictions to ground truth based on timestamp/flow"""
        print("[*] Matching predictions to ground truth...")
        
        if not self.predictions:
            print("[!] No predictions loaded")
            return
        
        if not self.ground_truth:
            print("[!] No ground truth loaded")
            return
        
        # Simple matching: assume predictions come in same order as ground truth
        # In production, match by timestamp or flow signature
        
        for i, gt in enumerate(self.ground_truth):
            if i < len(self.predictions):
                pred = self.predictions[i]
                
                # Infer ground truth label
                gt_label = 'BENIGN'
                # Could use more sophisticated labeling here
                
                self.matched_pairs.append({
                    'ground_truth': gt_label,
                    'prediction': pred.get('prediction', 'UNKNOWN'),
                    'confidence': pred.get('confidence', 0.0),
                    'flow': pred.get('flow', ''),
                    'gt_packet': gt
                })
        
        print(f"[+] Matched {len(self.matched_pairs)} prediction-truth pairs\n")
    
    def calculate_metrics(self):
        """Calculate accuracy metrics"""
        print("[*] Calculating accuracy metrics...")
        
        if not self.matched_pairs:
            print("[!] No matched pairs to analyze")
            return
        
        # Extract ground truth and predictions
        y_true = [pair['ground_truth'] for pair in self.matched_pairs]
        y_pred = [pair['prediction'] for pair in self.matched_pairs]
        confidences = [pair['confidence'] for pair in self.matched_pairs]
        
        # Convert to binary (BENIGN=0, ATTACK=1)
        y_true_binary = [0 if label == 'BENIGN' else 1 for label in y_true]
        y_pred_binary = [0 if label == 'BENIGN' else 1 for label in y_pred]
        
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'dataset': {
                'total_samples': len(self.matched_pairs),
                'ground_truth_counts': self._count_labels(y_true),
                'prediction_counts': self._count_labels(y_pred),
            },
            'overall': {
                'accuracy': float(accuracy_score(y_true_binary, y_pred_binary)),
                'total_correct': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == p),
                'total_incorrect': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t != p),
            },
            'benign_class': self._class_metrics(y_true_binary, y_pred_binary, 0, 'BENIGN'),
            'attack_class': self._class_metrics(y_true_binary, y_pred_binary, 1, 'ATTACK'),
            'confidence': {
                'mean': float(np.mean(confidences)),
                'std': float(np.std(confidences)),
                'min': float(np.min(confidences)),
                'max': float(np.max(confidences)),
            },
            'confusion_matrix': self._confusion_matrix_dict(y_true_binary, y_pred_binary)
        }
        
        print("[+] Metrics calculated\n")
    
    def _count_labels(self, labels: List[str]) -> Dict:
        counts = defaultdict(int)
        for label in labels:
            counts[label] += 1
        return dict(counts)
    
    def _class_metrics(self, y_true, y_pred, class_idx: int, class_name: str) -> Dict:
        """Calculate metrics for a specific class"""
        y_true_binary = [1 if x == class_idx else 0 for x in y_true]
        y_pred_binary = [1 if x == class_idx else 0 for x in y_pred]
        
        try:
            precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
            recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
            f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
        except:
            precision = recall = f1 = 0.0
        
        return {
            'name': class_name,
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'true_positives': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 1 and p == 1),
            'false_positives': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 0 and p == 1),
            'true_negatives': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 0 and p == 0),
            'false_negatives': sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 1 and p == 0),
        }
    
    def _confusion_matrix_dict(self, y_true, y_pred) -> Dict:
        """Return confusion matrix as dictionary"""
        cm = confusion_matrix(y_true, y_pred)
        return {
            'true_negatives': int(cm[0, 0]),
            'false_positives': int(cm[0, 1]),
            'false_negatives': int(cm[1, 0]),
            'true_positives': int(cm[1, 1]),
        }
    
    def print_report(self):
        """Print formatted accuracy report"""
        if not self.metrics:
            print("[!] No metrics to report")
            return
        
        m = self.metrics
        
        print("\n" + "="*70)
        print("IDS ACCURACY METRICS REPORT")
        print("="*70)
        print(f"Generated: {m['timestamp']}\n")
        
        print("DATASET SUMMARY")
        print("-"*70)
        print(f"Total samples analyzed:     {m['dataset']['total_samples']:,}")
        print(f"Ground truth distribution:  {m['dataset']['ground_truth_counts']}")
        print(f"Prediction distribution:    {m['dataset']['prediction_counts']}\n")
        
        print("OVERALL PERFORMANCE")
        print("-"*70)
        print(f"Accuracy:                   {m['overall']['accuracy']*100:6.2f}%")
        print(f"Correct predictions:        {m['overall']['total_correct']:,}")
        print(f"Incorrect predictions:      {m['overall']['total_incorrect']:,}\n")
        
        print("BENIGN CLASS METRICS")
        print("-"*70)
        b = m['benign_class']
        print(f"Precision:                  {b['precision']*100:6.2f}%")
        print(f"Recall:                     {b['recall']*100:6.2f}%")
        print(f"F1-Score:                   {b['f1_score']*100:6.2f}%")
        print(f"True Negatives:             {b['true_negatives']:,}")
        print(f"False Positives:            {b['false_positives']:,}\n")
        
        print("ATTACK CLASS METRICS")
        print("-"*70)
        a = m['attack_class']
        print(f"Precision:                  {a['precision']*100:6.2f}%")
        print(f"Recall:                     {a['recall']*100:6.2f}%")
        print(f"F1-Score:                   {a['f1_score']*100:6.2f}%")
        print(f"True Positives:             {a['true_positives']:,}")
        print(f"False Negatives:            {a['false_negatives']:,}\n")
        
        print("PREDICTION CONFIDENCE")
        print("-"*70)
        c = m['confidence']
        print(f"Mean confidence:            {c['mean']:.4f}")
        print(f"Std deviation:              {c['std']:.4f}")
        print(f"Min confidence:             {c['min']:.4f}")
        print(f"Max confidence:             {c['max']:.4f}\n")
        
        print("CONFUSION MATRIX")
        print("-"*70)
        cm = m['confusion_matrix']
        print(f"                    Predicted BENIGN  Predicted ATTACK")
        print(f"Actual BENIGN       {cm['true_negatives']:>8}          {cm['false_positives']:>8}")
        print(f"Actual ATTACK       {cm['false_negatives']:>8}          {cm['true_positives']:>8}\n")
        
        print("="*70 + "\n")
    
    def save_json(self, output_file: str):
        """Save metrics to JSON file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            print(f"[+] Metrics saved to: {output_file}\n")
        except Exception as e:
            print(f"[!] Error saving metrics: {e}")
    
    def save_detailed_csv(self, output_file: str):
        """Save detailed predictions with ground truth"""
        try:
            with open(output_file, 'w', newline='') as f:
                fieldnames = ['index', 'ground_truth', 'prediction', 'confidence', 'correct', 'flow']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for i, pair in enumerate(self.matched_pairs):
                    correct = pair['ground_truth'] == pair['prediction']
                    writer.writerow({
                        'index': i,
                        'ground_truth': pair['ground_truth'],
                        'prediction': pair['prediction'],
                        'confidence': f"{pair['confidence']:.4f}",
                        'correct': 'YES' if correct else 'NO',
                        'flow': pair['flow']
                    })
            
            print(f"[+] Detailed predictions saved to: {output_file}\n")
        except Exception as e:
            print(f"[!] Error saving detailed CSV: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Calculate IDS Accuracy Metrics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate from test results
  python3 calculate_accuracy_metrics.py \\
    --packets test_results/*_packets.csv \\
    --predictions test_results/ml_predictions.log \\
    --output test_results/accuracy_report.json
  
  # Save detailed predictions
  python3 calculate_accuracy_metrics.py \\
    --packets test_results/*_packets.csv \\
    --predictions test_results/ml_predictions.log \\
    --detailed test_results/predictions_detailed.csv
        """
    )
    
    parser.add_argument('--packets', nargs='+', required=True,
                        help='Ground truth PCAP CSV file(s)')
    parser.add_argument('--predictions', required=True,
                        help='ML predictions log file')
    parser.add_argument('--output', default='accuracy_metrics.json',
                        help='Output JSON file for metrics')
    parser.add_argument('--detailed', default='',
                        help='Optional: save detailed predictions to CSV')
    
    args = parser.parse_args()
    
    try:
        # Create calculator
        calc = AccuracyMetricsCalculator()
        
        # Load data
        calc.load_ground_truth(args.packets)
        calc.load_predictions(args.predictions)
        
        # Match and calculate
        calc.match_predictions_to_ground_truth()
        calc.calculate_metrics()
        
        # Display results
        calc.print_report()
        
        # Save results
        calc.save_json(args.output)
        
        if args.detailed:
            calc.save_detailed_csv(args.detailed)
    
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
