"""
app/graph/workflow.py
LangGraph StateGraph definition — wires all nodes into the pipeline.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.graph.state import GraphState
from app.agents.nodes import (
    pdf_loader_node,
    text_extraction_agent,
    data_normalization_agent,
    reconciliation_agent,
    compliance_mapping_agent,
    report_generation_agent,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_workflow() -> StateGraph:
    """Construct and compile the LangGraph pipeline."""

    graph = StateGraph(GraphState)

    # Register nodes
    # NOTE: node names must NOT match any GraphState key.
    # State keys: reconciliation, nepal_compliance → use suffixed node names.
    graph.add_node("node_pdf_loader", pdf_loader_node)
    graph.add_node("node_text_extraction", text_extraction_agent)
    graph.add_node("node_data_normalization", data_normalization_agent)
    graph.add_node("node_reconciliation", reconciliation_agent)
    graph.add_node("node_compliance_mapping", compliance_mapping_agent)
    graph.add_node("node_report_generation", report_generation_agent)

    # Entry point
    graph.set_entry_point("node_pdf_loader")

    # Linear pipeline
    graph.add_edge("node_pdf_loader", "node_text_extraction")
    graph.add_edge("node_text_extraction", "node_data_normalization")
    graph.add_edge("node_data_normalization", "node_reconciliation")
    graph.add_edge("node_reconciliation", "node_compliance_mapping")
    graph.add_edge("node_compliance_mapping", "node_report_generation")
    graph.add_edge("node_report_generation", END)

    return graph.compile()


# Singleton compiled graph
_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        logger.info("Compiling LangGraph workflow...")
        _workflow = build_workflow()
        logger.info("Workflow compiled.")
    return _workflow