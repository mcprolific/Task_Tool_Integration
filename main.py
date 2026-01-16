from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import agent
from langchain_core.messages import HumanMessage

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello World"}


# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or your React app origin
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/chat")
def chat(request: ChatRequest):
    result = agent.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": request.session_id}}
    )
    return {"reply": result["messages"][-1].content}


# pip install duckduckgo-search