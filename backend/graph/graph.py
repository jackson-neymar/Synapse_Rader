from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes.collector import collector_node
from .nodes.curator import curator_node
from .nodes.analyst import analyst_node
from .nodes.editor import editor_node
from .nodes.dispatcher import dispatcher_node


def build_synapse_rader_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("collector", collector_node)
    builder.add_node("curator", curator_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("editor", editor_node)
    builder.add_node("dispatcher", dispatcher_node)

    builder.set_entry_point("collector")
    builder.add_edge("collector", "curator")
    builder.add_edge("curator", "analyst")
    builder.add_edge("analyst", "editor")
    builder.add_edge("editor", "dispatcher")
    builder.add_edge("dispatcher", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
