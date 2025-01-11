from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
import os
import json

class ChatState(TypedDict):
    messages: List[Dict[str, str]]
    error: bool

class ChatbotWorkflow:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.workflow = self._create_workflow()

    def _initialize_llm(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            model="gpt-4o-mini",
            deployment_name="gpt-4o-mini",
            api_key=os.getenv("AZURE_OPENAI_API_KEY_2"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_2"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_2"),
            temperature=0.7,
        )

    def _create_workflow(self):
        workflow = StateGraph(ChatState)
        workflow.add_node("process_message", self.process_message)
        workflow.set_entry_point("process_message")
        workflow.add_edge("process_message", END)
        return workflow.compile()

    async def process_message(self, state: ChatState) -> ChatState:
        try:
            messages = state.get("messages", [])
            response = await self.llm.ainvoke(messages)
            
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            return {
                "messages": messages,
                "error": False
            }
        except Exception as e:
            return {
                "messages": messages,
                "error": True
            }

    async def ainvoke(self, input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        current_messages = []
        if input_data.get("message"):
            current_messages.append({
                "role": "user",
                "content": input_data["message"]
            })
        
        state = await self.workflow.ainvoke({
            "messages": current_messages,
            "error": False
        })
        
        return state