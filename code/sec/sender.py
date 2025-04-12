# Reliable UDP Communication
# 
# ------------------------------------------------------------------------------------------------
"""
CovertSender Class
--------------------
Responsible for sending UDP packets with covert message embedded in checksum field.
The existence of checksum encodes 1 bit of covert message.

Note on some members:
HEADER_LEN: A constant int to be added as a header to the covert message.
Agree on how many bits to send covertly in the beginning to tell the length of covert message. 
E.g. to send 3 bits of covert message, and fixed header is 8 bits, send: 0000 0011

"""
# ------------------------------------------------------------------------------------------------

import os
import socket
import argparse

# Define the maximum allowed packet size (adjust based on your network MTU)

def assert_type(obj, desired_type, note=""):
    assert isinstance(obj, desired_type), f"[ERROR] Expected {note} to be type {desired_type}, got {type(obj)}"

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
    msg_with_sequence = "[" + str(seq_number) + "]" + " " + msg_str
    return msg_with_sequence


class CovertSender:
    def __init__(self, covert_msg, verbose=False, timeout=5, MAX_UDP_PAYLOAD_SIZE=1458):        
        self.verbose = verbose
        self.timeout = timeout
        self.max_payload = MAX_UDP_PAYLOAD_SIZE
        self.covert_msg = covert_msg

        self.HEADER_LEN = 8       
        self.covert_bits_str = self._convert_to_covert_bits_str(covert_msg, self.HEADER_LEN)
        print(f"[INFO] Covert bits string: {self.covert_bits_str}")
        
        self.port = 8888
        self.host_ip = self.get_host()
        self.sock = self.create_socket()
        
        if verbose: print("[INFO] CovertSender created. Call send() to start sending packets.")

    def get_host(self, IP_NAME='INSECURENET_HOST_IP'):
        host = os.getenv(IP_NAME)
        if not host:
            raise ValueError("SECURENET_HOST_IP environment variable is not set.")
        return host
    
    def create_socket(self, host_ip=None):
         if host_ip is None: host_ip = self.host_ip
         else: 
             self.host_ip = host_ip
             print(f"[WARNING] Host IP changed to {host_ip}")

         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
         if self.verbose: print("[INFO] Socket created successfully.")
         return sock
    
    def shutdown(self):
        self.sock.close()

    def send(self, message):
        # Sends a legitimate message
        # If the given message cannot fit into a single packet
        # it splits up and sends multiple packets
            
        encoded_msg = message.encode() 
        encoded_msg_chunks = split_message_into_chunks(encoded_msg, self.max_payload-8) # -8 is to be able to add sequence number in the beginning 
        if self.verbose: print(f"[INFO] Message is splitted into {len(encoded_msg_chunks)} chunks.")

        # Send message packets
        for i, msg in enumerate(encoded_msg_chunks):
            msg_str = assign_sequence_number(msg.decode(), i)
            if self.verbose: print(f"[INFO] Appended sequence number to message: {msg_str}")

            udp_status = self._send_packet(msg_str)

    def _send_packet(self, message, max_resend=100)->int:
        # Send packet using UDP with ACK
        # Returns 0 if message sent successfully
        # -1 if it cannot be delivered in max_resend trials.
        self.sock.settimeout(self.timeout)
        trials = 0
        while True:
            trials += 1
            if trials > max_resend: return -1
            try: # Send the message
                
                encoded_msg = message.encode()
                assert len(encoded_msg) < MAX_UDP_PAYLOAD_SIZE, f"Maximum UDP payload is exceeded ({len(encoded_msg)}>{MAX_UDP_PAYLOAD_SIZE}), the message should be splitted into chunks or increase payload."

                self.sock.sendto(encoded_msg, (self.host_ip, self.port))
                if self.verbose: print(f"[INFO] Message sent to {self.host_ip}:{self.port}")

                # Wait for acknowledgment
                response, server = self.sock.recvfrom(4096)
                if response.decode() == "ACK":
                    if self.verbose: print("[INFO] Acknowledgment received. Message delivered successfully.")
                    break
            except socket.timeout:
                print("[INFO] Timeout occurred. Resending message...")
                
        return 0
            
    def _convert_to_covert_bits_str(self, covert_msg_str, header_len)->str:
        assert_type(covert_msg_str, str, "covert message")
        assert_type(header_len, int, "header length")
        covert_bytes = covert_msg_str.encode()
        covert_len = len(covert_bytes)

        covert_len_bits_str = bin(covert_len)[2:]
        assert len(covert_len_bits_str) <= self.HEADER_LEN, f"[ERROR] Length of the covert message exceeds maximum length allowed. At least {len(covert_len_bits_str)} bits needed, current header length is {self.HEADER_LEN}"
        covert_len_bits_str_padded = covert_len_bits_str.zfill(self.HEADER_LEN) # Pad remaining bits with zeroes
        
        msg_bits_string = message_to_bits(covert_bytes)
        return covert_len_bits_str_padded + msg_bits_string

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # TODO: Add timeout parameter, overt msg, covert msg
    MAX_UDP_PAYLOAD_SIZE = 80 # 1458 for a typical 1500 MTU Ethernet network


    carrier_msg = "Hello, this is a long message. " * 50
    covert_msg = "I'm a covert message."
    sender = CovertSender(covert_msg=covert_msg, verbose=True, timeout=5, 
                          MAX_UDP_PAYLOAD_SIZE=MAX_UDP_PAYLOAD_SIZE)

    try:
        sender.send(carrier_msg) 
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        sender.shutdown()
