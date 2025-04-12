
import socket
from scapy.all import IP, UDP, Raw, send

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

class CovertReceiver:

    def __init__(self, port=8888):
        self.port = port
        

    def create_and_bind_socket(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ( '', port)
        sock.bind(server_address)

        print(f"UDP listener started on port {port}")
        return sock

    def _udp_loop(self, sock):
        while True:
                data, addr = sock.recvfrom(4096)
                print(f"Received {len(data)} bytes from {addr}")
                print(data.decode())

                # Send acknowledgment
                data = "ACK".encode()
                if data:
                    sent = sock.sendto(data, addr)
                    print(f"Sent {sent} bytes (ACK) back to {addr}")

    def start_udp_listener(self):
        try:
            sock = self.create_and_bind_socket(self.port)
            self._udp_loop(sock)
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            sock.close()
            print("Socket closed.")

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    
    receiver = CovertReceiver(port=8888)
    print("Receiver is running...")
    try:
        receiver.start_udp_listener()
    except KeyboardInterrupt:
        print("Receiver stopped.")