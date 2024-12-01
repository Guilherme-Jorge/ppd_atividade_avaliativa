import random
import threading
import logging
import signal
import sys

from raft.node import RaftNode


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
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("raft_simulation.log", mode="w"),
            ],
        )

        self.logger = logging.getLogger("RaftClusterSimulator")

        self.nodes = [RaftNode(f"node-{i}", num_nodes) for i in range(num_nodes)]

        for node in self.nodes:
            node.cluster_nodes = {
                n.node_id: n for n in self.nodes if n.node_id != node.node_id
            }

        self.num_nodes = num_nodes
        self.failure_probability = failure_probability
        self.simulation_duration = simulation_duration

        self.failure_threads = []
        self.stop_event = threading.Event()

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def simulate_node_failure(self, node: RaftNode):
        """
        Simulate random node failure and recovery with prominent logging.
        """
        while not self.stop_event.is_set():
            try:
                self.stop_event.wait(timeout=random.uniform(5, 15))

                if (
                    not self.stop_event.is_set()
                    and random.random() < self.failure_probability
                ):
                    node.logger.critical(
                        f"{'#'*20} NODE FAILURE {'#'*20}\n"
                        f"Node {node.node_id} has CRASHED!\n"
                        f"Current State: {node.state.value}\n"
                        f"Term: {node.current_term}\n"
                        f"{'#'*50}"
                    )

                    self.stop_event.wait(timeout=random.uniform(3, 7))

                    if not self.stop_event.is_set():
                        node.logger.critical(
                            f"{'+'*20} NODE RECOVERY {'+'*20}\n"
                            f"Node {node.node_id} has RECOVERED!\n"
                            f"Reinitializing to default state\n"
                            f"{'+'*50}"
                        )

                        node.state = RaftNode.NodeState.FOLLOWER
                        node.votes_received = 0
                        node.voted_for = None

            except Exception as e:
                node.logger.error(f"Error in node failure simulation: {e}")

    def shutdown(self, signum=None):
        """
        Gracefully stop the simulation.

        Args:
        - signum: Signal number (optional)
        - frame: Current stack frame (optional)
        """
        if not self.stop_event.is_set():
            logging.info("Initiating graceful shutdown...")

            self.stop_event.set()

            for thread in self.failure_threads:
                thread.join(timeout=2)

            for node in self.nodes:
                logging.info(f"Final state of {node.node_id}: {node.state.value}")

            logging.info("Simulation stopped successfully.")

            if signum is not None:
                sys.exit(0)

    def run(self):
        """
        Run the cluster simulation with enhanced logging.
        """
        self.logger.critical(
            f"{'='*20} RAFT CLUSTER SIMULATION STARTED {'='*20}\n"
            f"Nodes: {self.num_nodes}\n"
            f"Failure Probability: {self.failure_probability}\n"
            f"Simulation Duration: {self.simulation_duration} seconds\n"
            f"{'='*60}"
        )

        try:
            self.failure_threads = [
                threading.Thread(
                    target=self.simulate_node_failure, args=(node,), daemon=True
                )
                for node in self.nodes
            ]

            for thread in self.failure_threads:
                thread.start()

            self.stop_event.wait(timeout=self.simulation_duration)

            self.logger.critical(
                f"{'='*20} SIMULATION COMPLETED {'='*20}\n"
                f"Duration: {self.simulation_duration} seconds\n"
                f"{'='*50}"
            )

        except Exception as e:
            self.logger.error(f"Error during simulation: {e}")

        finally:
            self.shutdown()
