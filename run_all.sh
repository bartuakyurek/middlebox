#!/bin/bash

# A test file to run RTT experiments in Phase 1
# It runs the related scripts in their corresponding containers
# assuming that docker containers are already running
# Output is saved as a .csv file (run plot_rtt.py to visualize it)

SENDER_CONTAINER="sec"
PROCESSOR_CONTAINER="udp-checksum-processor"

DELAYS=(0 1e-6 5e-6 10e-6 20e-6 50e-6 100e-6 200e-6 500e-6 1000e-6 5000e-6 10000e-6)

for DELAY in "${DELAYS[@]}"; do
    echo "Setting delay to $DELAY seconds"

    # 2. Run the processor script inside the Processor container
    echo "Starting processor script inside $PROCESSOR_CONTAINER..."
    docker exec -d $PROCESSOR_CONTAINER python3 main.py -d $DELAY

    # Get PID of the Python process
    PID=$(docker exec $PROCESSOR_CONTAINER pgrep -f "python3 main.py -d $DELAY")

    # 3. Run the ping test script inside the Sender container
    echo "Running ping test script inside $SENDER_CONTAINER..."
    docker exec $SENDER_CONTAINER bash ./ping_test/ping_test.sh $DELAY

    # Terminate the processor to start a new one in the next experiment
    docker exec $PROCESSOR_CONTAINER kill $PID
    echo "------------------------------------"
done 

#echo "Generating RTT plot..."
#docker exec $SENDER_CONTAINER python3 ./ping_test/plot_rtt.py
