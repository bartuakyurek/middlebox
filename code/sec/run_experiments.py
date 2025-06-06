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
import time
import numpy as np
import scipy
import matplotlib.pyplot as plt


from sender import run_sender, get_args, assert_type # TODO: move assert to utils

def get_metric_units(metric_name):
    if metric_name == 'capacity':
        return 'bits/packet'
    elif metric_name == 'bps_capacity':
        return 'bits/second'
    elif metric_name == 'timeout':
        return 'sec'
    else:
        return ''

def get_confidence_interval(values, confidence=0.95)-> tuple:
    # Compute confidence interval given a list of values
    # where values correspond the different measurements
    # retrieved by running experiments with the same configuration.
    a = np.array(values)
    mean = np.mean(a)
    stderr = scipy.stats.sem(a)  # Standard error of the mean
    margin = stderr * scipy.stats.t.ppf((1 + confidence) / 2., len(a) - 1)
    return mean, margin

def run_and_retrieve_statistics(args, num_trials)-> dict:
    # Run sender fully then retrieve statistics    
    
    stats = {}
    stats['capacity'] = []
    stats['bps_capacity'] = []
    for i in range(num_trials):

        start = time.time()
        sender = run_sender(args) 
        end = time.time()
        elapsed_secs = end - start

        print(f"Sending took {elapsed_secs:.2f} seconds.")
        print(f"Sent {sender.session_covert_bits_len} covert bits.")
        print("Covert Channel capacity: ")
        cap = sender.get_capacity() 
        bps_cap = sender.session_covert_bits_len / elapsed_secs 
        print(f"\t {bps_cap:.2f} covert bits per second.")
        print(f"\t {cap:.2f} covert bits per packet.")
        
        stats['capacity'].append(cap)
        stats['bps_capacity'].append(bps_cap)
        print(f"[INFO] Trial {i+1}/{num_trials} - Capacity: {cap}")
    return stats
    #capacity = sender.get_capacity()
    #return capacity

def change_one_arg_and_run(args, arg_name, arg_values, num_trials, 
                           exclude_args=['verbose', 'overt', 'covert', 'udpsize', 'probcov']):
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
    # ------------------------------------------------------------

    args_copy = copy.deepcopy(args) 
    stats = {}
    for arg_value in arg_values:
        setattr(args_copy, arg_name, arg_value)
        print(f"[....] Running with {arg_name} = {arg_value}")
        stats_of_single_parameter = run_and_retrieve_statistics(args_copy, num_trials)
        stats[arg_value] = stats_of_single_parameter
        
    fixed_args = {}
    for name in args_copy.__dict__:
        if str(name) != str(arg_name) and (name not in exclude_args):
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
    
    assert_type(stats_dict, dict, "stats")
    assert_type(arg_name, str, "arg_name")
    assert_type(metric_name, str, "metric_name")

    # Extract the metric values from the statistics dictionary
    # and sort them according to the x_values
    measurements_list, x = extract_metric_from_dict(stats_dict, metric_name)
    y, yerr = [], []
    for measurements in measurements_list:
        assert_type(measurements, list, "measurements")
        mean_y, margin_y = get_confidence_interval(measurements)
        y.append(mean_y)
        yerr.append(margin_y)
    
    label = ', '.join(f'{k}={v}' for k, v in fixed_args_dict.items())

    plt.figure()
    plt.plot(x, y, label=label,
             color='blue', linestyle='-', 
             marker='o', markerfacecolor='red', markeredgecolor='red')
    
    # Plot the shaded confidence interval
    ci = np.array(yerr)
    x, y = np.array(x), np.array(y)
    plt.fill_between(x, y - ci, y + ci, color='blue', alpha=0.2, label=f'± CI ({len(measurements)} trials)')

    plt.xlabel(f'{arg_name}') # ({get_metric_units(arg_name)})')
    plt.ylabel(f'{metric_name}') # ({get_metric_units(metric_name)})')
    plt.title(f'{metric_name} vs {arg_name}')
    plt.grid(True)
    plt.legend()

    figure_path = f'./{arg_name}_vs_{metric_name}.png'
    plt.savefig(figure_path)
    print(f"Saved figure to {figure_path}")

def extract_metric_from_dict(stats_dict, metric_name)->tuple:
    # Extract the metric from the statistics dictionary
    # Parameters:
    # ---------------------------------------------------------------
    # stats_dict: the statistics dictionary from output_dict['stats']
    # which holds the statistics for each value of the free parameter
    #
    # metric_name: the name of the metric to extract, e.g. 'capacity'
    # --------------------------------------------------------------
    # Returns tuple of lists:
    # metric_values: extracted metrics
    # sorted_keys: values of the parameter with the same order as metric_values
    # --------------------------------------------------------------
    assert_type(stats_dict, dict, "stats_dict")
    assert_type(metric_name, str, "metric_name")

    metric_values = []
    sorted_keys = sorted(stats_dict.keys())
    for key in sorted_keys:
        metric_value = stats_dict[key].get(metric_name)
        if metric_value is not None:
            metric_values.append(metric_value)
        else:
            raise ValueError(f"Metric {metric_name} not found for key {key}.")

    return metric_values, sorted_keys

def run_single_param_experiment(args, arg_name, arg_values, num_trials):
    arg_stats = change_one_arg_and_run(args, arg_name, arg_values, num_trials=num_trials)
    
    a_key = [key for key in arg_stats['stats'].keys()][0]
    available_metrics = arg_stats['stats'][a_key].keys() # WARNING Assumes same keys used in other stats as well 
    for metric_name in available_metrics:
        plot_statistics(arg_stats, arg_name, metric_name)

    print(f"{arg_name} statistics: ", arg_stats)

def run_experiments(args):

    # Parameters of experimental campaign
    # ------------------------------------------------------------
    num_trials=5 # Number of runs for each identical configuration

    # Test for a small message for now (WARNING: Set carrier length at least x16 more than covert message)
    CARRIER_MESSAGE = "Hello, this is a test message. " * 600
    COVERT_MESSAGE = "Covert." * 10

    # Parameters to test
    args.probcov = 1. # Force only covert if set to 1.0
    window_sizes = [1, 2, 4, 8, 16, 32]
    timeout_values = [0.01, 0.2, 1.0, 5.0]
    max_allowed_transmissions = [1, 2, 3, 4, 5] 
    # -------------------------------------------------------------
    args.overt = CARRIER_MESSAGE # Override them to test for small messages
    args.covert = COVERT_MESSAGE
    run_single_param_experiment(args, 'window', window_sizes, num_trials)
    run_single_param_experiment(args, 'timeout', timeout_values, num_trials)
    run_single_param_experiment(args, 'trans', max_allowed_transmissions, num_trials)

if __name__ == "__main__":
    
    print(">>> Running the experiments...")
    print("[NOTE] If you want to run a specific experiment, use sender.py instead.")

    default_args = get_args()
    
    run_experiments(default_args)

