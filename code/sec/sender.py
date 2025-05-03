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
import random
import socket
import argparse
import threading
from threading import Thread
from scapy.all import IP, UDP, Raw, send

from utils import assert_type
from utils import random_string
from utils import message_to_bits
from utils import assign_sequence_number
from utils import split_message_into_chunks
from utils import save_session_csv

class CovertSender:
    def __init__(self, verbose=False, 
                 window_size=5, timeout=5, max_udp_payload=1458, max_trans=3, 
                 port=9999, dport=8888):        
        
        self.HEADER_LEN = 8       
        self.covert_bits_str = "" # Covert bits to be sent
        self.session_covert_bits_len = 0

        self.verbose = verbose
        self.timeout = timeout
        self.max_payload = max_udp_payload
        self.max_trans = max_trans
        
        self.port = port
        self.dport = dport
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

        if verbose: print("[DEBUG] CovertSender created. Call send() to start sending packets.")

    def get_host(self, IP_NAME='INSECURENET_HOST_IP'):
        host = os.getenv(IP_NAME)
        if not host:
            raise ValueError("SECURENET_HOST_IP environment variable is not set.")
        return host
    
    def create_udp_socket(self, ip, port):
         
         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
         sock.bind((ip, port))
         if self.verbose: print("[DEBUG] Socket created successfully.")
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
            print(f"[DEBUG] Capacity: {capacity:.2%} ({n_success}/{n_total})")
            print(f"[WARNING] This capacity assumes the packet wasn't delivered if ACK wasn't received within the timeout but in fact,\n \
                    ACK may come later than the timeout, so the capacity may be higher than this value. Check the receiver's covert message to verify.")

        return capacity

    def get_ACK(self, sleep_time=0.01):
        # Listen for ACKs until all the covert bits are sent
        # WARNING: This assumes the rest of the message is not ACKed
        # so some packets after the covert bits may be lost.

        # Wait until every packet is either ACKed or marked as dropped
        while len(self.received_acks) < self.session_covert_bits_len and not self.stop_event.is_set():
            data, addr = self.ack_sock.recvfrom(4096)
            seq_num = int(data.decode())
            
            # Save the ACK timestamp with sequence number as key
            with self.lock: # To avoid race conditions
                if seq_num not in self.received_acks:
                    if self.verbose: print(f"[ACK] ({data}) received from {addr}. Sequence number: {seq_num}")
                    self.received_acks[seq_num] = time.time() # TODO: I assumed this could be useful for packet stats, but is it used?
                else:
                     if self.received_acks[seq_num] == -1:
                        self.received_acks[seq_num] = time.time() # Mark dropped packet it as received
                #    if self.verbose: print(f"[ACK] Duplicate ACK received for sequence number {seq_num}. Ignoring it.")

                while self.window_start in self.received_acks: 
                    self.window_start += 1 # Slide the window
                    if self.verbose: print(f"[SLIDE] Window is slided to {self.window_start}.")

            time.sleep(sleep_time) # Sleep to let the other threads acquire the lock more easily
        #self.stop_event.set() # Tell the sender to stop sending packets

    def timeout_based_retransmissions(self, packet_transmission_count, packet_timers, msg_str_list):
        for idx in range(self.window_start, self.cur_pkt_idx):
            if idx not in self.received_acks:
                if time.time() - packet_timers[idx] > self.timeout:
                    
                    if packet_transmission_count[idx] >= self.max_trans:
                        if self.verbose: print(f"[TIMEOUT] Maximum transmission limit reached for packet {idx}. Dropping it.")
                        assert not idx in self.received_acks, f"[ERROR] Packet {idx} should not be in received_acks."
                        self.received_acks[idx] = -1 # Mark it as missing 
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
        if self.verbose: print("[DEBUG] ACK thread started.")

    
    def send_packets_within_window(self, packet_timers, packet_transmission_count, msg_str_list):
        threads = []

        while self.cur_pkt_idx < self.window_start + self.window_size:
            if self.verbose: print("Current bit index:", self.cur_pkt_idx)

            if self.cur_pkt_idx >= len(msg_str_list):
                if self.verbose: print("[INFO] No more overt packets to send.")
                if self.cur_pkt_idx < self.session_covert_bits_len:
                    if self.verbose: print("[WARNING] Not all covert bits can be sent. Out of carrier message.")
                break

            msg_str = msg_str_list[self.cur_pkt_idx]
            bit = None if self.cur_pkt_idx >= self.session_covert_bits_len else self.covert_bits_str[self.cur_pkt_idx]
            
            # Prepare thread to send this packet
            t = Thread(target=self._send_and_track, args=(self.cur_pkt_idx, msg_str, bit, packet_timers, packet_transmission_count))
            threads.append(t)
            t.start()

            self.cur_pkt_idx += 1

        for t in threads:
            t.join()  # Optional: Wait for all threads to finish

    def _send_and_track(self, idx, msg_str, bit, packet_timers, packet_transmission_count):
        self.send_packet_with_covert(msg_str, bit)
        self.total_packets_sent += 1
        packet_timers[idx] = time.time()
        packet_transmission_count[idx] = 1
        if self.verbose:
            print("[DEBUG] Total packets sent:", self.total_packets_sent,
                "[DEBUG] total received ACKs:", self.count_successful_transmissions())

    def process_and_send_msg(self, message, covert_msg="", wait_time=1):
        # Sends a legitimate message 
        # The given message is split into chunks of size max_payload
        # and sent over UDP with the covert bits embedded in the checksum field.

        # top of process_and_send_msg
        self.cur_pkt_idx = 0
        self.window_start = 0
        self.received_acks.clear()

        encoded_msg = message.encode() 
        encoded_msg_chunks = split_message_into_chunks(encoded_msg, self.max_payload-8) # -8 is to be able to add sequence number in the beginning 
        if self.verbose: print(f"[DEBUG] Message is splitted into {len(encoded_msg_chunks)} packets.")
        assert len(encoded_msg_chunks) >= self.session_covert_bits_len, f"[ERROR] Number of packets are not enough for the number of covert bits {len(encoded_msg_chunks)} < {self.session_covert_bits_len}, please increase the carrier message length."

        # Add sequence number to each chunk
        msg_str_list = [assign_sequence_number(chunk.decode(), i) for i, chunk in enumerate(encoded_msg_chunks)]
        
        self.covert_bits_str = self._get_covert_bitstream(covert_msg, self.HEADER_LEN)
        
        self.session_covert_bits_len = len(self.covert_bits_str)
        if self.verbose: print(f"[DEBUG] Covert bits string: {self.covert_bits_str}")
        if self.verbose: print(f"[DEBUG] There are {self.session_covert_bits_len} bits to be sent covertly.")

        # Create a daemon to receive ACKs continuously
        self.stop_event.clear()
        self.create_ack_thread()

        # Send message packets
        # WARNING: This assumes the rest of the message after all the
        # covert bits are sent, can be dropped. (See get_ACK() Warning)
        packet_timers, packet_transmission_count = {}, {}
        while self.cur_pkt_idx < self.session_covert_bits_len: #len(encoded_msg_chunks):    
            with self.lock: 
                self.send_packets_within_window(packet_timers, packet_transmission_count, msg_str_list)
                self.timeout_based_retransmissions(packet_transmission_count, packet_timers, msg_str_list)
        # Done sending 
        if self.verbose: print(f"[DEBUG] All packets sent. Waiting extra {wait_time} seconds for ACKs...")
        time.sleep(wait_time) # Sleep for last ACKs to be received
    
        self.stop_event.set() # Tell ACK daemon to stop
                                
    def send_packet_with_covert(self, message, cov_bit=None):
        # Send packet using UDP with ACK
        # Returns 0 if message sent successfully
        # -1 if it cannot be delivered in max_resend trials.
        ip = IP(dst=self.recv_ip)
        udp = UDP(dport=self.dport, sport=self.port)
        # Covert bit as checksum field existence
        if cov_bit == '1' or cov_bit == None: # None when no covrt bit is sent
            udp.chksum = None  # Let OS/scapy compute it
        elif cov_bit == '0':
            udp.chksum = 0  # Explicitly remove checksum
        else:
            raise ValueError(f"Invalid covert bit. Must be '0' or '1'. Got: {cov_bit}")
        
        pkt = ip/udp/Raw(load=message)
        send(pkt, verbose=False)
        if self.verbose: print(f"[DEBUG] Message sent to {self.recv_ip}:{self.dport}")
            
    def _get_covert_bitstream(self, covert_msg_str, header_len)->str:
        # Given a covert message string and number of bits 
        # in the header, return string of bits to be sent covertly
        # header_len : number of bits in header, 
        #              where header represents the length of covert message string
        #              should be at least N bits where 2^N >= len(bits of covert msg) 
        assert_type(covert_msg_str, str, "covert message")
        assert_type(header_len, int, "header length")
        covert_bytes = covert_msg_str.encode()
        covert_len = len(covert_bytes)

        covert_len_bits_str = bin(covert_len)[2:] # number of bits needed to represent covert msg length
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

    sender = CovertSender(verbose=verbose, 
                          window_size=window, timeout=timeout, 
                          max_udp_payload=udpsize, max_trans=trans)

    try:

        prob_cov = args.probcov # Probability of sending covert message
        
        if random.random() < prob_cov:
            mode = "covert"
            print(f"[INFO] Sending covert message...")
            sender.process_and_send_msg(carrier_msg, covert_msg=covert_msg, wait_time=args.senderwait) 
        else:
            mode = "overt"
            num_dummy_chars = random.randint(1,10) 
            dummy_covert = random_string(num_dummy_chars) 

            print(f"[INFO] Sending overt-only message with dummy covert: {dummy_covert}")
            sender.process_and_send_msg(carrier_msg, dummy_covert, wait_time=args.senderwait) 
            

        save_session_csv(
                        sender,
                        session_id=i,
                        covert_msg=covert_msg,
                        overt_msg=carrier_msg,
                        mode=mode  # "covert" or "overt"
                        )

    except Exception as e:
        print(f"[ERROR] An error occurred on the sender side: {e}")
    finally:
        sender.shutdown()
        print("[INFO] Sending completed. Socket closed. Stop receiver process to see the message.")
    
    return sender

