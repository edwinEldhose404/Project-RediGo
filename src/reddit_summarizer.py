import praw
from pymongo import MongoClient
import logging
from datetime import datetime
from bson.objectid import ObjectId

from dotenv import load_dotenv
import os

#hide tensorflow warnings
import warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logging.getLogger("tensorflow").setLevel(logging.ERROR)


from transformers import pipeline
from google import genai


#load secret env variables
load_dotenv()

# Local Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemma-4-31b-it"

#initializing logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#load model
try:
    logging.info(f"Using Gemini model: {GEMINI_MODEL}")

    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english"
    )
    
except Exception as e:
    logging.error(f"Error loading models: {e}. Ensure you have an active internet connection or download models locally.")
    summarizer = None
    sentiment_analyzer = None

#initialize PRAW
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )
    logging.info("PRAW initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing PRAW: {e}. Check your Reddit API credentials.")
    reddit = None

#Initialize Mongo
try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client["redigo"]
    collection = db["redigo1"]
    # Force a connection check
    mongo_client.server_info()
    logging.info(f"Connected to MongoDB: Database '{db.name}', Collection '{collection.name}'.")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")
    mongo_client = None
    collection = None

#summarize text function
def summarize_text(text: str,
                   default_max_length: int = 150,
                   default_min_length: int = 50) -> str:

    if not text:
        return ""

    words = text.split()

    if len(words) < default_min_length // 2:
        return text.strip()

    try:

        prompt = f"""
You are summarizing Reddit discussions.

Write a concise summary.

Requirements:

- Mention only the important ideas.
- Merge similar opinions together.
- Ignore jokes and low-effort comments.
- Do not mention usernames.
- Do not say "Here is the summary."
- Return only the summary.
- Keep between {default_min_length} and {default_max_length} words.

TEXT:

{text}
"""

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:
        logging.warning(f"Gemini summarization failed: {e}")
        return text



#use sentiment analysis for checking comment agreement
def analyze_comment_agreement(comments: list, post_title: str, post_selftext: str) -> dict:
    total_comments = len(comments)
    if total_comments == 0:
        return {
            "summary": "No comments to analyze.",
            "agreement_percentage": 0.0,
            "disagreement_percentage": 0.0,
            "neutral_percentage": 0.0,
            "comment_details": []
        }
    
    if not sentiment_analyzer:
        logging.warning("Sentiment analysis model not loaded. Skipping analysis.")
        return {
            "summary": "Sentiment analysis unavailable.",
            "agreement_percentage": 0.0,
            "disagreement_percentage": 0.0,
            "neutral_percentage": 0.0,
            "comment_details": []
        }

    positive_count = 0
    negative_count = 0
    neutral_count = 0
    comment_summaries = []
    
    for comment in comments:
        comment_text = comment.body
        if not comment_text or comment_text == '[deleted]' or comment_text == '[removed]':
            continue
        
        
        try:
            # model has a max inpt length, so we truncate
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
            "original_text_snippet":
                comment_text[:500] if len(comment_text) > 500 else comment_text,
            "sentiment_label": sentiment_label,
            "sentiment_score": sentiment_score
        })

    total_analyzed_comments = positive_count + negative_count + neutral_count
    if total_analyzed_comments == 0:
        return {
            "summary": "No valid comments to analyze.",
            "agreement_percentage": 0.0,
            "disagreement_percentage": 0.0,
            "neutral_percentage": 0.0,
            "comment_details": []
        }

    agreement_percentage = (positive_count / total_analyzed_comments) * 100
    disagreement_percentage = (negative_count / total_analyzed_comments) * 100
    neutral_percentage = (neutral_count / total_analyzed_comments) * 100
    
    # make sure percentages r correct
    total_percentage = agreement_percentage + disagreement_percentage + neutral_percentage

    if abs(total_percentage - 100) > 0.01:
        if agreement_percentage > 0:
            agreement_percentage += (100 - total_percentage)
        elif disagreement_percentage > 0:
            disagreement_percentage += (100 - total_percentage)
        else:
            neutral_percentage += (100 - total_percentage)

    if comment_summaries:

        combined_comments = "\n\n".join(
            c["original_text_snippet"]
            for c in comment_summaries
        )

        overall_comment_summary = summarize_text(
            combined_comments,
            default_max_length=120,
            default_min_length=40,
        )

    else:
        overall_comment_summary = "No comments available."

    return {
        "summary": overall_comment_summary,
        "agreement_percentage": round(agreement_percentage, 2),
        "disagreement_percentage": round(disagreement_percentage, 2),
        "neutral_percentage": round(neutral_percentage, 2),
        "comment_details": comment_summaries
    }

#does what its called as well as storing the data
def fetch_and_process_subreddit(subreddit_name: str, post_limit: int, comment_limit_per_post: int, post_type: int):
    if not reddit or not mongo_client:
        logging.error("PRAW or MongoDB client not initialized. Cannot process request.")
        return []

    logging.info(f"Fetching top {post_limit} posts from r/{subreddit_name}...")
    try:
        #accounting for possible threads
        post_limit+=1

        #sorting type and default to hot
        subreddit = reddit.subreddit(subreddit_name)
        if post_type == 1:
            submissions = list(subreddit.hot(limit=post_limit))
        elif post_type == 2:
            submissions = list(subreddit.new(limit=post_limit))
        elif post_type == 3:
            submissions = list(subreddit.top(limit=post_limit))
        elif post_type == 4:
            submissions = list(subreddit.rising(limit=post_limit))
        else:
            submissions = list(subreddit.hot(limit=post_limit))
    except Exception as e:
        logging.error(f"Error fetching subreddit {subreddit_name}: {e}")
        return []

    processed_posts = []
    for submission in submissions:

        #ignore pinned posts which are 99% of the time threads
        if submission.stickied:
            continue

        try:
            logging.info(f"Processing post: '{submission.title}' (ID: {submission.id})")

            # Check if post already exists in the database
            if collection.find_one({"post_id": submission.id}):
                logging.info(f"Post '{submission.title}' (ID: {submission.id}) already exists in the database. Skipping.")
                continue

            # Summarize
            post_text_to_summarize = f"{submission.title}. {submission.selftext}" if submission.selftext else submission.title
            post_summary = summarize_text(post_text_to_summarize)

            # Fetch comments
            submission.comments.replace_more(limit=0)
            comments = [comment for comment in submission.comments.list() if isinstance(comment, praw.models.Comment)][:comment_limit_per_post]
            logging.info(f"Fetched {len(comments)} comments for post '{submission.title}'.")

            # Analyze comments
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
            logging.info(f"Successfully stored post '{submission.title}' in MongoDB.")

            processed_posts.append(post_data)

        except Exception as e:
            logging.error(f"Error processing post ID {submission.id} ('{submission.title}'): {e}", exc_info=True)
            continue

    logging.info(f"Finished processing. Total {len(processed_posts)} new posts processed and stored.")
    return processed_posts

#for testing obviously
#try todays top 5 popular posts from worldnews along with 10 top comments
#Fourth parameter - what sorting to use for top on posts
#Hot,New, Top, Rising -> 1,2,3,4 respectively
if __name__ == "__main__":
    results = fetch_and_process_subreddit("worldnews", 5, 10, 1)
    logging.info("Standalone run complete. Processed posts:")
    for post in results:
        print(f"Title: {post['title']}")
        print(f"Summary: {post['post_summary']}\n")
