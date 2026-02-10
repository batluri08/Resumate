"""
ChromaDB Vector Store Integration for RestlessResume
"""

import chromadb
from chromadb.config import Settings

# Initialize ChromaDB client
chroma_client = chromadb.Client(Settings(
    persist_directory=".chromadb"
))

# Collection for resume/job vectors
collection = chroma_client.get_or_create_collection("resume_job_vectors")


def add_vector(id: str, embedding: list, metadata: dict = None):
    """Add a vector to ChromaDB collection"""
    collection.add(
        ids=[id],
        embeddings=[embedding],
        metadatas=[metadata] if metadata else None
    )


def query_vector(query_embedding: list, n_results: int = 5):
    """Query ChromaDB for similar vectors"""
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )


def delete_vector(id: str):
    """Delete a vector from ChromaDB collection"""
    collection.delete(ids=[id])
