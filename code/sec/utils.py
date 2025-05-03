
import os
import csv

import random
import string

def save_session_csv(
    sender,
    session_id,
    covert_msg,
    overt_msg,
    mode="covert", 
    filename=None
):
    if filename is None:
        filename = f"covert_session_{session_id}.csv"

    fieldnames = [
        "seq_num",
        "mode",
        "covert_bit",
        "acknowledged",
        "overt_payload",
        "checksum",
        "timestamp_ack"
    ]

    file_exists = os.path.isfile(filename)

    with open(filename, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Only write the header if the file didn't exist before
        if not file_exists:
            writer.writeheader()

        """for seq in range(sender.session_covert_bits_len):
            packet = sender.outgoing_packets.get(seq)
            if not packet:
                continue

            writer.writerow({
                "seq_num": seq,
                "mode": mode,
                "covert_bit": sender.covert_bits_str[seq],
                "checksum": packet["checksum"],
                "timestamp_ack": sender.received_acks.get(seq, None)
            })
        """
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
