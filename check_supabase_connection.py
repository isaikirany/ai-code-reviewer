import os
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent/".env"
print("Loading configuration from:", env_path)
load_dotenv(dotenv_path=env_path,override=True)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment variables.")

supabase = create_client(supabase_url,supabase_key)
print("supabase_url",repr(supabase_url))
result = supabase.table('rag_content').select("id").limit(1).execute()
print("supabase connection Succeeded. Rows returned:", result.data)
