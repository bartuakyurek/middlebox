# Reliable UDP Communication
# 

import os
import socket
import argparse

# Define the maximum allowed packet size (adjust based on your network MTU)
MAX_UDP_PAYLOAD_SIZE = 1458 #1458  # For a typical 1500 MTU Ethernet network
# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

def split_message_into_chunks(encoded_message, chunk_size)->list:
    chunks = []
    for i in range(0, len(encoded_message), chunk_size):
        chunk = encoded_message[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

def assign_sequence_number(msg_str, seq_number)->str:
    assert type(msg_str)==str, f"Expected message to be string, got {type(msg_str)}"
    msg_with_sequence = "[" + str(seq_number) + "]" + " " + msg_str
    return msg_with_sequence

class CovertSender:
    def __init__(self, overt_msg, covert_msg, start_immediately=False, verbose=False, timeout=5):
        self.host_ip = self.get_host()
        self.verbose = verbose
        self.timeout = timeout
        
        if start_immediately: self.start_udp_sender(overt_msg)
        elif verbose: print("[INFO] CovertSender created. Call start_udp_sender() to start sending packets.")

    def get_host(self, IP_NAME='INSECURENET_HOST_IP'):
        host = os.getenv(IP_NAME)
        if not host:
            raise ValueError("SECURENET_HOST_IP environment variable is not set.")
        return host

    def _udp_with_ACK(self, sock, message, host, port, timeout, max_resend=10)->int:
        # Returns 0 if message sent successfully
        # -1 if it cannot be delivered in max_resend trials.
        sock.settimeout(timeout)
        trials = 0
        while True:
            trials += 1
            if trials > max_resend: return -1
            try: # Send the message
                
                encoded_msg = message.encode()
                assert len(encoded_msg) < MAX_UDP_PAYLOAD_SIZE, f"Maximum UDP payload is exceeded ({len(encoded_msg)}>{MAX_UDP_PAYLOAD_SIZE}), the message should be splitted into chunks."

                sock.sendto(encoded_msg, (host, port))
                if self.verbose: print(f"Message sent to {host}:{port}")

                # Wait for acknowledgment
                response, server = sock.recvfrom(4096)
                if response.decode() == "ACK":
                    if self.verbose: print("Acknowledgment received. Message delivered successfully.")
                    break
            except socket.timeout:
                print("Timeout occurred. Resending message...")
                
        return 0
            
    def start_udp_sender(self, message, host_ip=None, port=8888):
        if host_ip is None: host_ip = self.host_ip
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
            if self.verbose: print("[INFO] Socket created successfully.")

            encoded_msg = message.encode() 
            encoded_msg_chunks = split_message_into_chunks(encoded_msg, MAX_UDP_PAYLOAD_SIZE-8) # -8 is to be able to add sequence number in the beginning 
            if self.verbose: print(f"[INFO] Message is splitted into {len(encoded_msg_chunks)} chunks.")

            # Send message packets
            for i, msg in enumerate(encoded_msg_chunks):
                msg_str = assign_sequence_number(msg.decode(), i)
                if self.verbose: print(f"[INFO] Appended sequence number to message: {msg_str}")

                while True: # Send a single packet until success (TODO: use threaded)
                    udp_status = self._udp_with_ACK(sock, msg_str, host_ip, port, self.timeout)
                    if udp_status == 0: break # Move on to next message

        except Exception as e:
            print(f"[ERROR] An error occurred: {e}")
        finally:
            sock.close()

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    # TODO: Add timeout parameter, overt msg, covert msg

    overt_msg = "hello, world! this is an overt message. " * 100
    covert_msg = "this is a covert message."

    sender = CovertSender(overt_msg=overt_msg, 
                          covert_msg=covert_msg, 
                          start_immediately=True,
                          verbose=True)
    
    #TODO:
    #overt_messages = ["hello " for _ in range(10)]
    #covert_msg = "this is covert."
    #sender = CovertSender(covert_msg=covert_msg, verbose=True)
    #for msg in overt_messages:
    #    sender.send(msg)
