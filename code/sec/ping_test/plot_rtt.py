import numpy as np
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt

# Load results
df = pd.read_csv("ping_results.csv")

# Compute confidence intervals per delay
confidence = 0.95
summary = df.groupby("Delay")["Avg RTT"].agg(["mean", "std", "count"])
summary["CI"] = summary.apply(lambda x: st.t.interval(confidence, x["count"]-1, loc=x["mean"], scale=x["std"]/x["count"]**0.5), axis=1)

print(summary)


delay_values = summary.index
conf_intervals = summary["CI"].values
mean_rtts = summary["mean"].values

is_sorted = lambda a: np.all(a[:-1] <= a[1:])
assert is_sorted(delay_values), "Expected the delay values to be sorted in ascending order."

lower_bound = [ci[0] for ci in conf_intervals]
upper_bound = [ci[1] for ci in conf_intervals]

plt.figure(figsize=(10, 6))
plt.plot(delay_values, mean_rtts, marker='o', linestyle='-', color='b', label='Mean RTT with confidence intervals.')
plt.fill_between(delay_values, lower_bound, upper_bound, color='b', alpha=0.4, label='Confidence Interval')

plt.title('Average RTT vs. Processor Delay with 95% Confidence Intervals')
plt.xlabel('Delay (s)')
plt.ylabel('Average RTT (ms)')
plt.grid(True)
plt.legend()
plt.show()

"""
import glob
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt


# Read the output files for average RTT (average_rtt_*.txt)
average_root_name = "average_rtt_"

delay_values = []
rtt_data = {}  # Dictionary to store RTT values for each delay
path = "./results/"+average_root_name+"*.txt"
for filename in glob.glob(path):
    with open(filename, 'r') as f:

        # Extract delay value from file name
        # Delay values are appended at the end of the file name (average_rtt_<delay>.txt)
        delay_value = filename.split('_')[-1].split('.')[0] # "/results/average_rtt_<delay>.txt" -> "<delay>.txt" -> <delay>
        delay_value = float(delay_value)
        delay_values.append(delay_value)

        rtt_values = []
        # Read average rtt runs for that delay
        for line in f:
            rtt_avg = float(line.split()[-2])
            rtt_values.append(rtt_avg)

        rtt_data[str(delay_value)] = np.array(rtt_values)

# Plot the average RTT with confidance intervals
delay_values = np.sort(delay_values)
print("Found delay values (sorted): ", delay_values)

# Compute statistics
mean_rtts = []
conf_intervals = []

for delay in delay_values:
    rtt_values = rtt_data[str(delay)]
    N = len(rtt_values)
    mean_rtt = np.mean(rtt_values)
    std_rtt = np.std(rtt_values, ddof=1)  # Sample standard deviation
    SE = std_rtt / np.sqrt(N)  # Standard error
    t_score = stats.t.ppf(0.975, df=N-1)  # 95% CI from t-distribution
    CI = t_score * SE  # Confidence interval

    mean_rtts.append(mean_rtt)
    conf_intervals.append(CI)

# Plot the results
plt.figure(figsize=(8, 5))
plt.errorbar(delay_values, mean_rtts, yerr=conf_intervals, fmt='o-', capsize=5, label="RTT with 95% CI")
plt.xscale("log")  # Log scale for delay values
plt.xlabel("Delay (seconds)")
plt.ylabel("Mean RTT (ms)")
plt.title("RTT vs Delay with 95% Confidence Intervals")
plt.legend()
plt.grid(True, which="both", linestyle="--", linewidth=0.5)
plt.show()
"""