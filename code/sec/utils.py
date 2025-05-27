


import os
import csv
import uuid
import json
import random
import string


def _get_unique_filepath(base_name="", filetype="csv",  seperator="", length=8, rootpath=None):
    session_id = str(uuid.uuid4())[:8]  # Shorten 
    filename = f"{base_name}{seperator}{session_id}.csv"

    if rootpath:
        return os.path.join(rootpath, filename)
    return filename


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

def save_session(
    params,
    outgoing_packets=None,
    metadata_filename="dataset_metadata.json"
):
    data_folder_path = os.environ.get("DATA_PATH")
    metadata_path = os.path.join(data_folder_path, metadata_filename)

    metadata = _get_metadata(json_path=metadata_path)

    # Check if .json contains the params
    # If True, read filename 
    # Else, create a unique csv path
    csv_path = _get_unique_filepath("covert_sessions", filetype="csv", seperator="_", rootpath=data_folder_path)
    # and add params and filename to .json
        
    save_session_csv(
                     filepath=csv_path,
                     outgoing_packets=outgoing_packets)


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



if __name__ == '__main__':
    import pickle

    # Test packet dataset saving
    with open("outgoing_packets.pkl", "rb") as f:
        outgoing_packets = pickle.load(f)

    save_session(
                        session_id=0, # ignored if filename is given
                        filename="covert_sessions.csv",
                        outgoing_packets=outgoing_packets
                        )
        