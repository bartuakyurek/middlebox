# Reliable UDP Communication
# 

import os
import socket

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

def get_host(IP_NAME='INSECURENET_HOST_IP'):
    host = os.getenv(IP_NAME)
    if not host:
        raise ValueError("SECURENET_HOST_IP environment variable is not set.")
    return host


def _udp_with_ACK_loop(sock, message, host, port, timeout=2):
    sock.settimeout(timeout)
    while True:
        try:
            # Send the message
            sock.sendto(message.encode(), (host, port))
            print(f"Message sent to {host}:{port}")

            # Wait for acknowledgment
            response, server = sock.recvfrom(4096)
            if response.decode() == "ACK":
                print("Acknowledgment received. Message delivered successfully.")
                break
        except socket.timeout:
            print("Timeout occurred. Resending message...")
        except Exception as e:
            print(f"An error occurred: {e}")
            break


def start_udp_sender(host_ip, message="Hello, InSecureNet!", port=8888):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
        _udp_with_ACK_loop(sock, message, host_ip, port)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sock.close()


# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
if __name__ == '__main__':

    msg = "hello, world"

    host_ip = get_host()
    start_udp_sender(host_ip, msg)