def get_args():
    # Create a parser and set default values
    #  return the parsed arguments
    # WARNING: Content of carrier message is assumed to be unimportant, i.e.
    # this sender will send packets until all covert bits are sent, ignoring
    # remaining carrier message packets after that point.
    default_carrier_msg = "Hello, this is a long message. " * 200 # WARNING : Carrier must be much longer than covert message for now.
    default_covert_msg =  "Covert."*3 #"This is a covert message."
    default_udp_payload = 20 # 1458 for a typical 1500 MTU Ethernet network but I use smaller for sending more packets.
    default_sender_wait = 1 # seconds before stopping ACK daemon

    default_window_size = 5
    default_max_transmissions = 1
    default_timeout = 0.5   # seconds
    default_covert_prob = 1

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="print intermediate steps", action="store_true", default=False)
    parser.add_argument("-c", "--covert", help="covert message to be sent", type=str, default=default_covert_msg, required=False)
    parser.add_argument("-o", "--overt", help="carrier message to be sent", type=str, default=default_carrier_msg, required=False)
    parser.add_argument("-s", "--udpsize", help=f"maximum UDP payload size, default {default_udp_payload}. use small value to send more covert bits.", type=int, default=default_udp_payload, required=False) 
    parser.add_argument("-sw", "--senderwait", help=f"sleep time before closing the communication, default {default_sender_wait}", type=int, default=default_sender_wait, required=False)

    parser.add_argument("-w", "--window", help=f"sliding window size, default {default_window_size}", type=int, default=default_window_size, required=False)
    parser.add_argument("-r", "--trans", help=f"maximum number of transmissions of the same packet, 1 to send packets only once, default {default_max_transmissions}", type=int, default=default_max_transmissions, required=False)
    parser.add_argument("-t", "--timeout", help=f"timeout in seconds, default {default_timeout}", type=float, default=default_timeout, required=False)
    parser.add_argument("-p", "--probcov", help=f"probability of sending covert message between [0,1], default {default_covert_prob}", type=float, default=default_covert_prob, required=False)

    args = parser.parse_args()
    assert args.probcov >= 0 and args.probcov <= 1, f"Expected probability to be in range [0,1]. Got {args.probcov}."
    return args

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    import time

    args = get_args()

    NUM_RUNS = 1
    for i in range(NUM_RUNS):
        print("-"*50)
        start = time.time()
        sender = run_sender(args)
        end = time.time()

        elapsed_secs = end - start
        print(f"Sending took {elapsed_secs:.2f} seconds.")
        print(f"Sent {sender.session_covert_bits_len} covert bits.")
        print("Covert Channel capacity: ")

        bps_capacity = sender.session_covert_bits_len / elapsed_secs 
        print(f"\t {bps_capacity:.2f} covert bits per second.")
        print(f"\t {sender.get_capacity():.2f} covert bits per packet.")
