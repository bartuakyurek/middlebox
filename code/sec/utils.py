import os
import csv

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

    print(f"[INFO] CSV log appended to {filename}")
