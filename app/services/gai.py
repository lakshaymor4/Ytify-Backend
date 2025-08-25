from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq import ChatGroq
from typing_extensions import TypedDict
from typing import Annotated
from dotenv import load_dotenv
import os
import json

load_dotenv()

def get_song(name, artist):
    # Load keys
    tavily_key = os.getenv("TAVILY_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    # Define State before referencing it
    class State(TypedDict):
        messages: Annotated[list[AnyMessage], add_messages]

    def pick_best_title(state: State):
        last_message = state["messages"][-1]
        try:
            results = json.loads(last_message.content) if isinstance(last_message.content, str) else last_message.content
        except Exception:
            results = []

        if isinstance(results, list) and len(results) > 0:
            filtered = [
                r for r in results
                if "slowed" not in r.get("title", "").lower()
                and "playlist" not in r.get("title", "").lower()
                and "reverb" not in r.get("title", "").lower()
                and "lyrics" not in r.get("title", "").lower()
            ]
            if filtered:
                best = max(filtered, key=lambda r: r.get("score", 0))
                return {"messages": [AIMessage(content=best["title"])]}

        return {"messages": [AIMessage(content="No result found")]}

    # Tools and LLM setup
    tools = [TavilySearchResults(max_results=5, tavily_api_key=tavily_key)]
    llm_with_tools = ChatGroq(model="gemma2-9b-it").bind_tools(tools)

    def tool_calling_llm(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    # Build graph
    builder = StateGraph(State)
    builder.add_node("tool_calling_llm", tool_calling_llm)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("pick_best_title", pick_best_title)
    builder.add_edge(START, "tool_calling_llm")
    builder.add_conditional_edges("tool_calling_llm", tools_condition)
    builder.add_edge("tools", "pick_best_title")
    builder.add_edge("pick_best_title", END)
    graph = builder.compile()

    # Invoke graph
    test_messages = graph.invoke({
        "messages": [
            HumanMessage(content=(
                f'Given this Spotify track: "{artist} - {name}" '
                "Find the YouTube Music alternative of the song (no playlist, only songs). "
                "It can be in another language, can have ft or featuring, can have original in its name. "
                "Give only the best, no slowed, reverb, or lyrics versions. "
                "Search on YouTube Music, return only the best title."
            ))
        ]
    })

    return test_messages["messages"][-1].content
