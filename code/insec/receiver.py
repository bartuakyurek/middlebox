
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

    def __init__(self, port=8888, dest_port=8888):
        self.port = port
        self.dest_port = dest_port
        self.sock = self.create_and_bind_socket(port)

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
    
    def packet_callback(self, packet):
        if UDP in packet and Raw in packet:
            # Analyze packet
            payload = bytes(packet[Raw])
            seq_number = None
            print(f"Received packet with sequence number {seq_number}: {payload}")
            
            # Send acknowledgment
            sender_ip = packet[IP].src
            sent = self.sock.sendto("ACK".encode(), (sender_ip, self.dest_port))
            print(f"Sent {sent} bytes (ACK) back to {sender_ip}")

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
        sniff(filter=f"udp and port {self.port}", prn=self.packet_callback, store=False)        

    
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
