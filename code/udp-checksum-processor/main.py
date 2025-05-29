import os
import random
import asyncio
import argparse 

from scapy.all import Ether, IP, UDP, Raw
from nats.aio.client import Client as NATS

class UDP_Checksum_Processor:
    def __init__(self, nc, topic_dict, mean_delay=1e-2, mitigate=False):
        self.nc = nc
        self.topic_dict = topic_dict
        self.mean_delay = mean_delay
        self.mitigate_bool = mitigate

    async def subscribe(self):
        # Subscribe to inpktsec and inpktinsec topics
        subscriptions = [
            self.nc.subscribe(topic, cb=self.message_handler)
            for topic in self.topic_dict.keys()
        ]
        await asyncio.gather(*subscriptions)

    async def publish(self, subject, data):
        # Publish the received message to outpktsec and outpktinsec
        await self.nc.publish(self.topic_dict[subject], data)

        # Sends a PING and wait for a PONG from the server, up to the given timeout.
        # This gives guarantee that the server has processed above message.
        await self.nc.flush(timeout=1)
       
    async def mitigate(self, packet):
        # Mitigation strategy: Enforce checksum 
        # (i.e. always correct it, another strategy would be to always drop it, or corrupt)
    
        if UDP in packet:
            ip_layer = packet[IP]
            udp_layer = packet[UDP]
            original_checksum = udp_layer.chksum

            # Recompute checksum 
            udp_layer.chksum = None
            rebuilt_packet = Ether(bytes(packet))  
            new_checksum = rebuilt_packet[UDP].chksum
            print(f"[DEBUG] Original checksum: {original_checksum}")
            print(f"[DEBUG] Recomputed checksum: {new_checksum}")

            udp_layer.chksum = new_checksum
            packet = Ether(bytes(packet))
        return packet

    async def message_handler(self, msg):
        subject = msg.subject
        data = msg.data 
        
        packet = Ether(data)
        print("[DEBUG] Original Packet:")
        print(packet.show())

        if self.mitigate_bool:
            modified_packet = await self.mitigate(packet)
        else:
            modified_packet = packet

        delay = random.uniform(0, self.mean_delay * 2)
        await asyncio.sleep(delay)
        await self.publish(subject, bytes(modified_packet)) 


async def run(mean_delay=0, mitigate=False):
    nc = NATS()

    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222")
    await nc.connect(nats_url)

    topic_dict = {
                    "inpktsec" : "outpktinsec",
                    "inpktinsec" : "outpktsec"
    }

    processor = UDP_Checksum_Processor(nc, topic_dict, mean_delay, mitigate)
    await processor.subscribe()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await nc.close()



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-d', '--delay', type=float, default=1e-2, help='Specify the average delay to be added before sending packets in seconds.')
    parser.add_argument('-m', '--mitigate', help='Run covert channel mitigation strategy. Default False.', action="store_true", default=False)

    args = parser.parse_args()
    
    print("Running processor with delay ", args.delay)
    asyncio.run(run(args.delay, args.mitigate))

 