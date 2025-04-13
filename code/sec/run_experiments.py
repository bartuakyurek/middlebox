"""
File to run benchmark experiments campaign for Phase 2. 

WARNING: 
--------
This file measures metrics in terms of 
covert channel sender's *estimated* capacity, which
may or may not be the actual capacity. 

This is because it assumes covert channel has no knowledge about 
whether or not the receiver fully got the message, rather it relies
on its mechanism to ensure the packets are sent correctly.
"""

from sender import run_sender, get_args

# Parameters to test:


window_sizes = [1, 2, 4, 8]
timeout_values = [0.01, 0.1, 0.2, 0.5, 1.0]
max_allowed_retransmissions = [1, 2, 3, 4, 5] # TODO: 1 means do not retransmit, but it's confusing with this name, make the naming consistent

def run_capacity_test(sender):
    print(">>> Running capacity test...")
    print(">> Sender capacity: ", sender.get_capacity())
    return


def run_and_retrieve_statistics(args):
    # Run sender fully then retrieve statistics
    sender = run_sender(args) 
    print(">> Sender capacity: ", sender.get_capacity())
    print("TODO: Add more statistics here...")

def run_experiments(args):
    
    default_args = args
    # Choose the parameters to test
    # Set the args with the chosen parameters
    for w_size in window_sizes:
        args.window_size = w_size
        run_and_retrieve_statistics(args)

    print("Default window was: ", default_args.window_size) 
    print("Current args window size: ", args.window_size)

if __name__ == "__main__":
    
    print(">>> Running the experiments...")
    print("[NOTE] If you want to run a specific experiment, use sender.py instead.")

    default_args = get_args()
    run_experiments(default_args)

