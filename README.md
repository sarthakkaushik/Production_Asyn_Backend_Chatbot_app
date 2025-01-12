# Production-Ready Chatbot Application

A production-ready chatbot application built with FastAPI, LangGraph, and Streamlit, featuring PostgreSQL for conversation history storage.

## Files to consider
-- Backend - Fatapi- app3.py
-- Frontend -Streamlit- Streamlit_app.py


## Features

- Real-time chat interface with Streamlit
- FastAPI backend for efficient request handling
- PostgreSQL database for chat history storage
- Azure OpenAI integration via LangGraph
- Responsive and user-friendly design

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Azure OpenAI API credentials

## Setup

1. Clone the repository and navigate to the project directory

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost:5432/chatbot_db
AZURE_OPENAI_API_KEY_2=your_api_key
AZURE_OPENAI_ENDPOINT_2=your_endpoint
AZURE_OPENAI_API_VERSION_2=your_api_version
```

5. Initialize the database:
```bash
python -c "from database import init_db; init_db()"
```

## Running the Application

1. Start the FastAPI backend:
```bash
uvicorn app:app --reload
```

2. In a new terminal, start the Streamlit frontend:
```bash
streamlit run streamlit_app.py
```

3. Access the application:
- Frontend: http://localhost:8501
- API documentation: http://localhost:8000/docs

## Project Structure

- `app.py`: FastAPI backend application
- `database.py`: Database models and utilities
- `simple_chatbot.py`: LangGraph chatbot implementation
- `streamlit_app.py`: Streamlit frontend interface
- `requirements.txt`: Project dependencies

## API Endpoints

- POST `/chat/`: Send a message to the chatbot
- GET `/chat_history/`: Retrieve chat history

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 