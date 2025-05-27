


import os 
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report

data_folder_path = os.environ.get("DATA_PATH")
data_csv_path = os.path.join(data_folder_path, "covert_sessions.csv")

# Load the CSV
df = pd.read_csv(data_csv_path) # timestamp,checksum,payload,length,is_covert

# Create derived features
df["delta_time"] = df["timestamp"].diff().fillna(0)
df["checksum_entropy"] = df["checksum"].apply(lambda x: len(set(str(x))) / len(str(x)) if len(str(x)) > 0 else 0)

# Select features and labels
features = ["checksum"] #["timestamp", "checksum", "length"] #["length", "delta_time", "checksum_entropy"]
X = df[features]
y = df["is_covert"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features (optional, might help)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Initialize classifier
model = XGBClassifier(use_label_encoder=False, eval_metric='logloss')

# Fit model
model.fit(X_train, y_train)

# Predict
y_pred = model.predict(X_test)

# Evaluate
acc = accuracy_score(y_test, y_pred)
print(f"Accuracy: {acc:.4f}")
print("Classification Report:\n", classification_report(y_test, y_pred))

import matplotlib.pyplot as plt

# Create plot
fig, ax = plt.subplots(figsize=(10, 6))
xgb.plot_importance(model, ax=ax)
plt.tight_layout()

# Save to file
plt.savefig("feature_importance.png", dpi=300)
print("Feature importance plot saved to feature_importance.png")