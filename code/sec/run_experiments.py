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
import numpy as np
import scipy.stats as st
import matplotlib.pyplot as plt


from sender import run_sender, get_args, assert_type # TODO: move assert to utils

# Test for a small message for now
CARRIER_MESSAGE = "Hello, this is a test message. " * 100
COVERT_MESSAGE = "COW" * 1

# Parameters to test
window_sizes = [1, 2, 4, 8]
timeout_values = [0.1, 0.5, 1.0, 5.0]
max_allowed_retransmissions = [1, 2, 3, 4, 5] # TODO: 1 means do not retransmit, but it's confusing with this name, make the naming consistent


def run_and_retrieve_statistics(args)-> dict:
    # Run sender fully then retrieve statistics    
    sender = run_sender(args) 
    stats = {}
    stats['capacity'] = sender.get_capacity() 
    
    return stats

def change_one_arg_and_run(args, arg_name, arg_values, exclude_args=['verbose', 'overt', 'covert', 'udpsize']):
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
    #        out_dict = change_one_arg_and_run(args, 'window_size', window_sizes)
    #        print("Window size statistics: ", out_dict['stats'])
    #        print("Window size fixed arguments: ", out_dict['fixed_args'])
    args_copy = copy.deepcopy(args)
    stats = {}
    for arg_value in arg_values:
        setattr(args_copy, arg_name, arg_value)
        print(f"[....] Running with {arg_name} = {arg_value}")
        stat = run_and_retrieve_statistics(args_copy)

        stats[arg_value] = stat

    print(f"Statistics for {arg_name}: ", stats)
    print("Where fixed arguments are:")
    fixed_args = {}
    for name in args_copy.__dict__:
        if name != arg_name and name not in exclude_args:
            print(f"{name}: {args_copy.__dict__[name]}")
            fixed_args[name] = args_copy.__dict__[name]

    out_dict = {}
    out_dict['stats'] = stats
    out_dict['fixed_args'] = fixed_args
    return out_dict

def plot_statistics(output_dict, arg_name, metric_name):
    # Plot the statistics
    # Parameters:
    # ---------------------------------------------------------------
    # See change_one_arg_and_run for output_dict variable.
    # output_dict['stats']: the statistics to plot
    # output_dict['fixed_args']: the fixed arguments of the experiment
    # arg_name: name of the free parameter in the experiment
    # --------------------------------------------------------------
    stats_dict = output_dict['stats'] 
    fixed_args_dict = output_dict['fixed_args']
    print("Statistics: ", stats_dict)
    assert_type(stats_dict, dict, "stats")
    assert_type(arg_name, str, "arg_name")
    assert_type(metric_name, str, "metric_name")

    x_values = list(stats_dict.keys())
    y_values = [stats_dict[x][metric_name] for x in x_values]
    label = ', '.join(f'{k}={v}' for k, v in fixed_args_dict.items())

    plt.figure()
    plt.plot(x_values, y_values, label=label,
             color='blue', linestyle='-', 
             marker='o', markerfacecolor='red', markeredgecolor='red')
    plt.xlabel(arg_name)
    plt.ylabel(f'{metric_name}')
    plt.title(f'{metric_name} vs {arg_name}')
    plt.grid(True)
    plt.legend()

    figure_path = f'./{arg_name}_vs_{metric_name}.png'
    plt.savefig(figure_path)
    print(f"Saved figure to {figure_path}")

def run_experiments(args):
    
    args.overt = CARRIER_MESSAGE # Override them to test for small messages
    args.covert = COVERT_MESSAGE

    w_stats = change_one_arg_and_run(args, 'window_size', window_sizes)
    t_stats = change_one_arg_and_run(args, 'timeout', timeout_values)
    r_stats = change_one_arg_and_run(args, 'max_retrans', max_allowed_retransmissions)
    
    available_metrics = w_stats['stats'][1].keys() # WARNING Assumes same keys used in other stats as well 
    for metric_name in available_metrics:
        plot_statistics(w_stats, 'window_size', metric_name)
        plot_statistics(t_stats, 'timeout', metric_name)
        plot_statistics(r_stats, 'max_retrans', metric_name)

    print("Window size statistics: ", w_stats)
    print("Timeout statistics: ", t_stats)
    print("Max retransmissions statistics: ", r_stats)

if __name__ == "__main__":
    
    print(">>> Running the experiments...")
    print("[NOTE] If you want to run a specific experiment, use sender.py instead.")

    default_args = get_args()
    run_experiments(default_args)

