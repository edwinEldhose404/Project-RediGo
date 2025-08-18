import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'


import reddit_summarizer


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# %%
app = FastAPI(
    title="Reddit News Summarizer API",
    description="API for fetching, summarizing, and analyzing Reddit news posts and comments.",
    version="1.0.0"
)

# %%
# -*- coding: utf-8 -*-
"""
FastAPI Backend for Reddit News Summarizer

This script sets up a FastAPI application to expose an API endpoint
for the Reddit News Summarizer. It allows the frontend to request
summaries of Reddit posts and comments.

To run this application:
1. Ensure your `reddit_summarizer.py` is in the same directory.
2. Run: uvicorn app:app --reload --port 5000

Dependencies:
- fastapi: The web framework.
- uvicorn: ASGI server to run FastAPI.
- pydantic: For data validation (comes with fastapi).
- starlette.middleware.cors: For handling Cross-Origin Resource Sharing.
"""


# Import the main processing function from your existing script
# Make sure reddit_summarizer.py is in the same directory or accessible via PYTHONPATH
try:
    from reddit_summarizer import fetch_and_process_subreddit, collection
    logging.info("Successfully imported fetch_and_process_subreddit and collection from reddit_summarizer.py")
except ImportError as e:
    logging.error(f"Error importing from reddit_summarizer.py: {e}. Make sure the file exists and is correctly named.")
    # Exit or handle gracefully if the core logic cannot be imported
    exit(1)

app = FastAPI(
    title="Reddit News Summarizer API",
    description="API for fetching, summarizing, and analyzing Reddit news posts and comments.",
    version="1.0.0"
)

# Configure CORS to allow requests from your frontend (e.g., when running index.html directly)
# Adjust origins as necessary for your deployment environment
origins = [
    "http://localhost",
    "http://localhost:8000", # Default for Python's http.server
    "http://127.0.0.1:5500", # Common for Live Server VS Code extension
    "null", # For local file access (file:// protocol)
    "*" # WARNING: Use "*" only for development. For production, specify exact origins.
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
        # Call the function from reddit_summarizer.py
        # IMPORTANT: We need to modify fetch_and_process_subreddit to *return* the data
        # it processes, instead of just inserting it. This allows FastAPI to send it back.
        # For now, this will just trigger the processing and you'll need to query
        # the database for the results.
        # A more direct approach is to refactor fetch_and_process_subreddit
        # to return the list of processed post dictionaries.

        # Example of how you *would* return data if fetch_and_process_subreddit was refactored:
        # processed_posts = fetch_and_process_subreddit(subreddit, post_limit, comment_limit)
        # return {"message": "Summarization complete", "data": processed_posts}

        # Current implementation: Trigger processing and then fetch recent data
        # This assumes fetch_and_process_subreddit stores data immediately.
        # For a real-time display, this might not be ideal as it fetches *all* recent,
        # not just the ones from this specific run.
        fetch_and_process_subreddit(subreddit, post_limit, comment_limit)

        # Fetch the most recent posts from the database that match the subreddit
        # This is a heuristic. For precise results, fetch_and_process_subreddit should return them.
        recent_posts_cursor = collection.find(
            {"subreddit": subreddit}
        ).sort("processed_at", -1).limit(post_limit) # Sort by processed_at to get the most recent

        # Convert MongoDB cursor to a list of dictionaries, handling ObjectId and datetime
        processed_posts = []
        for post in recent_posts_cursor:
            # Convert ObjectId to string
            post['_id'] = str(post['_id'])
            # Convert datetime objects to ISO format strings for JSON serialization
            if 'created_utc' in post and isinstance(post['created_utc'], datetime):
                post['created_utc'] = post['created_utc'].isoformat()
            if 'processed_at' in post and isinstance(post['processed_at'], datetime):
                post['processed_at'] = post['processed_at'].isoformat()
            processed_posts.append(post)

        if not processed_posts:
            logging.warning(f"No posts found in DB after processing for subreddit: {subreddit}")
            return {"message": "No new posts summarized or found in the database for the given criteria.", "data": []}

        return {"message": "Summarization complete", "data": processed_posts}

    except Exception as e:
        logging.error(f"Error during summarization process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")




