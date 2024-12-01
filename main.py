import enum
import uuid
import random
import time
import threading
import queue
import logging
import signal
import sys
from typing import Dict, List

class LogEntry:
    """
    Represents an individual log entry in the Raft consensus algorithm.

    Attributes:
    - term: The term when the entry was created
    - command: The actual command/data to be replicated
    - id: Unique identifier for the log entry
    """

    def __init__(self, term: int, command: str):
        self.term = term
        self.command = command
        self.id = str(uuid.uuid4())

    def __repr__(self):
        return f"LogEntry(term={self.term}, command={self.command}, id={self.id})"
    
class NodeState(enum.Enum):
    """
    Represents the possible states of a Raft node.

    - FOLLOWER: Normal state for a node that is not leading or campaigning
    - CANDIDATE: State when node is requesting votes to become a leader
    - LEADER: State when node is currently managing the cluster
    """

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftNode:
    def __init__(self, node_id: str, cluster_size: int):
        """
        Initialize a Raft consensus node with enhanced logging.
        """
        # Node identification and cluster information
        self.node_id = node_id
        self.cluster_size = cluster_size

        # State variables
        self.current_term = 0
        self.voted_for = None
        self.state = NodeState.FOLLOWER

        # Election and timeout management
        self.election_timeout = random.uniform(0.15, 0.3)
        self.heartbeat_interval = 0.1
        self.last_heartbeat_time = time.time()

        # Log and commit management
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0

        # Voting and leadership tracking
        self.votes_received = 0
        self.cluster_nodes: Dict[str, "RaftNode"] = {}

        # Messaging and synchronization
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()

        # Logging setup with custom formatting
        self.logger = logging.getLogger(f"RaftNode-{node_id}")
        self.logger.setLevel(logging.INFO)

        # Start background threads
        threading.Thread(target=self.election_timer, daemon=True).start()
        threading.Thread(target=self.message_processor, daemon=True).start()

    def start_election(self):
        """Initiate leader election process with prominent logging."""
        with self.lock:
            self.state = NodeState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = 1

            # Prominent election start log
            self.logger.warning(
                f"{'='*20} ELECTION STARTED {'='*20}\n"
                f"Node {self.node_id} started election\n"
                f"Term: {self.current_term}\n"
                f"{'='*50}"
            )

            # Request votes from other nodes
            for node in self.cluster_nodes.values():
                if node.node_id != self.node_id:
                    self.send_request_vote(node)

    def send_request_vote(self, target_node):
        """Send vote request message to another node."""
        last_log_term = self.log[-1].term if self.log else 0
        vote_request = {
            "type": "vote_request",
            "term": self.current_term,
            "candidate_id": self.node_id,
            "last_log_term": last_log_term,
            "last_log_index": len(self.log) - 1,
        }
        target_node.receive_message(vote_request)

    def receive_message(self, message):
        """Process incoming messages from other nodes."""
        self.message_queue.put(message)

    def message_processor(self):
        """Background thread to process incoming messages."""
        while True:
            try:
                message = self.message_queue.get(timeout=self.election_timeout)

                if message["type"] == "vote_request":
                    self.handle_vote_request(message)
                elif message["type"] == "vote_response":
                    self.handle_vote_response(message)
                elif message["type"] == "append_entries":
                    self.handle_append_entries(message)

            except queue.Empty:
                # Election timeout occurred
                self.start_election()

    def handle_vote_request(self, request):
        """Evaluate and respond to vote requests with detailed logging."""
        vote_granted = False

        # Check term and log conditions
        if request["term"] > self.current_term and self._log_up_to_date(
            request["last_log_term"], request["last_log_index"]
        ):
            vote_granted = True
            self.voted_for = request["candidate_id"]
            self.current_term = request["term"]

        response = {
            "type": "vote_response",
            "term": self.current_term,
            "vote_granted": vote_granted,
        }

        # Detailed vote request logging
        self.logger.info(
            f"{'='*10} VOTE REQUEST {'='*10}\n"
            f"Candidate: {request['candidate_id']}\n"
            f"Request Term: {request['term']}\n"
            f"Current Term: {self.current_term}\n"
            f"Vote Granted: {vote_granted}\n"
            f"{'='*30}"
        )

        # Send response back to candidate
        candidate_node = self.cluster_nodes.get(request["candidate_id"])
        if candidate_node:
            candidate_node.receive_message(response)

    def _log_up_to_date(
        self, candidate_last_term: int, candidate_last_index: int
    ) -> bool:
        """Check if candidate's log is at least as up-to-date as this node's."""
        if not self.log:
            return True

        last_term = self.log[-1].term
        return candidate_last_term > last_term or (
            candidate_last_term == last_term
            and candidate_last_index >= len(self.log) - 1
        )

    def handle_vote_response(self, response):
        """Process vote responses during election."""
        if self.state != NodeState.CANDIDATE:
            return

        if response["vote_granted"]:
            self.votes_received += 1

        # Check if majority achieved
        if self.votes_received > self.cluster_size // 2:
            self.become_leader()

    def become_leader(self):
        """Transition to leader state with prominent logging."""
        with self.lock:
            self.state = NodeState.LEADER

            # Prominent leader election log
            self.logger.critical(
                f"{'*'*20} LEADER ELECTED {'*'*20}\n"
                f"Node {self.node_id} BECAME LEADER\n"
                f"Term: {self.current_term}\n"
                f"Votes Received: {self.votes_received}\n"
                f"{'*'*50}"
            )

            # Send initial heartbeats to all nodes
            for node in self.cluster_nodes.values():
                if node.node_id != self.node_id:
                    self.send_heartbeat(node)

    def send_heartbeat(self, target_node):
        """Send periodic heartbeat to maintain leadership."""
        append_entries = {
            "type": "append_entries",
            "term": self.current_term,
            "leader_id": self.node_id,
            "entries": [],  # Empty for heartbeat
            "leader_commit": self.commit_index,
        }
        target_node.receive_message(append_entries)

    def handle_append_entries(self, entries):
        """Process append entries message from leader with enhanced logging."""
        # Reset election timeout
        self.last_heartbeat_time = time.time()

        # Transition back to follower if term is higher
        if entries["term"] > self.current_term:
            old_state = self.state
            self.current_term = entries["term"]
            self.state = NodeState.FOLLOWER
            self.voted_for = None

            # Prominent state change log
            self.logger.warning(
                f"{'!'*20} STATE CHANGE {'!'*20}\n"
                f"Node {self.node_id} transitioned:\n"
                f"Previous State: {old_state.value}\n"
                f"New State: {self.state.value}\n"
                f"New Term: {self.current_term}\n"
                f"Leader ID: {entries['leader_id']}\n"
                f"{'!'*50}"
            )

        # Log details of append entries
        self.logger.info(
            f"{'+'*10} APPEND ENTRIES {'+'*10}\n"
            f"From Leader: {entries['leader_id']}\n"
            f"Term: {entries['term']}\n"
            f"Commit Index: {entries['leader_commit']}\n"
            f"{'+'*30}"
        )

    def election_timer(self):
        """Manage election timeouts and state transitions."""
        while True:
            time.sleep(self.election_timeout)

            current_time = time.time()
            if (
                current_time - self.last_heartbeat_time >= self.election_timeout
                and self.state != NodeState.LEADER
            ):
                self.start_election()
