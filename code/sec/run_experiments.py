"""
File to run benchmark experiments campaign for Phase 2. 


"""

from sender import run_sender, get_args

#

def run_capacity_test(sender):

    print("Sender capacity: ", sender.get_capacity())
    return

if __name__ == "__main__":
    # Parse command line arguments
    args = get_args()
    sender = run_sender(args)

    run_capacity_test(sender)

