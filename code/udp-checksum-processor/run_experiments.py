


import os 
import numpy as np
import matplotlib.pyplot as plt


from train import train






if __name__ == '__main__':
    data_folder_path = os.environ.get("DATA_PATH")
    data_csv_path = os.path.join(data_folder_path, f"covert_sessions.csv")

    model, acc, report, confusion_dict, num_samples = train(data_csv_path=data_csv_path)
    print(f"Accuracy: {acc:.4f}")
    print("Classification Report:\n", report)
    print("Confusion matrix:\n", confusion_dict)
    print("Total test samples: ", num_samples)
