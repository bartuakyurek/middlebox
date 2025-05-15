
import os
import csv

import random
import string

def save_session_csv(
    session_id=0,
    filename=None,
    outgoing_packets=None,
):
    if filename is None:
        filename = f"covert_session_{session_id}.csv"

    fieldnames = [
        "timestamp",
        "checksum",
        "payload",
        "length",
        "is_covert"
    ]

    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Only write the header if the file didn't exist before
        if not file_exists:
            writer.writeheader()

        for pkt_dict in outgoing_packets:
            writer.writerow(pkt_dict)
    
    print(f"[INFO] CSV log appended to {filename}")



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

    save_session_csv(
                        session_id=0, # ignored if filename is given
                        filename="covert_sessions.csv",
                        outgoing_packets=outgoing_packets
                        )
        