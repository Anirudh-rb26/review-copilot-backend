import os
import re
import nltk
import json
from datetime import datetime
from typing import Union, List
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional
from database import ReviewDatabase
from fastapi import FastAPI, HTTPException
from ai_services import GenerateReviewReply
from fastapi.middleware.cors import CORSMiddleware
from nltk.sentiment import SentimentIntensityAnalyzer

# Load environment variables from .env file
load_dotenv()

# Download required NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

app = FastAPI(title="Review Management API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "http://192.168.0.82:3000",
        "https://review-copilot-frontend.vercel.app",
        "https://review-copilot-frontend-git-main-anirudh-jayakumars-projects.vercel.app",
        "https://review-copilot-frontend-166lyy83x-anirudh-jayakumars-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

# In-memory storage for reviews
reviews_db = []

# Initialize database connection
db = ReviewDatabase()

# Initialize AI reply generator
api_key = os.getenv("GEMINI_API_KEY")
reply_generator = GenerateReviewReply(api_key=api_key)

# Topic keyword dictionary
TOPIC_KEYWORDS = {
    "professionalism": ["professional", "professionalism", "expert", "expertise", "skilled", "competent"],
    "efficiency": ["efficient", "efficiency", "quick", "fast", "timely", "prompt", "speedy"],
    "quality": ["quality", "excellent", "perfect", "great", "outstanding", "superb", "top-notch"],
    "customer_service": ["service", "helpful", "friendly", "courteous", "attentive", "responsive"],
    "communication": ["communication", "communicate", "informed", "updates", "clear", "transparent"],
    "timeliness": ["on time", "punctual", "deadline", "schedule", "timely"],
    "price": ["price", "cost", "expensive", "cheap", "affordable", "value", "worth"],
    "cleanliness": ["clean", "cleanliness", "tidy", "neat", "spotless", "organized"],
    "reliability": ["reliable", "dependable", "trustworthy", "consistent", "trust"],
    "experience": ["experience", "knowledgeable", "seasoned", "veteran"],
}


class ReviewInput(BaseModel):
    id: str
    location: str
    rating: int
    date: str
    text: str
    

class ReviewOutput(BaseModel):
    id: str
    location: str
    rating: int
    date: str
    text: str
    sentiment: str
    topics: List[str]


class GenerateReplyRequest(BaseModel):
    review_id: str


class GenerateReplyResponse(BaseModel):
    review_id: str
    review_text: str
    suggested_reply: str


def analyze_sentiment(text: str) -> str:
    """
    Analyze sentiment using NLTK's VADER sentiment analyzer.
    Returns: 'positive', 'negative', or 'neutral'
    """
    scores = sia.polarity_scores(text)
    compound = scores['compound']
    
    if compound >= 0.05:
        return "positive"
    elif compound <= -0.05:
        return "negative"
    else:
        return "neutral"


def extract_topics(text: str) -> List[str]:
    """
    Extract topics from review text using keyword matching.
    Returns: List of matched topics
    """
    text_lower = text.lower()
    matched_topics = []
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundaries to match whole words
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                matched_topics.append(topic)
                break  # Don't add the same topic multiple times
    
    return matched_topics if matched_topics else ["general"]


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Review Management API",
        "endpoints": ["/ingest", "/generate-reply", "/all-reviews", "/reply/{review_id}"],
        "total_reviews": len(reviews_db)
    }


@app.post("/ingest", response_model=Union[ReviewOutput, List[ReviewOutput]])
async def ingest_review(review: Union[ReviewInput, List[ReviewInput]]):
    """
    Ingest one or multiple reviews, analyze sentiment and extract topics.
    Accepts both a single review object or an array of review objects.
    """
    
    def process_single_review(review_data: ReviewInput):
        """Helper function to process a single review"""
        # Check if review ID already exists
        if any(r["id"] == review_data.id for r in reviews_db):
            raise HTTPException(
                status_code=400, 
                detail=f"Review with id {review_data.id} already exists"
            )
        
        # Analyze sentiment
        sentiment = analyze_sentiment(review_data.text)
        
        # Extract topics
        topics = extract_topics(review_data.text)
        
        # Create enriched review object
        enriched_review = {
            "id": review_data.id,
            "location": review_data.location,
            "rating": review_data.rating,
            "date": review_data.date,
            "text": review_data.text,
            "sentiment": sentiment,
            "topics": topics
        }
        
        return enriched_review
    
    # Handle both single review and list of reviews
    if isinstance(review, list):
        # Bulk processing
        enriched_reviews = []
        
        # Process all reviews first
        for review_item in review:
            enriched = process_single_review(review_item)
            enriched_reviews.append(enriched)
        
        # Batch add to in-memory database
        reviews_db.extend(enriched_reviews)
        
        # Batch add to SQLite database
        try:
            # If your db has a batch insert method, use it
            if hasattr(db, 'add_reviews_batch'):
                if not db.add_reviews_batch(enriched_reviews):
                    print("Warning: Failed to batch store reviews in database")
            else:
                # Fallback to individual inserts if batch method doesn't exist
                for enriched_review in enriched_reviews:
                    try:
                        if not db.add_review(enriched_review):
                            print(f"Warning: Failed to store review {enriched_review['id']} in database")
                    except Exception as e:
                        print(f"Database error for review {enriched_review['id']}: {e}")
        except Exception as e:
            print(f"Database batch error: {e}, continuing with in-memory storage")
        
        return enriched_reviews
    else:
        # Single review processing
        enriched_review = process_single_review(review)
        
        # Store in memory database
        reviews_db.append(enriched_review)
        
        # Store in SQLite database
        try:
            if not db.add_review(enriched_review):
                print("Warning: Failed to store review in database, continuing with in-memory storage")
        except Exception as e:
            print(f"Database error: {e}, continuing with in-memory storage")
        
        return enriched_review


