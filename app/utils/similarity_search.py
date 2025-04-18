from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import numpy as np
from typing import List, Tuple
from app.database import db
from app.models.embedding import Embedding
from sklearn.metrics.pairwise import cosine_similarity

async def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return float(similarity)

async def find_similar_sops(topic_embedding: List[float], description_embedding: List[float], threshold: float = 0.6) -> List[Tuple[str, float]]:
    # Get all embeddings from the database
    embeddings = []
    async for doc in db.embeddings.find():
        embeddings.append(Embedding(**doc))
    
    if not embeddings:
        return []
    
    # Convert embeddings to numpy arrays
    topic_embeddings = np.array([e.topic_embedding for e in embeddings])
    description_embeddings = np.array([e.summary_embedding for e in embeddings])
    
    # Calculate similarities
    topic_similarities = cosine_similarity(
        np.array(topic_embedding).reshape(1, -1),
        topic_embeddings
    )[0]
    
    description_similarities = cosine_similarity(
        np.array(description_embedding).reshape(1, -1),
        description_embeddings
    )[0]
    
    # Combine similarities with weights
    combined_similarities = 0.6 * topic_similarities + 0.4 * description_similarities
    
    # Get version numbers for each SOP
    version_boost = []
    for embedding in embeddings:
        sop_doc = await db.sop_documents.find_one({"sop_id": embedding.sop_id})
        version = sop_doc.get("version", 1) if sop_doc else 1
        # Apply version boost: each version increases similarity by 5%
        version_boost.append(1.0 + (version - 1) * 0.05)
    
    # Apply version boost to similarities
    boosted_similarities = combined_similarities * np.array(version_boost)
    
    # Get SOP IDs and create tuples
    sop_ids = [e.sop_id for e in embeddings]
    results = list(zip(sop_ids, boosted_similarities))
    
    # Filter by threshold and sort by similarity
    filtered_results = [(sop_id, score) for sop_id, score in results if score >= threshold]
    filtered_results.sort(key=lambda x: x[1], reverse=True)
    
    return filtered_results 