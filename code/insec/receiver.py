
import socket
from scapy.all import IP, UDP, Raw, send, sniff

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
def assert_type(obj, desired_type, note=""):
    assert isinstance(obj, desired_type), f"[ERROR] Expected {note} to be type {desired_type}, got {type(obj)}"

def bits_to_message(bits: str)->str:
    assert_type(bits, str, "bits")
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    return ''.join([chr(int(c, 2)) for c in chars])


class CovertReceiver:

    def __init__(self, port=8888, dest_port=9999):
        self.port = port
        self.dest_port = dest_port
        self.sock = self.create_and_bind_socket(port)

        self.HEADER_LEN = 8 # This must the same with CovertSender's TODO: share this variable across containers
        self.covert_bits = {} # Store in a dictionary because number of bits is unknown

    def create_and_bind_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ( '', port)
        sock.bind(server_address)

        print(f"UDP listener started on port {port}")
        return sock

    def shutdown(self):
        self.sock.close()
        print("[INFO] Socket closed.")

    def get_covert_msg(self):
        if self.covert_bits:
            bit_str = ''.join(self.covert_bits[i] for i in sorted(self.covert_bits))
            return bits_to_message(bit_str)
        return ""
    
    def extract_sequence_number(self, payload)->int:
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
    
    def packet_callback(self, packet):
        if UDP in packet and Raw in packet:
            # Analyze packet
            payload = bytes(packet[Raw])
            seq_number = self.extract_sequence_number(payload)
            if seq_number == -1:
                print(f"[WARNING] Invalid packet received: {payload}")
                return
            print(f"[INFO] Received packet with sequence number {seq_number}: {payload}")
            
            # Extract covert bit and save it
            covert_bit = '1' if packet[UDP].chksum != 0 else '0' # TODO: is 0 = 0?
            self.covert_bits[seq_number] = covert_bit
            print(f"[INFO] Covert bit {covert_bit} saved for sequence number {seq_number}")

            # Send acknowledgment
            sender_ip = packet[IP].src
            #print("dst ip:", packet[IP].dst)
            #print("src ip:", packet[IP].src)
            sent = self.sock.sendto("ACK".encode(), (sender_ip, self.dest_port))
            print(f"[INFO] Sent {sent} bytes (ACK) back to ({sender_ip}, {self.dest_port})")

    def start_udp_listener(self):

        """while True:
                data, addr = self.sock.recvfrom(4096)
                print(f"Received {len(data)} bytes from {addr}")
                print(data.decode())

                # Send acknowledgment
                data = "ACK".encode()
                if data:
                    sent = self.sock.sendto(data, addr)
                    print(f"Sent {sent} bytes (ACK) back to {addr}")"""
        sniff(filter=f"udp and dst port {self.port}", prn=self.packet_callback, store=False)        

    
# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    
    receiver = CovertReceiver(port=8888)
    print("Receiver is running...")
    try:
        receiver.start_udp_listener()
    except KeyboardInterrupt:
        print("Receiver stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        receiver.shutdown()
        print("\nCovert message:", receiver.get_covert_msg())
