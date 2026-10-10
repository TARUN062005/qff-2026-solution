from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel


def execute_counts(
    circuit: QuantumCircuit,
    shots: int,
    seed_simulator: int,
    noise_model: NoiseModel | None,
) -> dict[str, int]:
    simulator = AerSimulator(method="automatic", noise_model=noise_model, seed_simulator=seed_simulator)
    result = simulator.run(circuit, shots=shots).result()
    counts = result.get_counts()
    if not isinstance(counts, dict):
        raise RuntimeError("The simulator returned a counts object that is not a single histogram.")
    return {str(bitstring): int(count) for bitstring, count in counts.items()}
