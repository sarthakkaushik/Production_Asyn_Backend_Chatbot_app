# Template for langgraph based psotgres based sync memory

import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv()

class State(TypedDict):
    message: Annotated[list, add_messages]

class Chatbotflow:
    def __init__(self):    
        self.checkpointer = None
        self.workflow = None
        self.llm = AzureChatOpenAI(
            model="gpt-4o-mini",
            deployment_name="gpt-4o-mini", 
            api_key=os.getenv("AZURE_OPENAI_API_KEY_2"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_2"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_2"),
        )

    def set_checkpointer(self, checkpointer):
        self.checkpointer = checkpointer
        self.workflow = self._create_workflow()

    async def chatbot(self, state: State):
        try:
            response = await self.llm.ainvoke(state["message"])
            return {"message": response}
        except Exception as e:
            return {"message": f"Error occurred: {str(e)}"}

    def _create_workflow(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", self.chatbot)  # Use instance method
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", END)
        return graph_builder.compile(
            checkpointer=self.checkpointer
        )
    
    async def ainvoke(self, *args, **kwargs):
        if not self.workflow:
            raise RuntimeError("Workflow has no checkpointer set.")
        return await self.workflow.ainvoke(*args, **kwargs)