class RaftClusterSimulator:
    """
    Simulates a Raft consensus cluster with enhanced node failure logging.
    """

    def __init__(
        self,
        num_nodes: int = 5,
        failure_probability: float = 0.1,
        simulation_duration: float = 60,
    ):
        """
        Initialize the cluster simulator with enhanced logging.
        """
        # Configure logging with more detailed formatting
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("raft_simulation.log", mode="w"),
            ],
        )

        # Create a cluster-wide logger
        self.logger = logging.getLogger("RaftClusterSimulator")

        # Create nodes
        self.nodes = [RaftNode(f"node-{i}", num_nodes) for i in range(num_nodes)]

        # Establish cluster connections
        for node in self.nodes:
            node.cluster_nodes = {
                n.node_id: n for n in self.nodes if n.node_id != node.node_id
            }

        self.num_nodes = num_nodes
        self.failure_probability = failure_probability
        self.simulation_duration = simulation_duration

        self.failure_threads = []
        self.stop_event = threading.Event()

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def simulate_node_failure(self, node: RaftNode):
        """
        Simulate random node failure and recovery with prominent logging.
        """
        while not self.stop_event.is_set():
            try:
                # Random sleep to simulate node operation
                self.stop_event.wait(timeout=random.uniform(5, 15))

                # Potential node failure
                if (
                    not self.stop_event.is_set()
                    and random.random() < self.failure_probability
                ):
                    # Failure log with visual distinction
                    node.logger.critical(
                        f"{'#'*20} NODE FAILURE {'#'*20}\n"
                        f"Node {node.node_id} has CRASHED!\n"
                        f"Current State: {node.state.value}\n"
                        f"Term: {node.current_term}\n"
                        f"{'#'*50}"
                    )

                    # Simulate failure duration
                    self.stop_event.wait(timeout=random.uniform(3, 7))

                    if not self.stop_event.is_set():
                        # Recovery log with visual distinction
                        node.logger.critical(
                            f"{'+'*20} NODE RECOVERY {'+'*20}\n"
                            f"Node {node.node_id} has RECOVERED!\n"
                            f"Reinitializing to default state\n"
                            f"{'+'*50}"
                        )

                        # Reinitialize node state
                        node.state = RaftNode.NodeState.FOLLOWER
                        node.votes_received = 0
                        node.voted_for = None

            except Exception as e:
                node.logger.error(f"Error in node failure simulation: {e}")

    def shutdown(self, signum=None, frame=None):
        """
        Gracefully stop the simulation.

        Args:
        - signum: Signal number (optional)
        - frame: Current stack frame (optional)
        """
        if not self.stop_event.is_set():
            logging.info("Initiating graceful shutdown...")

            # Set stop event to signal all threads to stop
            self.stop_event.set()

            # Wait for all threads to finish
            for thread in self.failure_threads:
                thread.join(timeout=2)

            # Log final node states
            for node in self.nodes:
                logging.info(f"Final state of {node.node_id}: {node.state.value}")

            logging.info("Simulation stopped successfully.")

            # Exit the program if called from signal handler
            if signum is not None:
                sys.exit(0)

    def run(self):
        """
        Run the cluster simulation with enhanced logging.
        """
        # Cluster start log
        self.logger.critical(
            f"{'='*20} RAFT CLUSTER SIMULATION STARTED {'='*20}\n"
            f"Nodes: {self.num_nodes}\n"
            f"Failure Probability: {self.failure_probability}\n"
            f"Simulation Duration: {self.simulation_duration} seconds\n"
            f"{'='*60}"
        )

        try:
            # Start failure simulation threads
            self.failure_threads = [
                threading.Thread(
                    target=self.simulate_node_failure, args=(node,), daemon=True
                )
                for node in self.nodes
            ]

            for thread in self.failure_threads:
                thread.start()

            # Wait for specified simulation duration or stop event
            self.stop_event.wait(timeout=self.simulation_duration)

            # Log simulation completion
            self.logger.critical(
                f"{'='*20} SIMULATION COMPLETED {'='*20}\n"
                f"Duration: {self.simulation_duration} seconds\n"
                f"{'='*50}"
            )

        except Exception as e:
            self.logger.error(f"Error during simulation: {e}")

        finally:
            # Ensure graceful shutdown
            self.shutdown()

if __name__ == "__main__":
    try:
        # Create a cluster with specific parameters
        simulator = RaftClusterSimulator(
            num_nodes=5,  # Number of nodes in the cluster
            failure_probability=0.5,  # 50% chance of node failure
            simulation_duration=10,  # Run for 10 seconds
        )

        # Run the cluster simulation
        simulator.run()

    except Exception as e:
        logging.error(f"Simulation failed: {e}")
