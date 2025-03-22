#!/bin/bash

# Check if the delay value is provided as an argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <delay_value>"
    exit 1
fi

OUTPUT_FILE="./ping_test/ping_results.csv"

DELAY="$1"  # Get the delay value from the command-line argument
host=insec  # Target IP or hostname
num_pings=100      # Number of pings per run
num_runs=30        # Number of repetitions
interval=0.1      # Ping sending interval between packets

# Initialize CSV file if it doesn't exist already
if ! [ -f "$OUTPUT_FILE" ]; then
    echo "Delay,Trial,Min RTT,Avg RTT,Max RTT,Stddev RTT" > "$OUTPUT_FILE"
fi

echo "Running $num_runs ping tests with $num_pings pings each (Delay: $DELAY)..."

# Run ping tests
for (( run=1; run<=$num_runs; run++ ))
do
    echo "Running test $run / $num_runs..."
    
    # Run ping and extract RTT statistics (min, avg, max, stddev)
    PING_OUTPUT=$(ping -c "$num_pings" -i "$interval" $host | tail -1 | awk -F'/' '{print $4","$5","$6","$7}')

    # Store results in CSV
    echo "$DELAY,$run,$PING_OUTPUT" >> "$OUTPUT_FILE"
    
done

echo "Results saved to $OUTPUT_FILE"
