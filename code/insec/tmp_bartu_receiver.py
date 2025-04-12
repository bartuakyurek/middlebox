

import socket

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

def create_and_bind_socket(port=8888):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ( '', port)
    sock.bind(server_address)

    print(f"UDP listener started on port {port}")
    return sock

def _udp_loop(sock):
    while True:
            data, addr = sock.recvfrom(4096)
            print(f"Received {len(data)} bytes from {addr}")
            print(data.decode())

            # Send acknowledgment
            data = "ACK".encode()
            if data:
                sent = sock.sendto(data, addr)
                print(f"Sent {sent} bytes (ACK) back to {addr}")

def start_udp_listener():
    try:
        sock = create_and_bind_socket()
        _udp_loop(sock)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    start_udp_listener()