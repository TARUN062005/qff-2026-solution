from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image
from qiskit import QuantumCircuit

from src.max_cut import MaxCutInstance
from src.processor_model import ProcessorModel


PROCESSOR_COLORS = {"A": "#1f4e79", "B": "#2e7d4f"}


def _finish(figure: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(figure)


def save_processor_graph(processor: ProcessorModel, path: Path) -> None:
    graph = processor.networkx_graph()
    if processor.display_positions is not None:
        positions = {node: processor.display_positions[node] for node in graph.nodes}
    else:
        positions = nx.spring_layout(graph, seed=7)
    figure, axis = plt.subplots(figsize=(6.2, 4.4))
    color = PROCESSOR_COLORS.get(processor.identifier, "#1f4e79")
    nx.draw_networkx(
        graph,
        positions,
        ax=axis,
        node_color=color,
        node_size=780,
        font_color="white",
        font_size=11,
        edge_color="#5c6b73",
        width=2.2,
    )
    status = "official" if processor.provenance.get("official") else "provisional"
    axis.set_title(f"{processor.name} coupling graph ({status}, {graph.number_of_edges()} edges)")
    axis.set_axis_off()
    figure.tight_layout()
    _finish(figure, path)


def save_problem_graph(instance: MaxCutInstance, path: Path) -> None:
    graph = nx.Graph()
    graph.add_nodes_from(instance.vertices)
    graph.add_weighted_edges_from((edge.u, edge.v, edge.weight) for edge in instance.edges)
    positions = nx.circular_layout(graph)
    figure, axis = plt.subplots(figsize=(6.2, 5.2))
    nx.draw_networkx(
        graph,
        positions,
        ax=axis,
        node_color="#1f4e79",
        node_size=780,
        font_color="white",
        edge_color="#5c6b73",
        width=2.0,
    )
    nx.draw_networkx_edge_labels(
        graph,
        positions,
        edge_labels={(edge.u, edge.v): f"{edge.weight:g}" for edge in instance.edges},
        ax=axis,
        font_size=9,
    )
    status = "official" if instance.official else "provisional"
    axis.set_title(f"Weighted Max-Cut instance ({status})")
    axis.set_axis_off()
    figure.tight_layout()
    _finish(figure, path)


def save_circuit_figure(circuit: QuantumCircuit, path: Path, title: str) -> None:
    figure = circuit.draw(output="mpl", fold=-1, idle_wires=False)
    figure.suptitle(title, fontsize=12)
    figure.tight_layout()
    _finish(figure, path)


def save_circuit_panel(image_paths: list[Path], path: Path) -> None:
    images = [Image.open(image_path).convert("RGB") for image_path in image_paths]
    gap = 24
    width = sum(image.width for image in images) + gap * (len(images) - 1)
    height = max(image.height for image in images)
    canvas = Image.new("RGB", (width, height), "white")
    cursor = 0
    for image in images:
        canvas.paste(image, (cursor, 0))
        cursor += image.width + gap
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    for image in images:
        image.close()


def save_grouped_bars(
    categories: list[str],
    series: dict[str, list[float]],
    ylabel: str,
    title: str,
    path: Path,
    yerr: dict[str, list[float]] | None = None,
    footnote: str | None = None,
) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    count = len(categories)
    width = 0.8 / max(1, len(series))
    colors = ["#1f4e79", "#2e7d4f", "#d17a22", "#6b4c9a"]
    for index, (label, values) in enumerate(series.items()):
        offset = (index - (len(series) - 1) / 2) * width
        positions = [item + offset for item in range(count)]
        errors = None if yerr is None else yerr.get(label)
        axis.bar(positions, values, width=width * 0.92, label=label, color=colors[index % len(colors)], yerr=errors, capsize=4)
    axis.set_xticks(range(count), categories)
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False)
    _finish_figure(figure, path, footnote)


def _finish_figure(figure, path: Path, footnote: str | None) -> None:
    if footnote:
        figure.tight_layout(rect=(0.0, 0.14, 1.0, 1.0))
        figure.text(0.01, 0.02, footnote, fontsize=8, ha="left", va="bottom")
    else:
        figure.tight_layout()
    _finish(figure, path)


def save_performance_chart(
    rows: list[dict[str, object]],
    classical_optimum: float,
    ideal_qaoa_expectation: float,
    path: Path,
    footnote: str | None = None,
) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    labels = [f"{row['processor']} {row['execution_mode']}" for row in rows]
    values = [float(row["expected_cut"]) for row in rows]
    errors = [float(row["expected_cut_standard_error"]) for row in rows]
    colors = ["#1f4e79" if row["processor"] == "A" else "#2e7d4f" for row in rows]
    axis.bar(labels, values, color=colors, yerr=errors, capsize=4)
    axis.axhline(classical_optimum, color="#9a3412", linestyle="--", label=f"Exact optimum {classical_optimum:.4g}")
    axis.axhline(ideal_qaoa_expectation, color="#334155", linestyle=":", label=f"Ideal QAOA expectation {ideal_qaoa_expectation:.4g}")
    axis.set_ylabel("Expected cut value")
    axis.set_title("Measured problem performance")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False)
    _finish_figure(figure, path, footnote)


def save_tradeoff_chart(rows: list[dict[str, object]], path: Path, footnote: str | None = None) -> None:
    figure, axis = plt.subplots(figsize=(7.4, 5.0))
    for row in rows:
        color = "#1f4e79" if row["processor"] == "A" else "#2e7d4f"
        marker = "o" if row["execution_mode"] == "ideal" else "s"
        axis.errorbar(
            float(row["transpiled_two_qubit_count"]),
            float(row["expected_cut"]),
            yerr=float(row["expected_cut_standard_error"]),
            fmt=marker,
            color=color,
            markersize=8,
            capsize=4,
            label=f"Processor {row['processor']} {row['execution_mode']}",
        )
    axis.set_xlabel("Transpiled two-qubit instructions")
    axis.set_ylabel("Expected cut value")
    axis.set_title("Measured circuit cost and solution quality")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False)
    _finish_figure(figure, path, footnote)


def save_cut_histogram(histograms: dict[str, dict[str, int]], path: Path) -> None:
    values = sorted({float(value) for histogram in histograms.values() for value in histogram})
    figure, axis = plt.subplots(figsize=(8.4, 4.8))
    width = 0.8 / max(1, len(histograms))
    colors = ["#1f4e79", "#5b8fb8", "#2e7d4f", "#7dba8a"]
    for index, (label, histogram) in enumerate(histograms.items()):
        total = sum(histogram.values()) or 1
        heights = [histogram.get(f"{value:.10g}", 0) / total for value in values]
        positions = [item + (index - (len(histograms) - 1) / 2) * width for item in range(len(values))]
        axis.bar(positions, heights, width=width * 0.92, label=label, color=colors[index % len(colors)])
    axis.set_xticks(range(len(values)), [f"{value:g}" for value in values], rotation=45, ha="right")
    axis.set_xlabel("Cut value")
    axis.set_ylabel("Shot fraction")
    axis.set_title("Measured cut-value distribution")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False)
    figure.tight_layout()
    _finish(figure, path)
