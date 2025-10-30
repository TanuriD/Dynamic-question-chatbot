# Enhanced train_model.py with comprehensive evaluation metrics
import re
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    classification_report, 
    accuracy_score, 
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score
)

DATA_PATH = Path("district_mapping.csv")
MODEL_OUT = Path("district_knn_model.joblib")

def normalize_phone(ph: str) -> str:
    """Cleans and normalizes Sri Lankan phone numbers."""
    if ph is None:
        return ""
    s = re.sub(r"\D", "", str(ph))  # remove non-digits
    if s.startswith("94") and len(s) > 2:
        s = s[2:]  # remove +94
    if s.startswith("0"):
        s = s[1:]  # remove leading 0
    return s

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract prefix features for classification."""
    df = df.copy()
    df["phone_str"] = df["phone"].apply(normalize_phone)
    df["pref2"] = df["phone_str"].str[:2].fillna("NA")
    df["pref3"] = df["phone_str"].str[:3].fillna("NA")
    df["pref4"] = df["phone_str"].str[:4].fillna("NA")
    return df

def plot_confusion_matrix(y_true, y_pred, class_names, title="Confusion Matrix"):
    """Plot and save confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names)
    plt.title(title)
    plt.xlabel('Predicted District')
    plt.ylabel('Actual District')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
    plt.show()
    print(f"📊 Confusion matrix saved as 'confusion_matrix.png'")

def print_detailed_evaluation(y_train, y_train_pred, y_test, y_test_pred, class_names):
    """Print comprehensive evaluation metrics."""
    
    print("=" * 80)
    print("📊 COMPREHENSIVE MODEL EVALUATION REPORT")
    print("=" * 80)
    
    # Training Set Performance
    print("\n🎯 TRAINING SET PERFORMANCE:")
    print("-" * 40)
    train_accuracy = accuracy_score(y_train, y_train_pred)
    train_precision = precision_score(y_train, y_train_pred, average='weighted')
    train_recall = recall_score(y_train, y_train_pred, average='weighted')
    train_f1 = f1_score(y_train, y_train_pred, average='weighted')
    
    print(f"Training Accuracy:  {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
    print(f"Training Precision: {train_precision:.4f}")
    print(f"Training Recall:    {train_recall:.4f}")
    print(f"Training F1-Score:  {train_f1:.4f}")
    
    # Test Set Performance
    print("\n🧪 TEST SET PERFORMANCE:")
    print("-" * 40)
    test_accuracy = accuracy_score(y_test, y_test_pred)
    test_precision = precision_score(y_test, y_test_pred, average='weighted')
    test_recall = recall_score(y_test, y_test_pred, average='weighted')
    test_f1 = f1_score(y_test, y_test_pred, average='weighted')
    
    print(f"Test Accuracy:      {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
    print(f"Test Precision:     {test_precision:.4f}")
    print(f"Test Recall:        {test_recall:.4f}")
    print(f"Test F1-Score:      {test_f1:.4f}")
    
    # Overfitting Analysis
    print("\n⚠️  OVERFITTING ANALYSIS:")
    print("-" * 40)
    accuracy_diff = train_accuracy - test_accuracy
    if accuracy_diff < 0.05:
        print("✅ Good generalization - minimal overfitting")
    elif accuracy_diff < 0.1:
        print("⚠️  Moderate overfitting detected")
    else:
        print("❌ Significant overfitting detected")
    
    print(f"Accuracy difference (Train - Test): {accuracy_diff:.4f}")
    
    # Detailed Classification Report
    print("\n📋 DETAILED CLASSIFICATION REPORT:")
    print("-" * 40)
    print(classification_report(y_test, y_test_pred, target_names=class_names))
    
    # Confusion Matrix
    print("\n🔢 CONFUSION MATRIX:")
    print("-" * 40)
    cm = confusion_matrix(y_test, y_test_pred)
    print("Confusion Matrix (Test Set):")
    print(cm)
    
    return {
        'train_accuracy': train_accuracy,
        'test_accuracy': test_accuracy,
        'train_precision': train_precision,
        'test_precision': test_precision,
        'train_recall': train_recall,
        'test_recall': test_recall,
        'train_f1': train_f1,
        'test_f1': test_f1,
        'accuracy_diff': accuracy_diff
    }

def main():
    print("🚀 Starting Enhanced District Prediction Model Training")
    print("=" * 60)
    
    # Load and preprocess
    print("📂 Loading and preprocessing data...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Dataset shape: {df.shape}")
    print(f"   Districts: {df['district'].nunique()}")
    
    df = make_features(df)
    X = df[["pref2", "pref3", "pref4"]]
    y = df["district"]
    
    # Get unique class names for plotting
    class_names = sorted(y.unique())
    print(f"   Unique districts: {len(class_names)}")

    # Train/test split
    print("\n🔄 Splitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, stratify=y, test_size=0.2, random_state=42
    )
    print(f"   Training set: {X_train.shape[0]} samples")
    print(f"   Test set: {X_test.shape[0]} samples")

    # Preprocess and model pipeline
    print("\n🔧 Building model pipeline...")
    categorical_features = ["pref2", "pref3", "pref4"]
    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)]
    )

    model = Pipeline([
        ("pre", preprocessor),
        ("clf", KNeighborsClassifier(n_neighbors=5))
    ])

    # Training
    print("\n🏋️ Training KNN model...")
    model.fit(X_train, y_train)
    
    # Predictions
    print("🔮 Making predictions...")
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    
    # Comprehensive evaluation
    metrics = print_detailed_evaluation(y_train, y_train_pred, y_test, y_test_pred, class_names)
    
    # Plot confusion matrix
    print("\n📊 Generating confusion matrix plot...")
    try:
        plot_confusion_matrix(y_test, y_test_pred, class_names, 
                            "District Prediction Confusion Matrix")
    except Exception as e:
        print(f"⚠️  Could not generate confusion matrix plot: {e}")
        print("   (This might be due to missing matplotlib/seaborn)")

    # Save model
    print(f"\n💾 Saving model to {MODEL_OUT.resolve()}...")
    joblib.dump(model, MODEL_OUT)
    
    # Save evaluation metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv('model_evaluation_metrics.csv', index=False)
    print("📈 Evaluation metrics saved to 'model_evaluation_metrics.csv'")
    
    print("\n✅ Training completed successfully!")
    print("=" * 60)
    
    return model, metrics

if __name__ == "__main__":
    model, metrics = main()
