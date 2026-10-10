import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load variables from the .env file
load_dotenv()

# Create the Groq LLM
groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
llm = ChatGroq(
    model=groq_model,
    temperature=0
)