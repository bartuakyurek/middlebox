


import os 
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix


data_folder_path = os.environ.get("DATA_PATH")
data_csv_path = os.path.join(data_folder_path, "covert_sessions.csv")

# Load the CSV
df = pd.read_csv(data_csv_path) # timestamp,checksum,payload,length,is_covert

# Select features and labels
features = ["length"]
X = df[features]
y = df["is_covert"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features (optional, might help)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

print(X_train)