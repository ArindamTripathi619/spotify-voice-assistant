import os
import logging
from dotenv import load_dotenv

def load_environment():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../env/.env'))
    logging.info("Environment variables loaded.")
