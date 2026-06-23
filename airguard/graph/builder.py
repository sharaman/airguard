from langgraph.graph import StateGraph, END

from airguard.graph.state import AirGuardState
from airguard.graph.nodes import (
    collect_node, analyze_node, anomaly_node,
    rag_node, trend_node, rag_trend_node, report_node,
)
from airguard.graph.edges import route_after_anomaly, route_after_trend


def build_graph():
    g = StateGraph(AirGuardState)

    g.add_node("collect", collect_node)
    g.add_node("analyze", analyze_node)
    g.add_node("detect_anomaly", anomaly_node)
    g.add_node("fetch_rag", rag_node)
    g.add_node("detect_trend", trend_node)
    g.add_node("fetch_rag_trend", rag_trend_node)
    g.add_node("generate_report", report_node)

    g.set_entry_point("collect")
    g.add_edge("collect", "analyze")
    g.add_edge("analyze", "detect_anomaly")

    g.add_conditional_edges("detect_anomaly", route_after_anomaly, {
        "fetch_rag": "fetch_rag",
        "detect_trend": "detect_trend",
    })
    g.add_edge("fetch_rag", "detect_trend")

    g.add_conditional_edges("detect_trend", route_after_trend, {
        "fetch_rag_trend": "fetch_rag_trend",
        "generate_report": "generate_report",
    })
    g.add_edge("fetch_rag_trend", "generate_report")
    g.add_edge("generate_report", END)

    return g.compile()


def export_graph_schema():
    graph = build_graph()
    print(graph.get_graph().draw_mermaid())


if __name__ == "__main__":
    export_graph_schema()
