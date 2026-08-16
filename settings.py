import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "None")
    EXTRACTION_MODEL: str = os.getenv("EXTRACTION_MODEL", "gpt-4o")
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gpt-4o")

settings = Settings()