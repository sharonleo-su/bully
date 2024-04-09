# Bully
Implementation of the Bully Algorithm to elect a leader in a distributed system. 

## Cloning the Repository

To clone this repository and run the application locally, use the following commands:

1. Clone the repository to your local machine:

   ```bash
   git clone https://github.com/sharonleo-su/bully.git
   ```

2. Navigate to the project directory:

   ```bash
   cd bully
   ```

3. Install any necessary dependencies:

   ```bash
   pip install -r requirements.txt
   ```

This project implements the Bully algorithm for leader election in a fully interconnected group of nodes. Each node in the group has an identity represented by a pair: (days until the next birthday, SU ID). The algorithm handles joining the group, participating in elections, detecting leader failures, and recovering from feigned failures.

## Usage

To run the application, execute the following command:

```bash
python lab2.py
```

The program will initiate the node's participation in the group, handle elections, and manage leader failures and recovery.

## Files and Structure

- `lab2.py`: Main driver program implementing the Bully algorithm for leader election.
- `gcd.py`: Contains the Group Coordinator Daemon (GCD) functionality for managing group membership and communications.
- `node.py`: Represents a node in the group, including functionalities for joining, initiating elections, responding to messages, and recovering from failures.
- `message.py`: Defines message structures and protocols for communication between nodes.
- `utils.py`: Utility functions used throughout the application.

## Protocol

The application follows a message-based protocol for communication between nodes, including JOIN, ELECTION, COORDINATOR, and PROBE messages.

## Extra Credit

- Feigning Failure: Nodes can simulate failure by closing sockets or ignoring messages for a random duration, then recover and resume normal operation.

## Contributions

Contributions to this project are welcome. If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request.
