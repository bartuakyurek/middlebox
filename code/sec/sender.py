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
    def __init__(self, covert_msg, verbose=False, 
                 window_size=5, timeout=5, max_udp_payload=1458, max_trans=3,
                 port=9999, recv_port=8888):        
        self.verbose = verbose
        self.timeout = timeout
        self.max_payload = max_udp_payload
        self.max_trans = max_trans
        self.covert_msg = covert_msg

        self.HEADER_LEN = 8       
        self.covert_bits_str = self._convert_to_covert_bits_str(covert_msg, self.HEADER_LEN)

        self.total_covert_bits = len(self.covert_bits_str)

        if verbose: print(f"[INFO] Covert bits string: {self.covert_bits_str}")
        print(f"[INFO] There are {self.total_covert_bits} bits to be sent covertly.")

        self.port = port
        self.recv_port = recv_port
        self.recv_ip = self.get_host()
        self.received_acks = {} # Store sequence numbers as well as their timestamps
        self.ack_sock = self.create_udp_socket('', self.port) # Socket dedicated to receive ACK
        
        self.ack_thread = None
        self.total_packets_sent = 0 # WARNING: Assumes packets are sent only until all covert bits are sent
        self.cur_pkt_idx = 0
        self.window_start = 0
        self.window_size = window_size
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

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
        #if self.ack_thread is not None:
        #    self.ack_thread.join() # Wait for the ACK thread to finish
        self.ack_sock.close()

    def count_successful_transmissions(self):
        # Count the number of successful transmissions
        # print("Received ACKs: ", self.received_acks)
        num_success = 0
        for _, timestamp in self.received_acks.items():
            if timestamp != -1:
                num_success += 1
        return num_success
    
    def get_capacity(self):
        # Calculate the capacity of the channel by number of bits 
        # sent successfully over the total number of packets sent
        
        # WARNING: Since each packet carries 1 bit of covert message
        # in this design, the maximum capacity is 1 bit per packet.
        # With that being said, the capacity is calculated by 
        # counting number of successful transmissions assuming
        # each successful transmission carries 1 bit of covert message.
        # If it wasn't this design choice, one could carry more bits
        # per packet, then this capacity function would be obselete.

        # IMPORTANT WARNING: This function assumes that the receiver
        # is not sending any ACKs for the packets after the covert bits
        n_success = self.count_successful_transmissions()
        n_total = self.total_packets_sent #self.cur_pkt_idx
        if n_total == 0:
            print("[WARNING] No packets sent yet. The capacity is returned 0.")
            return 0
        
        capacity = n_success / n_total
        if self.verbose: 
            print(f"[INFO] Capacity: {capacity:.2%} ({n_success}/{n_total})")
            print(f"[WARNING] This capacity assumes the packet wasn't delivered if ACK wasn't received within the timeout but in fact,\n \
                    ACK may come later than the timeout, so the capacity may be higher than this value. Check the receiver's covert message to verify.")

        return capacity

    def get_ACK(self, sleep_time=0.1):
        # Listen for ACKs until all the covert bits are sent
        # WARNING: This assumes the rest of the message is not ACKed
        # so some packets after the covert bits may be lost.

        # Wait until every packet is either ACKed or marked as dropped
        while len(self.received_acks) < self.total_covert_bits and not self.stop_event.is_set():
            data, addr = self.ack_sock.recvfrom(4096)
            seq_num = int(data.decode())
            
            # Save the ACK timestamp with sequence number as key
            with self.lock: # To avoid race conditions
                if seq_num not in self.received_acks:
                    if self.verbose: print(f"[ACK] ({data}) received from {addr}. Sequence number: {seq_num}")
                    self.received_acks[seq_num] = time.time() # TODO: I assumed this could be useful for packet stats, but is it used?
                #else:
                #    if self.verbose: print(f"[ACK] Duplicate ACK received for sequence number {seq_num}. Ignoring it.")

                while self.window_start in self.received_acks: 
                    self.window_start += 1 # Slide the window
                    if self.verbose: print(f"[SLIDE] Window is slided to {self.window_start}.")

            time.sleep(sleep_time) # Sleep to let the other threads acquire the lock more easily

    def timeout_based_retransmissions(self, packet_transmission_count, packet_timers, msg_str_list):
        for idx in range(self.window_start, self.cur_pkt_idx):
            if idx not in self.received_acks:
                if time.time() - packet_timers[idx] > self.timeout:
                    
                    if packet_transmission_count[idx] >= self.max_trans:
                        if self.verbose: print(f"[TIMEOUT] Maximum transmission limit reached for packet {idx}. Dropping it.")
                        assert not idx in self.received_acks, f"[ERROR] Packet {idx} should not be in received_acks."
                        #self.received_acks[idx] = -1 # Mark it as missing 
                        if self.window_start == idx: self.window_start += 1 # Slide the window
                        
                    else:
                        if self.verbose: print(f"[TIMEOUT] Packet {idx} timed out. Resending...")
                        self.send_packet_with_covert(msg_str_list[idx], self.covert_bits_str[idx])
                        self.total_packets_sent += 1
                        packet_timers[idx] = time.time() # Reset the timer
                        packet_transmission_count[idx] += 1 # Increment transmission count
                                
    def create_ack_thread(self):
        self.ack_thread = threading.Thread(target=self.get_ACK, daemon=True)
        self.ack_thread.start()
        if self.verbose: print("[INFO] ACK thread started.")

    def send_packets_within_window(self, packet_timers, packet_transmission_count, msg_str_list):
        # Send all the packets within the window
                while self.cur_pkt_idx < self.window_start + self.window_size:
                    if self.verbose: print("Current bit index:", self.cur_pkt_idx) 

                    msg_str = msg_str_list[self.cur_pkt_idx]
                    if self.verbose: print(f"[INFO] Appended sequence number to message: {msg_str}")

                    if self.cur_pkt_idx >= self.total_covert_bits:
                        if self.verbose: print("[INFO] All bits have been sent...")
                        bit = None
                    else:                
                        bit = self.covert_bits_str[self.cur_pkt_idx]
   
                    self.send_packet_with_covert(msg_str, bit)
                    self.total_packets_sent += 1
                    packet_timers[self.cur_pkt_idx] = time.time()
                    packet_transmission_count[self.cur_pkt_idx] = 1 # Initialize transmission count
                    self.cur_pkt_idx += 1
                    if self.verbose: print("Total packets sent: ", self.total_packets_sent, " total received ACKs:",
                                           len(self.received_acks) )

    def process_and_send_msg(self, message):
        # Sends a legitimate message 
        # The given message is split into chunks of size max_payload
        # and sent over UDP with the covert bits embedded in the checksum field.
        encoded_msg = message.encode() 
        encoded_msg_chunks = split_message_into_chunks(encoded_msg, self.max_payload-8) # -8 is to be able to add sequence number in the beginning 
        print(f"[INFO] Message is splitted into {len(encoded_msg_chunks)} packets.")
        assert len(encoded_msg_chunks) >= self.total_covert_bits, f"[ERROR] Number of packets are not enough for the number of covert bits {len(encoded_msg_chunks)} < {self.total_covert_bits}, please increase the carrier message length."

        # Add sequence number to each chunk
        msg_str_list = [assign_sequence_number(chunk.decode(), i) for i, chunk in enumerate(encoded_msg_chunks)]
        
        # Create a daemon to receive ACKs continuously
        self.stop_event.clear()
        self.create_ack_thread()

        # Send message packets
        # WARNING: This assumes the rest of the message after all the
        # covert bits are sent, can be dropped. (See get_ACK() Warning)
        packet_timers, packet_transmission_count = {}, {}
        while self.cur_pkt_idx < self.total_covert_bits: #len(encoded_msg_chunks):    
            with self.lock: 
                self.send_packets_within_window(packet_timers, packet_transmission_count, msg_str_list)
                self.timeout_based_retransmissions(packet_transmission_count, packet_timers, msg_str_list)
        # Done sending 
        time.sleep(1) # Sleep for last ACKs to be received
        self.stop_event.set() # Tell ACK daemon to stop
                                
    def send_packet_with_covert(self, message, cov_bit=None):
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


