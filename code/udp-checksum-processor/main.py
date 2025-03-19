import os
import random
import asyncio

import nats
from scapy.all import Ether
from nats.aio.client import Client as NATS

class UDP_Checksum_Processor:
    def __init__(self, nc, topic_dict):
        self.nc = nc
        self.topic_dict = topic_dict

        self.delay_mean = 10e-6

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
       
    async def message_handler(self, msg):
        subject = msg.subject
        data = msg.data 
        
        packet = Ether(data)
        print(packet.show())

        delay = random.expovariate(1. / self.delay_mean)
        await asyncio.sleep(delay)
        
        await self.publish(subject, msg.data)


async def run():
    nc = NATS()

    nats_url = os.getenv("NATS_SURVEYOR_SERVERS", "nats://nats:4222")
    await nc.connect(nats_url)

    topic_dict = {
                    "inpktsec" : "outpktinsec",
                    "inpktinsec" : "outpktsec"
    }

    processor = UDP_Checksum_Processor(nc, topic_dict)
    await processor.subscribe()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Disconnecting...")
        await nc.close()



if __name__ == '__main__':
    asyncio.run(run())

 