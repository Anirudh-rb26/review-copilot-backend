import os
from google import genai

class GenerateReviewReply:
    def __init__(self, api_key: str | None = None):
        # If api_key is None, the client library should pick up from GEMINI_API_KEY env var
        self.client = genai.Client(api_key=api_key)

    def generate_reply(self, review_text: str) -> str:
        prompt = f"""
You are a professional customer service agent responding to customer feedback or reviews.
Your response should:
- Acknowledge and thank them for their feedback,
- Address their concern or dissatisfaction,
- Offer to help or request more info (or escalation) if needed,
- If it's serious, ask them to contact support at customerservice@email.com.
- Sound human, polite, empathic, and professional.

Customer’s review: "{review_text}"
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                # optionally provide config to tweak thinking / latency etc
                # config=some_ThinkingConfig(...)  
            )
        except Exception as e:
            # Fallback / error-handling
            # You could log the error, rethrow, or return a generic reply
            return (
                "Thank you for your feedback. "
                "We encountered a technical issue while generating a reply, "
                "but we value your concern. Please reach out to us at customerservice@email.com, "
                "and we’ll be glad to assist you."
            )

        # Extract text
        # The response object should have .text (according to examples), but this depends on your version
        reply_text = getattr(response, "text", None)
        if reply_text is None:
            # fallback: try alternate attribute
            try:
                # e.g. response.candidates[0].text or something
                reply_text = response.candidates[0].text  # or variant
            except Exception:
                reply_text = (
                    "Thank you for your message. We'll get back to you via support soon."
                )

        return reply_text
