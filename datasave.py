import praw
from pymongo import MongoClient
from transformers import pipeline
import logging
from datetime import datetime

# --- Configuration Section ---
REDDIT_CLIENT_ID = "FPi02ocg4HRZCOdu_CH3Xg"
REDDIT_CLIENT_SECRET = "xVncQKK1nhzCERw-GFBhkmWKeEY_9A"
REDDIT_USER_AGENT = "RedditNewsSummarizer"
REDDIT_USERNAME = "Shady-General-6233"
REDDIT_PASSWORD = "Edwin282869"

# Subreddit and Fetch Limit
SUBREDDIT_NAME = "news"  # Example: "worldnews", "technology", "sports"
POST_LIMIT = 5          # Number of top posts to fetch
COMMENT_LIMIT_PER_POST = 10 # Number of top comments to fetch per post

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialize Models ---
try:
    logging.info("Loading summarization model...")
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    logging.info("Summarization model loaded.")

    logging.info("Loading sentiment analysis model...")
    sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    logging.info("Sentiment analysis model loaded.")
except Exception as e:
    logging.error(f"Error loading models: {e}. Please ensure you have an active internet connection or download models locally.")
    exit(1)

# --- Initialize PRAW ---
try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD
    )
    logging.info("PRAW initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing PRAW: {e}. Check your Reddit API credentials.")
    exit(1)

# --- Initialize MongoDB ---
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["redigo_base"]
    collection = db["redigo1"]
    logging.info(f"Connected to MongoDB: Database '{db.name}', Collection '{collection.name}'.")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")
    exit(1)


# --- Function Definitions ---
def summarize_text(text: str, default_max_length: int = 150, default_min_length: int = 50) -> str:
    if not text:
        return ""

    text_words = text.strip().split()
    text_len_words = len(text_words)

    if text_len_words < default_min_length // 2:
        return text.strip()

    try:
        if len(text) > 10000:
            text = text[:10000]

        dynamic_max_length = min(max(int(text_len_words * 0.75), default_min_length), default_max_length)
        dynamic_min_length = min(max(int(text_len_words * 0.25), 10), dynamic_max_length - 5)

        if dynamic_min_length >= dynamic_max_length:
            dynamic_min_length = max(10, dynamic_max_length - 10)

        summary = summarizer(text, max_length=dynamic_max_length, min_length=dynamic_min_length, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        logging.warning(f"Error summarizing text: {e}. Returning original text for now. Text snippet: '{text[:100]}...'")
        return text

def analyze_comment_agreement(comments: list, post_title: str, post_selftext: str) -> dict:
    total_comments = len(comments)
    if total_comments == 0:
        return {
            "summary": "No comments to analyze.",
            "agreement_percentage": 0,
            "disagreement_percentage": 0,
            "neutral_percentage": 0,
            "comment_details": []
        }

    positive_count = 0
    negative_count = 0
    neutral_count = 0
    comment_summaries = []
    
    post_context = f"{post_title}. {post_selftext}" if post_selftext else post_title

    for comment in comments:
        comment_text = comment.body
        if not comment_text:
            continue
        
        comment_summary = summarize_text(comment_text, default_max_length=50, default_min_length=10)

        sentiment_score = None
        sentiment_label = "NEUTRAL"

        try:
            sentiment_result = sentiment_analyzer(comment_text[:512])
            sentiment_label = sentiment_result[0]['label']
            sentiment_score = sentiment_result[0]['score']

            if sentiment_label == "POSITIVE":
                positive_count += 1
            elif sentiment_label == "NEGATIVE":
                negative_count += 1
            else:
                neutral_count += 1
        except Exception as e:
            logging.warning(f"Error analyzing sentiment for comment: {e}. Comment snippet: '{comment_text[:50]}...'")
            neutral_count += 1 

        comment_summaries.append({
            "id": comment.id,
            "author": str(comment.author),
            "score": comment.score,
            "original_text_snippet": comment_text[:200] + "..." if len(comment_text) > 200 else comment_text,
            "summary": comment_summary,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score
        })

    agreement_percentage = (positive_count / total_comments) * 100 if total_comments > 0 else 0
    disagreement_percentage = (negative_count / total_comments) * 100 if total_comments > 0 else 0
    neutral_percentage = (neutral_count / total_comments) * 100 if total_comments > 0 else 0

    overall_comment_summary = f"Out of {total_comments} comments: {positive_count} positive, {negative_count} negative, {neutral_count} neutral. "

    if comment_summaries:
        top_comment_snippets = " ".join([c["summary"] for c in comment_summaries if c["summary"]][:5])
        overall_comment_summary += summarize_text(f"Key themes from comments: {top_comment_snippets}", default_max_length=100, default_min_length=20)
    else:
        overall_comment_summary += "No specific themes identified due to lack of comments."

    return {
        "summary": overall_comment_summary,
        "agreement_percentage": round(agreement_percentage, 2),
        "disagreement_percentage": round(disagreement_percentage, 2),
        "neutral_percentage": round(neutral_percentage, 2),
        "comment_details": comment_summaries
    }

def fetch_and_process_subreddit(subreddit_name: str, post_limit: int, comment_limit_per_post: int):
    logging.info(f"Fetching top {post_limit} posts from r/{subreddit_name}...")
    subreddit = reddit.subreddit(subreddit_name)
    processed_posts_count = 0

    for submission in subreddit.new(limit=post_limit):
        try:
            logging.info(f"Processing post: '{submission.title}' (ID: {submission.id})")

            if collection.find_one({"post_id": submission.id}):
                logging.info(f"Post '{submission.title}' (ID: {submission.id}) already exists in the database. Skipping.")
                continue
            
            post_text_to_summarize = f"{submission.title}. {submission.selftext}" if submission.selftext else submission.title
            post_summary = summarize_text(post_text_to_summarize)

            submission.comments.replace_more(limit=0) 
            comments = [comment for comment in submission.comments.list() if isinstance(comment, praw.models.Comment)][:comment_limit_per_post]
            logging.info(f"Fetched {len(comments)} comments for post '{submission.title}'.")

            comment_analysis_result = analyze_comment_agreement(comments, submission.title, submission.selftext)

            post_data = {
                "post_id": submission.id,
                "title": submission.title,
                "author": str(submission.author),
                "subreddit": submission.subreddit.display_name,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "url": submission.url,
                "created_utc": datetime.fromtimestamp(submission.created_utc),
                "post_summary": post_summary,
                "comments_summary": comment_analysis_result["summary"],
                "comment_agreement_percentage": comment_analysis_result["agreement_percentage"],
                "comment_disagreement_percentage": comment_analysis_result["disagreement_percentage"],
                "comment_neutral_percentage": comment_analysis_result["neutral_percentage"],
                "comment_details": comment_analysis_result["comment_details"],
                "processed_at": datetime.now()
            }

            collection.insert_one(post_data)
            logging.info(f"Successfully stored post '{submission.title}' in MongoDB.\n")
            processed_posts_count += 1

        except Exception as e:
            logging.error(f"Error processing post ID {submission.id} ('{submission.title}'): {e}", exc_info=True)
            continue

    logging.info(f"Finished processing. Total {processed_posts_count} posts processed and stored.")
    client.close()
    logging.info("MongoDB connection closed.")


# --- Main Execution Block ---
if __name__ == "__main__":
    if REDDIT_CLIENT_ID == "YOUR_REDDIT_CLIENT_ID":
        logging.error("Please update your Reddit API credentials in the configuration section at the top of the script before running.")
    else:
        fetch_and_process_subreddit(SUBREDDIT_NAME, POST_LIMIT, COMMENT_LIMIT_PER_POST)