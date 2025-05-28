


import os 
import numpy as np
import matplotlib.pyplot as plt

import json
import hashlib

from train import train


def _hash_params(params):
    # This should be the same in sec/utils.py
    # TODO: could utils.py be in shared data path? to avoid duplicates
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(param_str.encode()).hexdigest()

def _get_metadata(json_path):
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            metadata = json.load(f)
        return metadata
    else:
        raise FileNotFoundError

def _get_associated_csv(metadata_path, params):
    metadata = _get_metadata(metadata_path)
    param_hash = _hash_params(params)

    print("Param hash: ", param_hash)
    print("Metadata keys: ", metadata.keys())
    if param_hash in metadata:
        csv_path = metadata[param_hash]["filename"] # Read csv_path from metadata
        print(f"[INFO] Found associated dataset in {csv_path}")
        return csv_path
    else:
        raise KeyError("Parameters ", params, " not found in dataset!")

def run_phase3_experiments(metadata_path):
    
    # Free parameter
    window_sizes = [1, 2, 4, 8, 16, 32]

    # Fixed parameters (from default args)
    timeout = 0.5
    trans = 1

    for window in window_sizes:
        params = {
                    "window_size": window,
                    "timeout": timeout,
                    "trans": trans,
                }
        
        data_csv_path = _get_associated_csv(metadata_path=metadata_path, params=params)
        model, acc, report, confusion_dict, num_samples = train(data_csv_path=data_csv_path)

        print(f"Accuracy: {acc:.4f}")
        print("Classification Report:\n", report)
        print("Confusion matrix:\n", confusion_dict)
        print("Total test samples: ", num_samples)

    return


if __name__ == '__main__':

    rootpath = os.environ.get("DATA_PATH")
    metadata_filename="dataset_metadata.json"
    metadata_path = os.path.join(rootpath, metadata_filename)
    run_phase3_experiments(metadata_path=metadata_path)

    