def run_sender(args, **kwargs)->CovertSender:
    # Create a CovertSender object and send the covert message
    # 
    # See get_args() to configure default arguments
    # and pass optional arguments as kwargs.
    # 
    # Required arguments:
    #     overt : set the carrier message
    #     covert : set the covert message
    # Optional arguments:
    #     verbose : print intermediate steps
    #     timeout : timeout in seconds
    #     window_size : sliding window size
    #     udpsize : maximum UDP payload size
    #     trans : maximum number of transmissions

    # WARNING: If the length of the carrier message is too short
    # not all the covert bits will be sent. 
    carrier_msg = args.overt
    covert_msg =  args.covert

    verbose = kwargs.get('verbose', args.verbose)
    timeout = kwargs.get('timeout', args.timeout)
    window = kwargs.get('window_size', args.window)
    udpsize = kwargs.get('max_udp_payload', args.udpsize)
    trans = kwargs.get('max_transmissions', args.trans)

    sender = CovertSender(covert_msg=covert_msg, verbose=verbose, 
                          window_size=window, timeout=timeout, 
                          max_udp_payload=udpsize, max_trans=trans)

    try:
        print("[INFO] Sending message... This might take a while.")
        sender.process_and_send_msg(carrier_msg) 
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        sender.shutdown()
        print("[INFO] Sending completed. Socket closed. Stop receiver process to see the message.")
    
    return sender

def get_args():
    # Create a parser and set default values
    #  return the parsed arguments
    default_carrier_msg = "Hello, this is a long message. " * 200 # WARNING : Carrier must be much longer than covert message for now.
    default_covert_msg =  "Covert." #"This is a covert message."
    default_window_size = 1
    default_udp_payload = 20 # 1458 for a typical 1500 MTU Ethernet network but I use smaller for sending more packets.
    
    default_max_transmissions = 5
    default_timeout = 0.1   # seconds

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="print intermediate steps", action="store_true", default=False)
    parser.add_argument("-c", "--covert", help="covert message to be sent", type=str, default=default_covert_msg, required=False)
    parser.add_argument("-o", "--overt", help="carrier message to be sent", type=str, default=default_carrier_msg, required=False)
    
    parser.add_argument("-r", "--trans", help=f"maximum number of transmissions of the same packet, 1 to send packets only once, default {default_max_transmissions}", type=int, default=default_max_transmissions, required=False)
    parser.add_argument("-t", "--timeout", help=f"timeout in seconds, default {default_timeout}", type=float, default=default_timeout, required=False)

    parser.add_argument("-w", "--window", help=f"sliding window size, default {default_window_size}", type=int, default=default_window_size, required=False)
    parser.add_argument("-s", "--udpsize", help=f"maximum UDP payload size, default {default_udp_payload}. use small value to send more covert bits.", type=int, default=default_udp_payload, required=False) 
    
    args = parser.parse_args()
    return args

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    args = get_args()
    sender = run_sender(args)
    print("Covert Channel capacity: ", sender.get_capacity() , " bits per packet.")