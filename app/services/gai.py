from langchain_community.tools.tavily_search import TavilySearchResults
import json
from langchain_core.messages import AIMessage
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph , START , END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from typing import Annotated
from langchain.tools import TavilySearchResults
from langchain_groq import ChatGroq
from langchain_core.messages import  HumanMessage


def get_song(name , artist):
    tools = [TavilySearchResults(max_results=5)]

    llm = ChatGroq(model = "gemma2-9b-it")

    llm_with_tools = ChatGroq(model="gemma2-9b-it").bind_tools(tools)

    class State(TypedDict):
        messages: Annotated[list[AnyMessage], add_messages]
    def tool_calling_llm(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    builder = StateGraph(State)
    builder.add_node("tool_calling_llm", tool_calling_llm)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("pick_best_title", pick_best_title)
    builder.add_edge(START, "tool_calling_llm")
    builder.add_conditional_edges(
        "tool_calling_llm",
        tools_condition
    )
    builder.add_edge("tools", "pick_best_title")

    builder.add_edge("pick_best_title", END)
    graph = builder.compile()

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



    
    
    test_messages = graph.invoke({"messages": [HumanMessage(content=f"""Given this Spotify track: "{artist} - {name}"
    Find the youtube music alternative of the song , no playlist only songs it can be in another language , can have ft or featuring  , can have original in it 's name and all sorts of things and give only the best , also don't use any song revies and an dno other versions of the songs to be used just the orignal one that has been asked by the user don't deviate from it and search it oon youtubemusic  rather than youtube which is the most accurate also just tell me the title of the song which one to choose """)]})

    song = test_messages["messages"][-1].content
    return song



