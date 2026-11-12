from google import genai
from google.genai import types
from app.core.config import settings
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_gemini_client() -> genai.Client:
    """Create and return a Gemini API client with the API key from settings."""
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set in environment. Gemini service will not work.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)

def generate_chat_response(prompt: str) -> str:
    """
    Generate a response from Gemini given a prompt.
    Returns the generated text or raises an exception on API errors.
    """
    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise

def build_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Build a prompt for the LLM that includes the question and retrieved chunks.
    Each chunk is labeled with a source number and its bookmark title.
    The model is instructed to cite sources by number and to say it doesn't know when context is insufficient.
    """
    if not chunks:
        return f"Question: {question}\n\nNo relevant context found. Please respond that you don't have enough information to answer."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        title = chunk.get('bookmark_title', 'Unknown Title')
        text = chunk.get('text') or chunk.get('chunk', '')
        context_parts.append(f"[Source {i}: {title}]\n{text}")

    context_str = "\n\n".join(context_parts)
    prompt = f"""You are a helpful assistant that answers questions based only on the provided context.
If the context does not contain enough information to answer the question, say "I don't have enough information to answer that question."
Do not fabricate answers. Cite your sources by their source number in square brackets, e.g., [1], [2].

Context:
{context_str}

Question: {question}

Answer:"""
    return prompt
