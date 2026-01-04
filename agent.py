# agent.py
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env")

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# ------------------- TOOLS -------------------

@tool
def weather_tool(city: str) -> str:
    """
    Return the simulated weather for a given city.
    Example: weather_tool("Lagos") -> "Sunny, 30°C"
    """
    fake_weather = {
        "Lagos": "Sunny, 30°C",
        "Abuja": "Cloudy, 28°C",
        "Paris": "Rainy, 15°C"
    }
    return fake_weather.get(city.title(), f"Weather for {city} is not available.")

@tool
def dictionary_tool(word: str) -> str:
    """
    Return the definition of a word from a small dictionary.
    Example: dictionary_tool("ephemeral") -> "lasting for a very short time"
    """
    small_dict = {
        "ephemeral": "lasting for a very short time",
        "prolific": "producing much fruit or many works",
        "python": "a high-level programming language"
    }
    return small_dict.get(word.lower(), f"No definition found for '{word}'")

@tool
def web_search_tool(query: str) -> str:
    """
    Perform a web search using DuckDuckGo and return top 3 results.
    Example: web_search_tool("AI news") -> "- Title1: URL1 ..."
    """
    from duckduckgo_search import DDGS
    ddgs = DDGS()
    results = ddgs.text(query, max_results=3)
    return "\n".join([f"- {r['title']}: {r['href']}" for r in results]) or "No results found."

# List of tools
tools = [weather_tool, dictionary_tool, web_search_tool]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# ------------------- AGENT NODE -------------------

sys_msg = SystemMessage(content="""
You are a helpful assistant with access to tools:
- Use weather_tool for weather queries
- Use dictionary_tool for word definitions
- Use web_search_tool for web searches
Only call tools when necessary; otherwise, answer directly.
""")

def assistant(state: MessagesState) -> dict:
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# ------------------- CONDITIONAL ROUTING -------------------

from typing import Literal

def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    """
    Decide next step based on last AI message.
    If tools were called -> go to tools node
    Else -> finish
    """
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"
    return "__end__"

# ------------------- BUILD STATE GRAPH -------------------

builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))  # Executes tool calls automatically

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", should_continue, {"tools": "tools", "__end__": END})
builder.add_edge("tools", "assistant")  # After tool execution, go back to assistant

# ------------------- MEMORY -------------------

memory = MemorySaver()
agent = builder.compile(checkpointer=memory)

print("Agent initialized with 3 tools and memory")
