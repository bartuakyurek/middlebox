
# Phase 1 Report

## NATS Processor
This processor is based on the given python processor example. The main difference is that it declares a class for the processor, to adopt a modular approach. In the upcoming phases it is excpected to be easier to extend its functionality through this class, to add the covert channel detection and mitigation functionalities.

The processor samples a random delay value $D$ from a uniform distribution, waits $D$ seconds before publishing the incoming packets. The mean of the uniform distribution is provided by the arguments, ì.e. via  ``phython main.py -d <delay_in_seconds>``.

 **TODO: Is this description up to date?**

## Tests
To measure RTT, ``ping`` command is used throughout the bash scripts. To run all the tests ``run_all.sh`` is used after starting the docker containers. A script inside ``sec``, ``/ping_test/ping_test.sh`` is provided to ping the ``insec`` host with $N$ packets. It also has a parameter of $K$ trials, to run the same experiment for $K$ times.

Throughout the experiments $N=100$ and $K=30$ is used, i.e. 100 packets are sent from ``sec`` to ``insec`` for 30 different trials. $K$ trials are conducted in order to calculate a confidence interval as it was suggested for this phase. 

**TODO: Are these N and K values up to date?**  

![alt text](delay_vs_rtt.png "Mean of a uniform random delay vs. Average RTT")

**TODO: Elaborate on the graph**

