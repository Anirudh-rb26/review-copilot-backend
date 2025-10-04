import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def find_similar_reviews(review_id, db, reviews_db):
    """
    Find the 2 most similar reviews to a given review using TF-IDF and cosine similarity.
    
    Args:
        review_id: The ID of the review to find similar reviews for
        db: Database instance
        reviews_db: In-memory reviews list
    
    Returns:
        List of 2 review IDs of the most similar reviews
    """
    # Get all reviews (try database first, fallback to memory)
    try:
        reviews_json = db.get_all_reviews_as_json()
        all_reviews = json.loads(reviews_json)
        if not all_reviews:
            all_reviews = reviews_db
    except Exception:
        all_reviews = reviews_db
    
    if len(all_reviews) < 2:
        return []
    
    review_texts = []
    review_ids = []
    target_idx = None
    
    for idx, review in enumerate(all_reviews):
        review_ids.append(review['id'])
        text = review.get('text', '')
        review_texts.append(text)
        
        if review['id'] == review_id:
            target_idx = idx
    
    if target_idx is None:
        raise ValueError(f"Review with ID {review_id} not found")
    
    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_features=5000,
        ngram_range=(1, 2)
    )
    tfidf_matrix = vectorizer.fit_transform(review_texts)
    
    target_vector = tfidf_matrix[target_idx]
    similarities = cosine_similarity(target_vector, tfidf_matrix).flatten()
    
    similarities[target_idx] = -1
    
    num_similar = min(2, len(all_reviews) - 1)
    similar_indices = np.argsort(similarities)[-num_similar:][::-1]
    
    similar_review_ids = [review_ids[idx] for idx in similar_indices]
    
    return similar_review_ids