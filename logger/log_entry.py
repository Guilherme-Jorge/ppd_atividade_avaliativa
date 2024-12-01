import uuid


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
