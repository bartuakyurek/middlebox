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
import time
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
    msg_with_sequence = "[" + str(seq_number) + "]" + msg_str
    return msg_with_sequence


class CovertSender:
    def __init__(self, covert_msg, verbose=False, window_size=5, timeout=5, MAX_UDP_PAYLOAD_SIZE=1458, port=9999, recv_port=8888):        
        self.verbose = verbose
        self.timeout = timeout
        self.max_payload = MAX_UDP_PAYLOAD_SIZE
        self.covert_msg = covert_msg

        self.HEADER_LEN = 8       
        self.covert_bits_str = self._convert_to_covert_bits_str(covert_msg, self.HEADER_LEN)

        self.total_covert_bits = len(self.covert_bits_str)

        print(f"[INFO] Covert bits string: {self.covert_bits_str}")
        print(f"[INFO] There are {self.total_covert_bits} bits to be sent covertly.")

        self.port = port
        self.recv_port = recv_port
        self.recv_ip = self.get_host()
        self.received_acks = {} # Store sequence numbers as well as their timestamps
        self.ack_sock = self.create_udp_socket('', self.port) # Socket dedicated to receive ACK
        
        self.cur_pkt_idx = 0
        self.window_start = 0
        self.window_size = window_size
        self.lock = threading.Lock()

        if verbose: print("[INFO] CovertSender created. Call send() to start sending packets.")

    def get_host(self, IP_NAME='INSECURENET_HOST_IP'):
        host = os.getenv(IP_NAME)
        if not host:
            raise ValueError("SECURENET_HOST_IP environment variable is not set.")
        return host
    
    def create_udp_socket(self, ip, port):
         
         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
         sock.bind((ip, port))
         if self.verbose: print("[INFO] Socket created successfully.")
         return sock
    
    def shutdown(self):
        self.ack_sock.close()


    def get_ACK(self):
        # Listen for ACKs until all the covert bits are sent
        # WARNING: This assumes the rest of the message is not ACKed
        # so some packets after the covert bits may be lost
        while self.cur_pkt_idx < self.total_covert_bits:
            data, addr = self.ack_sock.recvfrom(4096)
            seq_num = int(data.decode())
            if self.verbose: print(f"[ACK] ({data}) received from {addr}. Sequence number: {seq_num}")

            # Save the ACK timestamp with sequence number as key
            with self.lock: # To avoid race conditions
                if seq_num not in self.received_acks:
                    self.received_acks[seq_num] = time.time() # TODO: I assumed this could be useful for packet stats, but is it used?
                else:
                    if self.verbose: print(f"[ACK] Duplicate ACK received for sequence number {seq_num}. Ignoring it.")
                
                while self.window_start in self.received_acks: 
                    self.window_start += 1 # Slide the window
                    if self.verbose: print(f"[SLIDE] Window is slided to {self.window_start}.")

    def send(self, message):
        # Sends a legitimate message
        # If the given message cannot fit into a single packet
        # it splits up and sends multiple packets
        encoded_msg = message.encode() 
        encoded_msg_chunks = split_message_into_chunks(encoded_msg, self.max_payload-8) # -8 is to be able to add sequence number in the beginning 
        if self.verbose: print(f"[INFO] Message is splitted into {len(encoded_msg_chunks)} chunks.")

        # Create a daemon to receive ACKs continuously
        ack_thread = threading.Thread(target=self.get_ACK, daemon=True)
        ack_thread.start()
        if self.verbose: print("[INFO] ACK thread started.")

        # Send message packets
        # WARNING: This assumes the rest of the message after all the
        # covert bits are sent, can be dropped. (See get_ACK() Warning)
        packet_timers = {}
        while self.cur_pkt_idx < self.total_covert_bits: #len(encoded_msg_chunks):    
            if self.verbose: print("Current bit index:", self.cur_pkt_idx, " / total packets ", len(encoded_msg_chunks))
            with self.lock: 
                # Send all the packets within the window
                while self.cur_pkt_idx < self.window_start + self.window_size:
                    msg = encoded_msg_chunks[self.cur_pkt_idx]
                    msg_str = assign_sequence_number(msg.decode(), self.cur_pkt_idx)
                    if self.verbose: print(f"[INFO] Appended sequence number to message: {msg_str}")

                    if self.cur_pkt_idx >= self.total_covert_bits:
                        if self.verbose: print("[INFO] All bits have been sent...")
                        bit = None
                    else:                
                        bit = self.covert_bits_str[self.cur_pkt_idx]

                    self._send_packet(msg_str, bit)
                    packet_timers[self.cur_pkt_idx] = time.time()
                    self.cur_pkt_idx += 1
                
                # Timeout checks
                for idx in range(self.window_start, self.cur_pkt_idx):
                    if idx not in self.received_acks:
                        if time.time() - packet_timers[idx] > self.timeout:
                            if self.verbose: print(f"[TIMEOUT] Packet {idx} timed out. Resending...")
                            self._send_packet(encoded_msg_chunks[idx], self.covert_bits_str[idx])
                            packet_timers[idx] = time.time() # Reset the timer

    def _send_packet(self, message, cov_bit=None):
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

    default_carrier_msg = "Hello, this is a long message. " * 120
    default_covert_msg = "This is a covert message."
    default_window_size = 5
    default_udp_payload = 20 # 1458 for a typical 1500 MTU Ethernet network but I use smaller for sending more packets.

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="print intermediate steps", action="store_true", default=False)
    parser.add_argument("-c", "--covert", help="covert message to be sent", type=str, default=default_covert_msg, required=False)
    parser.add_argument("-o", "--overt", help="carrier message to be sent", type=str, default=default_carrier_msg, required=False)

    parser.add_argument("-w", "--window", help=f"sliding window size, default {default_window_size}", type=int, default=default_window_size, required=False)
    parser.add_argument("-s", "--udpsize", help=f"maximum UDP payload size, default {default_udp_payload}. use small value to send more covert bits.", type=int, default=default_udp_payload, required=False) 
    args = parser.parse_args()
    
    # WARNING: If the length of the carrier message is too short
    # not all the covert bits will be sent. 
    carrier_msg = args.overt
    covert_msg =  args.covert
    sender = CovertSender(covert_msg=covert_msg, verbose=args.verbose, 
                          window_size=args.window, timeout=5, 
                          MAX_UDP_PAYLOAD_SIZE=args.udpsize)

    try:
        print("[INFO] Sending message... This might take a while.")
        sender.send(carrier_msg) 
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        sender.shutdown()
        print("[INFO] Sending completed. Socket closed. Stop receiver process to see the message.")
