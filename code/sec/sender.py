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
import threading
from scapy.all import IP, UDP, Raw, send

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
    def __init__(self, covert_msg, verbose=False, timeout=5, MAX_UDP_PAYLOAD_SIZE=1458, port=9999, recv_port=8888):        
        self.verbose = verbose
        self.timeout = timeout
        self.max_payload = MAX_UDP_PAYLOAD_SIZE
        self.covert_msg = covert_msg

        self.HEADER_LEN = 8       
        self.covert_bits_str = self._convert_to_covert_bits_str(covert_msg, self.HEADER_LEN)

        self.total_covert_bits = len(self.covert_bits_str)
        self.current_bit_idx = 0 
        print(f"[INFO] Covert bits string: {self.covert_bits_str}")
        print(f"[INFO] There are {self.total_covert_bits} bits to be sent covertly.")

        self.port = port
        self.recv_port = recv_port
        self.recv_ip = self.get_host()
        self.ack_sock = self.create_udp_socket(self.recv_ip) # Socket dedicated to receive ACK
        
        if verbose: print("[INFO] CovertSender created. Call send() to start sending packets.")

    def get_host(self, IP_NAME='INSECURENET_HOST_IP'):
        host = os.getenv(IP_NAME)
        if not host:
            raise ValueError("SECURENET_HOST_IP environment variable is not set.")
        return host
    
    def create_udp_socket(self, host_ip=None):
         if host_ip is None: host_ip = self.recv_ip
         else: 
             self.recv_ip = host_ip
             print(f"[WARNING] Host IP changed to {host_ip}")

         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
         if self.verbose: print("[INFO] Socket created successfully.")
         return sock
    
    def shutdown(self):
        self.ack_sock.close()


    def get_ACK(self):
        pass # TODO: Receive ACK

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

            if self.current_bit_idx >= self.total_covert_bits:
                if self.verbose: print("[INFO] All bits have been sent...")
                bit = None
            else:                
                bit = self.covert_bits_str[self.current_bit_idx]

            self._send_packet(msg_str, bit)
            self.current_bit_idx += 1

    def _send_packet(self, message, cov_bit=None)->int:
        # Send packet using UDP with ACK
        # Returns 0 if message sent successfully
        # -1 if it cannot be delivered in max_resend trials.
        ip = IP(dst=self.recv_ip)
        udp = UDP(dport=self.recv_port, sport=self.port)
        # Covert bit as checksum field existence
        if cov_bit == '1' or cov_bit == None: # None when no covrt bit is sent
            udp.chksum = None  # Let OS/scapy compute it
        elif cov_bit == '0':
            udp.chksum = 0  # Explicitly remove checksum
        else:
            raise ValueError(f"Invalid covert bit. Must be '0' or '1'. Got: {cov_bit}")
        
        pkt = ip/udp/Raw(load=message)
        send(pkt, verbose=False)
        if self.verbose: print(f"[INFO] Message sent to {self.recv_ip}:{self.recv_port}")
            
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
    
    MAX_UDP_PAYLOAD_SIZE = 20 # 1458 for a typical 1500 MTU Ethernet network

    # WARNING: If the length of the carrier message is too short
    # not all the covert bits will be sent. 
    carrier_msg = "Hello, this is a long message. " * 100
    covert_msg = "This is a covert message." 
    sender = CovertSender(covert_msg=covert_msg, verbose=True, timeout=5, 
                          MAX_UDP_PAYLOAD_SIZE=MAX_UDP_PAYLOAD_SIZE)

    try:
        sender.send(carrier_msg) 
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        sender.shutdown()
