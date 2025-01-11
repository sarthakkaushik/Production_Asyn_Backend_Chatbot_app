import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    "AZURE_OPENAI_API_KEY_2",
    "AZURE_OPENAI_ENDPOINT_2",
    "AZURE_OPENAI_API_VERSION_2"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class State(TypedDict):
    message: Annotated[List[Dict[str, str]], add_messages]

def initialize_llm() -> AzureChatOpenAI:
    try:
        llm = AzureChatOpenAI(
            model="gpt-4o-mini",
            deployment_name="gpt-4o-mini",
            api_key=os.getenv("AZURE_OPENAI_API_KEY_2"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_2"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_2"),
            temperature=0.7,
            request_timeout=30,
        )
        # Test the LLM connection
        test_message = [HumanMessage(content="test")]
        test_response = llm.invoke(test_message)
        logger.info("LLM initialized successfully")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Azure OpenAI: {str(e)}")
        raise RuntimeError(f"Failed to initialize Azure OpenAI: {str(e)}")

def chatbot(state: State) -> Dict[str, Any]:
    try:
        if not state.get("message"):
            logger.warning("No messages provided in state")
            raise ValueError("No messages provided in state")
        
        # Convert the message format
        messages = [
            HumanMessage(content=msg["content"]) if msg["role"] == "user" 
            else AIMessage(content=msg["content"])
            for msg in state["message"]
        ]
        
        logger.info(f"Processing message: {messages[-1].content}")
        response = llm.invoke(messages)
        
        # Format the response
        formatted_response = {
            "role": "assistant",
            "content": response.content if hasattr(response, 'content') else str(response)
        }
        
        logger.info(f"Generated response: {formatted_response['content'][:100]}...")
        return {"message": formatted_response}
    except Exception as e:
        logger.error(f"Error in chatbot function: {str(e)}")
        error_message = {
            "role": "assistant", 
            "content": "I apologize, but I encountered an error. Please try again or contact support if the issue persists."
        }
        return {"message": error_message}

# Initialize the language model
try:
    llm = initialize_llm()
except Exception as e:
    logger.critical(f"Failed to initialize application: {str(e)}")
    raise

# Build the graph
graph_builder = StateGraph(State)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge("chatbot", END)

# Compile the graph
graph = graph_builder.compile()

# Example usage (commented out for production)
# result = graph.invoke({"mes": [{"role": "user", "content": "What is 2+2?"}]})
# print(result)