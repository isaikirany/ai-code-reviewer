import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


env_path = Path(__file__).resolve().parent/".env"
load_dotenv(dotenv_path = env_path,override=True)

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY must be set in the environment variables.")


with OpenAI(api_key=api_key) as client:
    response = client.responses.create(
        model="gpt-4o-mini",
        input="Hello, OpenAI! Can you confirm that the connection is working?",
        max_output_tokens=100
    )


    print(response.output_text)