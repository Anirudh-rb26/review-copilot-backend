import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    print("=" * 50)
    print("Testing Root Endpoint")
    print("=" * 50)
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_ingest_review():
    print("=" * 50)
    print("Testing Ingest Review (Positive)")
    print("=" * 50)
    review_data = {
        "id": "rev001",
        "location": "New York",
        "rating": 5,
        "date": "2025-10-04",
        "text": "Excellent service! The team was very professional and efficient. They completed the work on time and the quality was outstanding."
    }
    response = requests.post(f"{BASE_URL}/ingest", json=review_data)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_ingest_negative_review():
    print("=" * 50)
    print("Testing Ingest Review (Negative)")
    print("=" * 50)
    review_data = {
        "id": "rev002",
        "location": "Los Angeles",
        "rating": 2,
        "date": "2025-10-03",
        "text": "Very disappointed with the service. The staff was unprofessional and the work was delayed by several days. Poor communication throughout."
    }
    response = requests.post(f"{BASE_URL}/ingest", json=review_data)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_get_all_reviews():
    print("=" * 50)
    print("Testing Get All Reviews")
    print("=" * 50)
    response = requests.get(f"{BASE_URL}/all-reviews")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_generate_reply(review_id):
    print("=" * 50)
    print(f"Testing Generate Reply for {review_id}")
    print("=" * 50)
    reply_data = {"review_id": review_id}
    response = requests.post(f"{BASE_URL}/generate-reply", json=reply_data)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_get_reply(review_id):
    print("=" * 50)
    print(f"Testing Get Stored Reply for {review_id}")
    print("=" * 50)
    response = requests.get(f"{BASE_URL}/reply/{review_id}")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def main():
    print("\n" + "=" * 50)
    print("REVIEW MANAGEMENT API - TESTING SUITE")
    print("=" * 50 + "\n")
    
    try:
        # Test 1: Root endpoint
        test_root()
        
        # Test 2: Ingest positive review
        test_ingest_review()
        
        # Test 3: Ingest negative review
        test_ingest_negative_review()
        
        # Test 4: Get all reviews
        test_get_all_reviews()
        
        # Test 5: Generate reply for positive review
        test_generate_reply("rev001")
        
        # Test 6: Generate reply for negative review
        test_generate_reply("rev002")
        
        # Test 7: Get stored replies
        test_get_reply("rev001")
        test_get_reply("rev002")
        
        print("=" * 50)
        print("ALL TESTS COMPLETED!")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API.")
        print("Make sure the API is running on http://localhost:8000")
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    main()