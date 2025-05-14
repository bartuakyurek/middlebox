
import socket
from scapy.all import IP, UDP, Raw, sniff

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
def assert_type(obj, desired_type, note=""):
    assert isinstance(obj, desired_type), f"[ERROR] Expected {note} to be type {desired_type}, got {type(obj)}"

def bits_to_message(bits: str)->str:
    assert_type(bits, str, "bits")
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    return ''.join([chr(int(c, 2)) for c in chars])


class CovertReceiver:

    def __init__(self, port=8888, dest_port=9999, verbose=False):
        self.verbose = verbose
        self.port = port
        self.dest_port = dest_port
        self.sock = self.create_and_bind_socket(port)
        
        self.state = "overt" # overt, covert

        # Overt state vars
        self.PREAMBLE = "01010011" # 8-bit TODO: make it an environment variable to share with sender.py?
        self.received_preamble = {}

        # Covert state vars
        self.HEADER_LEN = 8 # Number of covert bytes, Must the same with CovertSender's TODO: share this variable across containers
        self.BITS_PER_COVERT_CHAR = 8 

        self.covert_bits_chunk = {} 
        self.covert_chunk_len = 0 # To be determined by <HEADER_LEN>-bit header


    def create_and_bind_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ( '', port)
        sock.bind(server_address)

        if self.verbose: print(f"UDP listener started on port {port}")
        return sock

    def reset_data(self):
        # To reset aggregated chunks in between
        self.covert_bits_chunk = {}
        self.received_preamble = {}
        if self.verbose: print("[DEBUG] Covert and preamble dictionaries have been reset.")

    def shutdown(self):
        self.sock.close()
        if self.verbose: print("[INFO] Socket closed.")

    def _get_covert_len_from_header(self):
        if len(self.covert_bits_chunk.items()) < self.HEADER_LEN:
            return False
        
        # Extract bits in correct order (from index 0 to HEADER_LEN - 1)
        sorted_covert_array = sorted(self.covert_bits_chunk)
        header_bits = [self.covert_bits_chunk[sorted_covert_array[i]] for i in range(self.HEADER_LEN)]
        if self.verbose: print("[DEBUG] Header bits:", header_bits)

        # Join into a binary string and convert to number
        bitstring = "".join(header_bits)
        if self.verbose: print("[DEBUG] Header bitstring:", bitstring)
        self.covert_chunk_len = int(bitstring, 2) * self.BITS_PER_COVERT_CHAR 

        self.covert_chunk_len += self.HEADER_LEN # Don't forget to include header bits
        if self.verbose: print(f"[DEBUG] Parsed covert chunk length: {self.covert_chunk_len}")
        return True

    def get_covert_msg(self):
        # First HEADER_LEN bits represent the actual length of covert message
        if self.covert_bits_chunk:
            bit_str = ''.join(self.covert_bits_chunk[i] for i in sorted(self.covert_bits_chunk))
            
            covert_start = self.HEADER_LEN
            length = int(bit_str[:covert_start], 2) # number of chars in covert message
            covert_end = covert_start + (length * self.BITS_PER_COVERT_CHAR ) # 8 bits per char

            if self.verbose:
                print("Covert message starts at ", covert_start)
                print("Covert message ends at ", covert_end)
                print("bit_str:", bit_str)
                print("length:", length)

            bit_str = bit_str[covert_start:covert_end]
            return bits_to_message(bit_str)
        return ""
    
    def extract_sequence_number_from_payload(self, payload)->int:
        # Sequence number is embedded as '[<seq_number>] '
        # where <seq_number> is an integer
        # Returns -1 if not found
        assert_type(payload, bytes, "payload")

        start = payload.find(b'[')
        end = payload.find(b']', start)
        if start != -1 and end != -1:
            seq_number = payload[start + 1:end]
            return int(seq_number.decode())
        return -1 
    
    def _check_udp_checksum_existence(self, packet):
        # In this implementation,
        # existence of UDP checksum field indicates 1 or 0 covert bit
        covert_bit = '1' if packet[UDP].chksum != 0 else '0' # TODO: is 0 = 0?
        return covert_bit

    def _save_covert_bit(self, packet, seq_number):
        # Extract covert bit and save it
        covert_bit = self._check_udp_checksum_existence(packet)
        self.covert_bits_chunk[seq_number] = covert_bit
        if self.verbose: 
            print(f"[INFO] Covert bit {covert_bit} saved for sequence number {seq_number}")

        return True
    
    def _send_ack(self, packet, seq_number):
        sender_ip = packet[IP].src
        ack = str(seq_number).encode() 
        sent = self.sock.sendto(ack, (sender_ip, self.dest_port))
        if self.verbose: print(f"[INFO] Sent {sent} bytes (ACK) back to ({sender_ip}, {self.dest_port})")
        return True
    
    def _retrieve_seq_number(self, packet):
        payload = bytes(packet[Raw])
        seq_number = self.extract_sequence_number_from_payload(payload)
        if seq_number == -1:
            print(f"[WARNING] Invalid packet received: {payload}")
            return -9999
        if self.verbose: print(f"[INFO] Received packet with sequence number {seq_number}: {payload}")

        return seq_number

    def _check_all_coverts_received(self):
        if self._get_covert_len_from_header():
            if len(self.covert_bits_chunk.items()) >= self.covert_chunk_len:
                if self.verbose:
                    print(f"[DEBUG] Covert bits {len(self.covert_bits_chunk.items())} >= Expected Length {self.covert_chunk_len}")
                print(f"[INFO] Covert of the session: {self.get_covert_msg()}")
                return True
        return False

    def _check_preamble(self, packet, seq_number):
        print("[INFO] Overt state...")
        covert_bit = self._check_udp_checksum_existence(packet)  # Returns "0" or "1"

        self.received_preamble[seq_number] = covert_bit
        if self.verbose:
            print(f"[DEBUG] Covert bit {covert_bit} saved for sequence number {seq_number}")

        # (Naive implementation)
        # Only check if we have at least preamble length bits
        if len(self.received_preamble) >= len(self.PREAMBLE):
            # Sort by sequence number and get the most recent N bits
            recent_seq = sorted(self.received_preamble.keys())[-len(self.PREAMBLE):]
            recent_bits = ''.join(self.received_preamble[seq] for seq in recent_seq)
            if self.verbose:
                print(f"[DEBUG] Recent bits for preamble check: {recent_bits}")

            if recent_bits == self.PREAMBLE:
                if self.verbose:
                    print("[INFO] Preamble matched!")
                return True

        return False

    def _toggle_state(self):
        prev_state = self.state
        if self.state == "overt":
            self.state = "covert"
        elif self.state == "covert":
            self.state = "overt"
        else:
            raise ValueError(f"Unknown state {self.state}")
        
        print("[INFO] State is toggled to {prev_state} -> {self.state}")
        self.reset_data()
        return

    # Main packet receive logic
    def packet_callback(self, packet):
        if UDP in packet and Raw in packet:
            
            seq_number = self._retrieve_seq_number(packet) # Analyze packet

            if self.state == "overt":
                preamble = self._check_preamble(packet, seq_number) # Changes status if covert preamble detected
                
                if preamble:
                    self.state = "covert"
                    self.reset_data() # Clean preamble and previous covert data

            elif self.state == "covert":
                self._save_covert_bit(packet, seq_number)
                received = self._check_all_coverts_received()
                
                if received:
                    self.state = "overt" 
                    self.reset_data()
            else:
                print(f"[WARNING] Unknown state {self.state}")

            self._send_ack(packet, seq_number)

            

    def start_udp_listener(self):
        if self.verbose: print("Receiver is running...")
        sniff(filter=f"udp and dst port {self.port}", prn=self.packet_callback, store=False)        

    
# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="print intermediate steps", action="store_true", default=False)
    args = parser.parse_args()

    receiver = CovertReceiver(port=8888, dest_port=9999, verbose=args.verbose)
    
    try:
        print("Receiver started. Press Ctrl+C to stop and see the received covert message.")
        receiver.start_udp_listener()
    except KeyboardInterrupt:
        print("Receiver stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        receiver.shutdown()
        print(f"\nCovert message: {receiver.get_covert_msg()}")
