import enum


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