@app.get("/all-reviews", response_model=List[ReviewOutput])
async def get_all_reviews():
    """
    Get all reviews from the database.
    """
    try:
        # Try to get from database first
        reviews_json = db.get_all_reviews_as_json()
        db_reviews = json.loads(reviews_json)
        
        # If database has reviews, return them
        if db_reviews:
            return db_reviews
    except Exception as e:
        print(f"Database error: {e}, falling back to in-memory storage")
    
    # Fallback to in-memory storage
    return reviews_db


import logging

logger = logging.getLogger(__name__)

@app.post("/generate-reply", response_model=GenerateReplyResponse)
async def generate_reply(request: GenerateReplyRequest):
    """
    Generate AI-powered reply suggestions for reviews.
    This calls the GenerateReviewReply class from ai_services.py
    If a reply already exists for this review, it returns the cached reply
    instead of generating a new one.
    """
    logger.info(f"Request received for review_id: {request.review_id}")
    
    # Find the review once (check memory first, then database)
    review = next((r for r in reviews_db if r["id"] == request.review_id), None)
    
    if review:
        logger.info(f"Review found in memory for id: {request.review_id}")
    
    if review is None:
        logger.info(f"Review not in memory, checking database for id: {request.review_id}")
        try:
            reviews_json = db.get_all_reviews_as_json()
            all_reviews = json.loads(reviews_json)
            review = next((r for r in all_reviews if r["id"] == request.review_id), None)
            if review:
                logger.info(f"Review found in database for id: {request.review_id}")
            else:
                logger.warning(f"Review not found in database for id: {request.review_id}")
        except Exception as e:
            logger.error(f"Database error while fetching review: {e}")
    
    if review is None:
        logger.error(f"Review with id {request.review_id} not found")
        raise HTTPException(status_code=404, detail=f"Review with id {request.review_id} not found")
    
    # Check if a reply already exists
    logger.info(f"Checking for existing reply for review_id: {request.review_id}")
    try:
        existing_reply = db.get_suggested_reply(request.review_id)
        if existing_reply:
            logger.info(f"Found existing reply for review_id: {request.review_id}, returning cached version")
            return GenerateReplyResponse(
                review_id=request.review_id,
                review_text=review["text"],
                suggested_reply=existing_reply
            )
        else:
            logger.info(f"No existing reply found for review_id: {request.review_id}, will generate new one")
    except Exception as e:
        logger.error(f"Error checking for existing reply: {e}")
    
    # Generate new reply using AI
    logger.info(f"Generating new AI reply for review_id: {request.review_id}")
    try:
        suggested_reply = reply_generator.generate_reply(review["text"])
        logger.info(f"Successfully generated AI reply for review_id: {request.review_id}")
        
        # Try to store the suggested reply in the database
        logger.info(f"Storing reply in database for review_id: {request.review_id}")
        try:
            db.add_suggested_reply(request.review_id, suggested_reply)
            logger.info(f"Successfully stored reply in database for review_id: {request.review_id}")
        except Exception as e:
            logger.error(f"Failed to store reply in database for review_id {request.review_id}: {e}")
        
        return GenerateReplyResponse(
            review_id=request.review_id,
            review_text=review["text"],
            suggested_reply=suggested_reply
        )
    except Exception as e:
        logger.error(f"Failed to generate reply for review_id {request.review_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate reply: {str(e)}"
        )

@app.get("/reply/{review_id}")
async def get_reply(review_id: str):
    """
    Get the stored suggested reply for a review.
    """
    try:
        reply = db.get_suggested_reply(review_id)
        if reply is None:
            raise HTTPException(status_code=404, detail=f"No reply found for review {review_id}")
        return {"review_id": review_id, "reply": reply}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)