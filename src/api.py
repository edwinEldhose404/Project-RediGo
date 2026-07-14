"""HTTP API for RediGo's Reddit processing pipeline."""

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .reddit_summarizer import collection, fetch_and_process_subreddit

app = FastAPI(title="RediGo API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefreshRequest(BaseModel):
    subreddit: str = Field(default="worldnews", min_length=1, max_length=100)
    post_limit: int = Field(default=5, ge=1, le=25)
    comment_limit_per_post: int = Field(default=10, ge=0, le=50)
    sort: Literal["hot", "new", "top", "rising"] = "hot"


SORT_TYPES = {"hot": 1, "new": 2, "top": 3, "rising": 4}


def serialize_post(post: dict) -> dict:
    """Return browser-facing post data in a JSON-safe shape."""
    return jsonable_encoder({
        "id": str(post.get("_id", "")), "post_id": post.get("post_id"),
        "title": post.get("title"), "author": post.get("author"),
        "subreddit": post.get("subreddit"), "score": post.get("score", 0),
        "num_comments": post.get("num_comments", 0), "url": post.get("url"),
        "created_utc": post.get("created_utc"), "post_summary": post.get("post_summary", ""),
        "comments_summary": post.get("comments_summary", ""),
        "comment_agreement_percentage": post.get("comment_agreement_percentage", 0),
        "comment_disagreement_percentage": post.get("comment_disagreement_percentage", 0),
        "comment_neutral_percentage": post.get("comment_neutral_percentage", 0),
        "processed_at": post.get("processed_at"),
    })


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database_connected": collection is not None}


@app.get("/api/posts")
def list_posts(page: int = 1, limit: int = 10) -> dict:
    if collection is None:
        raise HTTPException(status_code=503, detail="MongoDB is not available")

    safe_page = max(1, page)
    safe_limit = max(1, min(limit, 10))
    total = collection.count_documents({})
    posts = collection.find().sort("created_utc", -1).skip((safe_page - 1) * safe_limit).limit(safe_limit)
    return {
        "posts": [serialize_post(post) for post in posts],
        "total": total,
        "page": safe_page,
        "page_size": safe_limit,
    }


@app.post("/api/refresh")
def refresh_posts(request: RefreshRequest) -> dict:
    if collection is None:
        raise HTTPException(status_code=503, detail="MongoDB is not available")
    processed = fetch_and_process_subreddit(
        request.subreddit, request.post_limit, request.comment_limit_per_post, SORT_TYPES[request.sort]
    )
    return {"processed_count": len(processed), "processed_at": datetime.now(),
            "posts": [serialize_post(post) for post in processed]}
