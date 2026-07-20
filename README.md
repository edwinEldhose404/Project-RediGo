Project RediGo

A Python-based Reddit data collection and analysis pipeline that automatically fetches posts from Reddit, summarizes discussions using Google's Generative AI models, performs sentiment analysis on comments using Hugging Face Transformers, and stores the processed results in MongoDB Atlas. The project is designed to run automatically using GitHub Actions.

Features
Fetches posts from any Reddit subreddit using the Reddit API (PRAW)
Supports multiple post sorting methods:
Hot
New
Top
Rising
Generates AI summaries of Reddit posts
Generates AI summaries of combined top comments
Performs sentiment analysis on comments using DistilBERT
Calculates:
Agreement percentage
Disagreement percentage
Neutral percentage
Stores processed data in MongoDB Atlas
Prevents duplicate posts from being inserted
Automatically runs every day using GitHub Actions
Securely stores API credentials using GitHub Secrets
Technologies Used
Python 3.12
PRAW (Python Reddit API Wrapper)
Google Generative AI (Gemma/Gemini)
Hugging Face Transformers
PyTorch
MongoDB Atlas
PyMongo
GitHub Actions
Python Dotenv
Project Structure
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
Installation

Clone the repository:

git clone https://github.com/<your-username>/Project-RediGo.git

cd Project-RediGo

Create a virtual environment:

Windows
python -m venv venv

venv\Scripts\activate
Linux/macOS
python3 -m venv venv

source venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Environment Variables

Create a .env file in the project root.

REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=your_user_agent

GEMINI_API_KEY=your_api_key

MONGO_URI=your_mongodb_connection_string
Running the Project

Execute:

python src/reddit_summarizer.py
GitHub Actions Automation

The project is configured to execute automatically every day using GitHub Actions.

Required repository secrets:

REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT

GEMINI_API_KEY

MONGO_URI

Workflow file:

.github/workflows/reddit-fetch.yml

The workflow:

Checks out the repository
Sets up Python
Installs dependencies
Restores dependency cache
Restores Hugging Face model cache
Executes the Reddit summarizer
Stores processed data in MongoDB Atlas
Data Stored

Each processed Reddit post contains:

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
Workflow
Reddit
   │
   ▼
Fetch Posts
   │
   ▼
Skip Stickied/Duplicate Posts
   │
   ▼
Generate Post Summary
   │
   ▼
Fetch Top Comments
   │
   ▼
Sentiment Analysis
   │
   ▼
Generate Comment Summary
   │
   ▼
Store in MongoDB Atlas
Future Improvements
Support multiple subreddits in a single execution
Topic modeling and keyword extraction
Trend analysis across time
REST API for querying stored data
Interactive dashboard for analytics
Visualization of subreddit sentiment trends
Multi-language support
Automatic report generation
License

This project is intended for educational purposes.

Author

Edwin Eldhose
