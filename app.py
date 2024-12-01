import logging

from raft.cluster_simulator import RaftClusterSimulator


if __name__ == "__main__":
    try:
        simulator = RaftClusterSimulator(
            num_nodes=5,
            failure_probability=0.7,
            simulation_duration=10,
        )

        simulator.run()

    except Exception as e:
        logging.error(f"Simulation failed: {e}")
