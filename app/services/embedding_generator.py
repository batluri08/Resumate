"""
Embedding generation using Sentence Transformers (Hugging Face)
"""

from sentence_transformers import SentenceTransformer

# Load model (can be swapped for OpenAI later)
model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text: str) -> list:
    """Generate embedding for input text"""
    embedding = model.encode(text, convert_to_numpy=True).tolist()
    return embedding
