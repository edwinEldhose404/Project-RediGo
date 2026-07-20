# Project RediGo

Project RediGo is a Python-based Reddit data collection and analysis pipeline that automatically fetches posts from Reddit, summarizes discussions using Google's Generative AI models, performs sentiment analysis on comments using Hugging Face Transformers, and stores the processed results in MongoDB Atlas. The project is designed to run automatically using GitHub Actions.

---

## Features

- Fetch posts from any subreddit using the Reddit API (PRAW)
- Support multiple sorting methods:
  - Hot
  - New
  - Top
  - Rising
- Generate AI summaries for Reddit posts
- Generate AI summaries for combined top comments
- Perform sentiment analysis using DistilBERT
- Calculate agreement, disagreement, and neutral percentages from comment sentiment
- Store processed data in MongoDB Atlas
- Prevent duplicate posts from being stored
- Automate daily execution using GitHub Actions
- Secure API credentials using GitHub Secrets

---

## Technologies Used

- Python 3.12
- PRAW (Python Reddit API Wrapper)
- Google Generative AI (Gemma/Gemini)
- Hugging Face Transformers
- PyTorch
- MongoDB Atlas
- PyMongo
- GitHub Actions
- python-dotenv

---

## Project Structure

```text
Project-RediGo/
│
├── .github/
│   └── workflows/
│       └── reddit-fetch.yml
│
├── src/
│   ├── __init__.py
│   ├── api.py
│   └── reddit_summarizer.py
│
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## Data Stored

Each processed Reddit post contains the following information:

```json
{
  "post_id": "",
  "title": "",
  "author": "",
  "subreddit": "",
  "score": 0,
  "num_comments": 0,
  "url": "",
  "created_utc": "",
  "post_summary": "",
  "comments_summary": "",
  "comment_agreement_percentage": 0,
  "comment_disagreement_percentage": 0,
  "comment_neutral_percentage": 0,
  "comment_details": [],
  "processed_at": ""
}
```

---

## Processing Workflow

```text
Reddit
   │
   ▼
Fetch Posts
   │
   ▼
Remove Stickied Posts
   │
   ▼
Skip Duplicate Posts
   │
   ▼
Generate Post Summary
   │
   ▼
Fetch Top Comments
   │
   ▼
Perform Sentiment Analysis
   │
   ▼
Generate Comment Summary
   │
   ▼
Store Processed Data in MongoDB Atlas
```


## Author

**Edwin Eldhose**
