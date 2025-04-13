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
import copy
from sender import run_sender, get_args

# Test for a small message for now
CARRIER_MESSAGE = "Hello, this is a test message. " * 100
COVERT_MESSAGE = "Covert." * 1

# Parameters to test
window_sizes = [1, 2, 4, 8]
timeout_values = [0.01, 0.1, 0.2, 0.5, 1.0]
max_allowed_retransmissions = [1, 2, 3, 4, 5] # TODO: 1 means do not retransmit, but it's confusing with this name, make the naming consistent


def run_and_retrieve_statistics(args)-> dict:
    # Run sender fully then retrieve statistics    
    sender = run_sender(args) 
    stats = {}
    stats['capacity'] = sender.get_capacity() 
    #rint("TODO: Add more statistics here...")
    return stats

def change_one_arg_and_run(args, arg_name, arg_values, exclude_args=['verbose', 'overt', 'covert']):
    # Change one argument and run the sender
    # Parameters:
    # ------------------------------------------------------------
    # args: arguments of sender (see sender.py)
    # arg_name: name of the argument to change
    # arg_values: values to test for the argument
    # exclude_args: arguments to exclude from saved statistic
    #                i.e. other arguments will be saved as fixed 
    #                experiment parameters
    # ------------------------------------------------------------
    # Example use: 
    #        from sender import get_args
    #        args = get_args() # This has argument window_size
    #        window_sizes = [1, 2, 4, 8]
    #        change_one_arg_and_run(args, 'window_size', window_sizes)
    args_copy = copy.deepcopy(args)
    stats = {}
    for arg_value in arg_values:
        setattr(args_copy, arg_name, arg_value)
        print(f"[####] Running with {arg_name} = {arg_value}")
        stat = run_and_retrieve_statistics(args_copy)

        stats[arg_value] = stat

    print(f"Statistics for {arg_name}: ", stats)
    print("Where fixed arguments are:")
    for name in args_copy.__dict__:
        if name != arg_name and name not in exclude_args:
            print(f"{name}: {args_copy.__dict__[name]}")

def run_experiments(args):
    
    args.overt = CARRIER_MESSAGE # Override them to test for small messages
    args.covert = COVERT_MESSAGE

    change_one_arg_and_run(args, 'window_size', window_sizes)
    # Choose the parameters to test
    # Set the args with the chosen parameters
    #w_stats = {}
    #w_stats['timeout'] = args.timeout
    #w_stats['max_retrans'] = args.max_retrans
    #for i, w_size in enumerate(window_sizes):
    #    print(f"\n>> Running experiment {i+1}/{len(window_sizes)}with window size: {w_size}")
    #    args.window_size = w_size
    #    stat = run_and_retrieve_statistics(args)
    #    w_stats[w_size] = stat
    #print("Window size capacity statistics: ", w_stats)

if __name__ == "__main__":
    
    print(">>> Running the experiments...")
    print("[NOTE] If you want to run a specific experiment, use sender.py instead.")

    default_args = get_args()
    run_experiments(default_args)

