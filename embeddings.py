from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

env_path = Path(__file__).resolve().parent/ ".env"
load_dotenv(dotenv_path = env_path,override= True)

def get_embeddings(text: str) -> list[float]:
    """convert nonempty text into a 1536-dimensional vector."""
    if not text.strip():
        raise ValueError("Text must be nonempty.")

    client = OpenAI()

    response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = text
    )
    return response.data[0].embedding


if __name__ == "__main__":
    vector = get_embeddings("check whether the divisor is zero before dividing")

    print("Dimensions",len(vector))
    print("First five values",vector[:5])