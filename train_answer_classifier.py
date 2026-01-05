# 2️⃣ Answer Classifier Training Script
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

df = pd.read_csv("answer_training.csv")
X = df["reply"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

answer_model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1,2))),
    ("clf", LogisticRegression(max_iter=1000))
])

answer_model.fit(X_train, y_train)
y_pred = answer_model.predict(X_test)
print("\nANSWER CLASSIFIER REPORT\n")
print(classification_report(y_test, y_pred))

joblib.dump(answer_model, "models/answer_classifier.pkl")
print("Saved: models/answer_classifier.pkl")
