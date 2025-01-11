import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configure the API endpoint
API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Chatbot", layout="wide")

# Add custom CSS for better styling
st.markdown("""
    <style>
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .bot-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    st.title("AI Chatbot")
    
    # Initialize chat history if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Chat history section
    st.sidebar.title("Chat History")
    if st.sidebar.button("Refresh History"):
        try:
            response = requests.get(f"{API_URL}/chat_history/")
            if response.status_code == 200:
                history = response.json()
                df = pd.DataFrame(history)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                st.sidebar.dataframe(
                    df[['timestamp', 'user_message', 'bot_response']],
                    hide_index=True,
                    use_container_width=True
                )
        except Exception as e:
            st.sidebar.error(f"Error fetching history: {str(e)}")

    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="chat-message user-message">You: {message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message bot-message">Bot: {message["content"]}</div>', 
                       unsafe_allow_html=True)

    # Chat input
    user_input = st.text_input("Type your message:", key="user_input")
    
    if st.button("Send") and user_input:
        try:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get bot response
            response = requests.post(f"{API_URL}/chat/", json={"message": user_input})
            
            if response.status_code == 200:
                bot_response = response.json()["response"]
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Clear input
                st.session_state.user_input = ""
                
                # Rerun to update the chat display
                st.experimental_rerun()
            else:
                st.error("Failed to get response from the bot.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 