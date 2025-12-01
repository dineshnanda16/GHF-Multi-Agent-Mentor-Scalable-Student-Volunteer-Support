# logging_config.py
import logging

def setup_logging():
    """Configure logging for the app"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
