import os
# LOADING VARIABLES
from dotenv import load_dotenv
load_dotenv()

from voice_studio_stack.logger.logging_tool import get_logger
logger = get_logger()

# REDIS_HOST = os.getenv("REDIS_HOST", "redis") # Default to "redis" for Docker container
REDIS_HOST = os.getenv("REDIS_HOST", "localhost") # Default to "localhost" for local development
REDIS_PORT = os.getenv("REDIS_PORT", "6379"
REDIS_DB = os.getenv("RED
def get_redis_url():
    logger.debug(f"Using Redis URL: redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    return f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"