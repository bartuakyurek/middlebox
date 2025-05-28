


import os
import csv
import uuid
import json
import random
import string
import hashlib

def _get_unique_filepath(base_name="", filetype="csv",  seperator="", length=8, rootpath=None):
    session_id = str(uuid.uuid4())[:8]  # Shorten 
    filename = f"{base_name}{seperator}{session_id}.csv"

    if rootpath:
        return os.path.join(rootpath, filename)
    return filename

def _hash_params(params):
    # Deterministically hash sorted params to identify duplicates
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(param_str.encode()).hexdigest()

def _get_metadata(json_path):
    # Check if .json exists
    # If true, load it
    # Else, return empty dictionary
    # Return a dictionary of metadata
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {}
    return metadata

def _dump_metadata(metadata, metadata_path):
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"[INFO] New session saved. Metadata updated: {metadata_path}")

def _save_metadata(params, metadata, metadata_path, rootpath=""):
    # Returns the associated csv dataset path with given params
    param_hash = _hash_params(params)

    # Check if .json contains the params
    csv_path = "error_path"

    if param_hash in metadata:
        csv_path = metadata[param_hash]["filename"] # Read csv_path from metadata
        print(f"[INFO] Found existing file for identical params: {csv_path}")

    else: 
        # Create a unique csv path, add it to metadata
        csv_path = _get_unique_filepath("covert_sessions", filetype="csv", seperator="_", rootpath=rootpath)

        metadata[param_hash] = {
            "params": params,
            "filename": csv_path,
        }
        _dump_metadata(metadata=metadata, metadata_path=metadata_path)

    return csv_path

def save_session(
    params,
    outgoing_packets=None,
    metadata_filename="dataset_metadata.json"
):
    rootpath = os.environ.get("DATA_PATH")
    metadata_path = os.path.join(rootpath, metadata_filename)

    # Retrieve metadata from path, if not exist, create it 
    metadata = _get_metadata(json_path=metadata_path)
    csv_path = _save_metadata(params=params, metadata_path=metadata_path, metadata=metadata, rootpath=rootpath)

    print(f"[INFO] Saving session to {csv_path}")
    save_session_csv(
                     filepath=csv_path,
                     outgoing_packets=outgoing_packets)
    return

def save_session_csv(
    filepath=None,
    outgoing_packets=None,
):
    
    fieldnames = [
        "timestamp",
        "checksum",
        "payload",
        "length",
        "is_covert"
    ]

    file_exists = os.path.isfile(filepath)

    with open(filepath, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Only write the header if the file didn't exist before
        if not file_exists:
            writer.writeheader()

        for pkt_dict in outgoing_packets:
            writer.writerow(pkt_dict)
    
    print(f"[INFO] CSV log appended to {filepath}")





def assert_type(obj, desired_type, note=""):
    assert isinstance(obj, desired_type), f"[ERROR] Expected {note} to be type {desired_type}, got {type(obj)}"

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def message_to_bits(msg)->str:
    # msg : str or bytes
    if isinstance(msg, str): msg = msg.encode()
    assert_type(msg, bytes, "message")
    return ''.join(format(byte, '08b') for byte in msg)

def split_message_into_chunks(encoded_message, chunk_size)->list:
    chunks = []
    for i in range(0, len(encoded_message), chunk_size):
        chunk = encoded_message[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

def assign_sequence_number(msg_str, seq_number)->str:
    assert_type(msg_str, str, "message")
    msg_with_sequence = "[" + str(seq_number) + "]" + msg_str
    return msg_with_sequence

