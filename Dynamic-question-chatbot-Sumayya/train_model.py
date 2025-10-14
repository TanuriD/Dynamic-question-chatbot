# train_model.py
import re
import joblib
import pandas as pd
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, accuracy_score

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

def main():
    # Load and preprocess
    df = pd.read_csv(DATA_PATH)
    df = make_features(df)
    X = df[["pref2", "pref3", "pref4"]]
    y = df["district"]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

    # Preprocess and model pipeline
    categorical_features = ["pref2", "pref3", "pref4"]
    preprocessor = ColumnTransformer(
        transformers=[("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)]
    )

    model = Pipeline([
        ("pre", preprocessor),
        ("clf", KNeighborsClassifier(n_neighbors=5))
    ])

    print("Training KNN model...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("\nEvaluation Report:")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))

    # Save model
    joblib.dump(model, MODEL_OUT)
    print(f"\n✅ Model saved to {MODEL_OUT.resolve()}")

if __name__ == "__main__":
    main()
