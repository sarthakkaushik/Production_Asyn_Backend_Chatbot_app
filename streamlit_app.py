import streamlit as st
import requests
import json
from datetime import datetime
import os
from typing import Dict, List
import pandas as pd

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Session state initialization
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

class ChatAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def create_session(self, user_id: str) -> Dict:
        response = requests.post(
            f"{self.base_url}/new_session",
            json={"user_id": user_id}
        )
        response.raise_for_status()
        return response.json()

    def continue_session(self, user_id: str, thread_id: str, question: str) -> Dict:
        response = requests.post(
            f"{self.base_url}/continue_session",
            json={
                "user_id": user_id,
                "thread_id": thread_id,
                "question": question
            }
        )
        response.raise_for_status()
        return response.json()

    def get_session_history(self, thread_id: str) -> List[Dict]:
        response = requests.get(f"{self.base_url}/session_history/{thread_id}")
        response.raise_for_status()
        return response.json()

def initialize_chat_interface():
    st.title("AI Chat Assistant")
    
    # Sidebar for user authentication and session management
    with st.sidebar:
        st.header("Session Management")
        
        # User authentication
        if st.session_state.user_id is None:
            user_id = st.text_input("Enter User ID")
            if st.button("Start Session"):
                if user_id:
                    st.session_state.user_id = user_id
                    try:
                        chat_api = ChatAPI(API_URL)
                        response = chat_api.create_session(user_id)
                        st.session_state.thread_id = response["thread_id"]
                        st.success("Session started successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting session: {str(e)}")
        else:
            st.write(f"Current User: {st.session_state.user_id}")
            if st.button("Start New Thread"):
                try:
                    chat_api = ChatAPI(API_URL)
                    response = chat_api.create_session(st.session_state.user_id)
                    st.session_state.thread_id = response["thread_id"]
                    st.session_state.messages = []
                    st.success("New thread started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating new thread: {str(e)}")
            
            if st.button("Logout"):
                st.session_state.user_id = None
                st.session_state.thread_id = None
                st.session_state.messages = []
                st.rerun()

def load_session_history():
    if st.session_state.thread_id:
        try:
            chat_api = ChatAPI(API_URL)
            history = chat_api.get_session_history(st.session_state.thread_id)
            st.session_state.messages = []
            for msg in history:
                if msg["question"]:
                    st.session_state.messages.append({"role": "user", "content": msg["question"]})
                if msg["ai_answer"]:
                    st.session_state.messages.append({"role": "assistant", "content": msg["ai_answer"]})
        except Exception as e:
            st.error(f"Error loading chat history: {str(e)}")

def display_chat_messages():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

def handle_user_input():
    if prompt := st.chat_input("What would you like to know?"):
        if not st.session_state.user_id or not st.session_state.thread_id:
            st.error("Please start a session first!")
            return

        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display updated chat
        with st.chat_message("user"):
            st.write(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    chat_api = ChatAPI(API_URL)
                    response = chat_api.continue_session(
                        st.session_state.user_id,
                        st.session_state.thread_id,
                        prompt
                    )
                    ai_response = response["ai_answer"]
                    st.write(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    st.error(f"Error getting response: {str(e)}")

def main():
    st.set_page_config(
        page_title="AI Chat Assistant",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Apply custom CSS
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .stChatMessage.user {
            background-color: #f0f2f6;
        }
        .stChatMessage.assistant {
            background-color: #e8f0fe;
        }
        </style>
    """, unsafe_allow_html=True)

    initialize_chat_interface()
    
    if st.session_state.user_id and st.session_state.thread_id:
        if not st.session_state.messages:
            load_session_history()
        
        # Display chat interface
        st.divider()
        display_chat_messages()
        handle_user_input()

if __name__ == "__main__":
    main()