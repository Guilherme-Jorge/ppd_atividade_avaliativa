import random
import time
import threading
import queue
import logging
from typing import Dict, List

from raft.node_state import NodeState
from logger.log_entry import LogEntry


class RaftNode:
    def __init__(self, node_id: str, cluster_size: int):
        """
        Initialize a Raft consensus node with enhanced logging.
        """
        self.node_id = node_id
        self.cluster_size = cluster_size

        self.current_term = 0
        self.voted_for = None
        self.state = NodeState.FOLLOWER

        self.election_timeout = random.uniform(0.15, 0.3)
        self.heartbeat_interval = 0.1
        self.last_heartbeat_time = time.time()

        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0

        self.votes_received = 0
        self.cluster_nodes: Dict[str, "RaftNode"] = {}

        self.message_queue = queue.Queue()
        self.lock = threading.Lock()

        self.logger = logging.getLogger(f"RaftNode-{node_id}")
        self.logger.setLevel(logging.INFO)

        threading.Thread(target=self.election_timer, daemon=True).start()
        threading.Thread(target=self.message_processor, daemon=True).start()

    def start_election(self):
        """Initiate leader election process with prominent logging."""
        with self.lock:
            self.state = NodeState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = 1

            self.logger.warning(
                f"{'='*20} ELECTION STARTED {'='*20}\n"
                f"Node {self.node_id} started election\n"
                f"Term: {self.current_term}\n"
                f"{'='*50}"
            )

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
                self.start_election()

    def handle_vote_request(self, request):
        """Evaluate and respond to vote requests with detailed logging."""
        vote_granted = False

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

        self.logger.info(
            f"{'='*10} VOTE REQUEST {'='*10}\n"
            f"Candidate: {request['candidate_id']}\n"
            f"Request Term: {request['term']}\n"
            f"Current Term: {self.current_term}\n"
            f"Vote Granted: {vote_granted}\n"
            f"{'='*30}"
        )

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

        if self.votes_received > self.cluster_size // 2:
            self.become_leader()

    def become_leader(self):
        """Transition to leader state with prominent logging."""
        with self.lock:
            self.state = NodeState.LEADER

            self.logger.critical(
                f"{'*'*20} LEADER ELECTED {'*'*20}\n"
                f"Node {self.node_id} BECAME LEADER\n"
                f"Term: {self.current_term}\n"
                f"Votes Received: {self.votes_received}\n"
                f"{'*'*50}"
            )

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
        self.last_heartbeat_time = time.time()

        if entries["term"] > self.current_term:
            old_state = self.state
            self.current_term = entries["term"]
            self.state = NodeState.FOLLOWER
            self.voted_for = None

            self.logger.warning(
                f"{'!'*20} STATE CHANGE {'!'*20}\n"
                f"Node {self.node_id} transitioned:\n"
                f"Previous State: {old_state.value}\n"
                f"New State: {self.state.value}\n"
                f"New Term: {self.current_term}\n"
                f"Leader ID: {entries['leader_id']}\n"
                f"{'!'*50}"
            )

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
