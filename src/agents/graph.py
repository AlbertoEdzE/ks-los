from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage
from src.agents.state import AgentState
from src.agents.nodes_legacy import (
    journey_coach_node,
    tool_node,
    risk_engine_node,
    advisory_node,
    profile_parser_node
)
from src.agents.nodes_calculation import calculation_node


def route_journey_coach(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM decided to call a tool
    if last_message.tool_calls:
        return "tools"

    content = (getattr(last_message, "content", "") or "").lower()
    if any(k in content for k in ["credit profile", "generate a credit profile", "risk score", "credit score profile"]):
        return "tools"

    # Otherwise, stop (and wait for user input in next turn)
    return END


def build_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("journey_coach", journey_coach_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("profile_parser", profile_parser_node)
    workflow.add_node("calculation", calculation_node)  # NEW - Task 3
    workflow.add_node("risk_engine", risk_engine_node)
    workflow.add_node("advisory", advisory_node)

    # Add Edges
    workflow.set_entry_point("journey_coach")

    workflow.add_conditional_edges(
        "journey_coach",
        route_journey_coach,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "profile_parser")
    
    workflow.add_edge("profile_parser", "calculation")  # UPDATED - calculations before risk
    workflow.add_edge("calculation", "risk_engine")     # NEW - calculation → risk
    workflow.add_edge("risk_engine", "advisory")
    workflow.add_edge("advisory", END)

    return workflow.compile()


app = build_graph()
