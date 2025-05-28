


import os 
import numpy as np
import matplotlib.pyplot as plt

import json
import hashlib

from train import train

 # TODO: could utils.py be in shared data path? to avoid duplicates
# -------------------------------------------------------------------
def _hash_params(params):
    # This should be the same in sec/utils.py
   
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(param_str.encode()).hexdigest()

def _dump_metadata(metadata, metadata_path):
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"[INFO] New session saved. Metadata updated: {metadata_path}")
# -------------------------------------------------------------------

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

    if param_hash in metadata:
        csv_path = metadata[param_hash]["filename"] # Read csv_path from metadata
        print(f"[INFO] Found associated dataset in {csv_path}")
        return csv_path, param_hash
    else:
        raise KeyError("Parameters ", params, " not found in dataset!")

def _append_results_to_json(json_path, param_key, result_key_str, result_value):
    
    metadata = _get_metadata(json_path=json_path)
    data_dict = metadata[param_key]

    if result_key_str in data_dict:
        previous_results = data_dict[result_key_str]
        previous_results.append(result_value)
        data_dict[result_key_str] = previous_results
    else:
        # Create a new entry
        data_dict[result_key_str] = [result_value]

    metadata[param_key] = data_dict
    _dump_metadata(metadata=metadata, metadata_path=json_path)

def _remove_previous_results(metadata_path, param_key, result_key_str):
    metadata = _get_metadata(json_path=metadata_path)
    data_dict = metadata[param_key]

    if result_key_str in data_dict:
        data_dict[result_key_str] = []
    
    metadata[param_key] = data_dict
    _dump_metadata(metadata=metadata, metadata_path=metadata_path)

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
        
        data_csv_path, param_hash = _get_associated_csv(metadata_path=metadata_path, params=params)


        # Clean up
        _remove_previous_results(metadata_path=metadata_path, result_key_str="accuracy", param_key=param_hash)

        # Training and test TODO: could you separate train and test? so that you use the same model?
        model, acc, report, confusion_dict, num_samples = train(data_csv_path=data_csv_path)

        print(f"Accuracy: {acc:.4f}")
        print("Classification Report:\n", report)
        print("Confusion matrix:\n", confusion_dict)
        print("Total test samples: ", num_samples)

        # Save the results to .json to plot them later
        res_str = "accuracy"
        val = acc
        _append_results_to_json(json_path=metadata_path, 
                                param_key=param_hash,
                                result_key_str=res_str,
                                result_value=val)
        
    return


if __name__ == '__main__':

    rootpath = os.environ.get("DATA_PATH")
    metadata_filename="dataset_metadata.json"
    metadata_path = os.path.join(rootpath, metadata_filename)
    run_phase3_experiments(metadata_path=metadata_path)

    