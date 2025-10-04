import sqlite3
import json
from typing import Optional, List, Dict, Any
import threading


class ReviewDatabase:
    def __init__(self, db_path: str = "reviews.db"):
        """Initialize the database connection and create table if it doesn't exist."""
        self.db_path = db_path
        self._local = threading.local()
        # Create the table using a temporary connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                rating INTEGER NOT NULL,
                date TEXT NOT NULL,
                text TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                topics TEXT NOT NULL,
                suggested_reply TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def add_review(self, review: Dict[str, Any]) -> bool:
        """
        Add a new review to the database.
        
        Args:
            review: Dictionary containing id, location, rating, date, text, sentiment, and topics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert topics list to JSON string for storage
            topics_json = json.dumps(review['topics'])
            
            cursor.execute('''
                INSERT INTO reviews (id, location, rating, date, text, sentiment, topics, suggested_reply)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            ''', (
                review['id'],
                review['location'],
                review['rating'],
                review['date'],
                review['text'],
                review['sentiment'],
                topics_json
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Review with id '{review['id']}' already exists.")
            return False
        except Exception as e:
            print(f"Error adding review: {e}")
            return False

    def add_reviews_batch(self, reviews: List[Dict[str, Any]]) -> bool:
        """
        Add multiple reviews to the database in a single transaction.
        Much more efficient than individual inserts.
        
        Args:
            reviews: List of dictionaries, each containing id, location, rating, date, 
                    text, sentiment, and topics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Prepare data for batch insert
            review_data = [
                (
                    review['id'],
                    review['location'],
                    review['rating'],
                    review['date'],
                    review['text'],
                    review['sentiment'],
                    json.dumps(review['topics'])
                )
                for review in reviews
            ]
            
            # Execute batch insert with executemany
            cursor.executemany('''
                INSERT INTO reviews (id, location, rating, date, text, sentiment, topics, suggested_reply)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            ''', review_data)
            
            conn.commit()
            print(f"Successfully inserted {len(reviews)} reviews in batch")
            return True
        except sqlite3.IntegrityError as e:
            conn.rollback()
            print(f"Integrity error during batch insert (duplicate review ID): {e}")
            return False
        except Exception as e:
            conn.rollback()
            print(f"Error during batch insert: {e}")
            return False
    
    def add_suggested_reply(self, review_id: str, suggested_reply: str) -> bool:
        """
        Add a suggested reply to an existing review.
        
        Args:
            review_id: The ID of the review to update
            suggested_reply: The suggested reply text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE reviews
                SET suggested_reply = ?
                WHERE id = ?
            ''', (suggested_reply, review_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                print(f"No review found with id '{review_id}'.")
                return False
            return True
        except Exception as e:
            print(f"Error adding suggested reply: {e}")
            return False
    
    def get_all_reviews_as_json(self) -> str:
        """
        Extract the entire database as JSON.
        
        Returns:
            JSON string containing all reviews
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM reviews')
            rows = cursor.fetchall()
            
            reviews = []
            for row in rows:
                review = {
                    'id': row['id'],
                    'location': row['location'],
                    'rating': row['rating'],
                    'date': row['date'],
                    'text': row['text'],
                    'sentiment': row['sentiment'],
                    'topics': json.loads(row['topics']),
                }
                # Only include suggested_reply if it exists
                if row['suggested_reply']:
                    review['suggested_reply'] = row['suggested_reply']
                
                reviews.append(review)
            
            return json.dumps(reviews, indent=2)
        except Exception as e:
            print(f"Error extracting reviews: {e}")
            return "[]"
    
    def get_suggested_reply(self, review_id: str) -> Optional[str]:
        """
        Get the suggested reply for a specific review by ID.
        
        Args:
            review_id: The ID of the review
            
        Returns:
            The suggested reply text if it exists, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT suggested_reply FROM reviews
                WHERE id = ?
            ''', (review_id,))
            
            row = cursor.fetchone()
            if row and row['suggested_reply']:
                return row['suggested_reply']
            return None
        except Exception as e:
            print(f"Error retrieving suggested reply: {e}")
            return None

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete review by ID.
        
        Args:
            review_id: The ID of the review
            
        Returns:
            Dictionary containing all review information if found, None otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM reviews
                WHERE id = ?
            ''', (review_id,))
            
            row = cursor.fetchone()
            if row:
                review = {
                    'id': row['id'],
                    'location': row['location'],
                    'rating': row['rating'],
                    'date': row['date'],
                    'text': row['text'],
                    'sentiment': row['sentiment'],
                    'topics': json.loads(row['topics']),
                }
                # Only include suggested_reply if it exists
                if row['suggested_reply']:
                    review['suggested_reply'] = row['suggested_reply']
                
                return review
            return None
        except Exception as e:
            print(f"Error retrieving review: {e}")
            return None
    
    def close(self):
        """Close the database connection."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the connection."""
        self.close()