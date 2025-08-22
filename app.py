import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import logging
from bson.objectid import ObjectId

# Import the main processing function and clients from your existing script
try:
    from reddit_summarizer import fetch_and_process_subreddit
    logging.info("Successfully imported fetch_and_process_subreddit from reddit_summarizer.py")
except ImportError as e:
    logging.error(f"Error importing from reddit_summarizer.py: {e}. Make sure the file exists.")
    exit(1)

app = FastAPI(
    title="Reddit News Summarizer API",
    description="API for fetching, summarizing, and analyzing Reddit news posts and comments.",
    version="1.0.0"
)

# Configure CORS to allow requests from your frontend
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "null", # Allows local file access (e.g., file:// protocol)
    # WARNING: Use "*" only for development. For production, specify exact origins.
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model for the /summarize endpoint
class SummarizeRequest(BaseModel):
    subreddit: str = "news"
    post_limit: int = 5
    comment_limit: int = 10

def prepare_post_data(posts: list):
    """
    Helper function to convert MongoDB data types for JSON serialization.
    """
    prepared_posts = []
    for post in posts:
        # Create a new dictionary to avoid modifying the original
        prepared_post = post.copy()
        # Convert ObjectId to string
        if '_id' in prepared_post and isinstance(prepared_post['_id'], ObjectId):
            prepared_post['_id'] = str(prepared_post['_id'])
        # Convert datetime objects to ISO format strings
        if 'created_utc' in prepared_post and isinstance(prepared_post['created_utc'], datetime):
            prepared_post['created_utc'] = prepared_post['created_utc'].isoformat()
        if 'processed_at' in prepared_post and isinstance(prepared_post['processed_at'], datetime):
            prepared_post['processed_at'] = prepared_post['processed_at'].isoformat()
        prepared_posts.append(prepared_post)
    return prepared_posts

@app.get("/")
async def read_root():
    """Root endpoint for the API."""
    return {"message": "Welcome to the Reddit News Summarizer API. Use /summarize to get data."}

@app.post("/summarize")
async def summarize_reddit_data(request_data: SummarizeRequest):
    """
    Endpoint to fetch, summarize, and store Reddit news data.
    Returns the processed data.
    """
    subreddit = request_data.subreddit
    post_limit = request_data.post_limit
    comment_limit = request_data.comment_limit

    logging.info(f"Received request to summarize: Subreddit='{subreddit}', Posts={post_limit}, Comments={comment_limit}")

    try:
        # Call the refactored function which now returns the data
        processed_posts = fetch_and_process_subreddit(subreddit, post_limit, comment_limit)

        if not processed_posts:
            logging.warning(f"No new posts found or processed for subreddit: {subreddit}")
            # Note: The frontend needs to handle this case gracefully.
            return {"message": "No new posts summarized or found in the database for the given criteria.", "data": []}
        
        # Prepare the list of dictionaries for JSON serialization
        prepared_data = prepare_post_data(processed_posts)

        return {"message": "Summarization complete", "data": prepared_data}

    except Exception as e:
        logging.error(f"Error during summarization process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")