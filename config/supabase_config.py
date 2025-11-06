"""
Supabase client configuration
This file sets up the connection to your Supabase database
"""

from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

def get_supabase_client() -> Client:

    # Get credentials from environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. "
            "Please set SUPABASE_URL and SUPABASE_KEY in your .env file"
        )

    client = create_client(supabase_url, supabase_key)
    return client
