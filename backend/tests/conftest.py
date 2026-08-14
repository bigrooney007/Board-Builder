import os

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
if "REACT_APP_BACKEND_URL" not in os.environ:
    load_dotenv("/app/frontend/.env")
