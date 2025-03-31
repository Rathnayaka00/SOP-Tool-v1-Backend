from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import numpy as np
from typing import List, Tuple
from app.database import db

async def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return float(similarity)

async def find_similar_sops(topic_embedding: List[float], description_embedding: List[float], threshold: float = 0.6) -> List[Tuple[str, float]]:
    embeddings = await db.embeddings.find({}).to_list(None)
    
    similar_sops = []
    for doc in embeddings:
        topic_similarity = await calculate_similarity(topic_embedding, doc["topic_embedding"])
        desc_similarity = await calculate_similarity(description_embedding, doc["summary_embedding"])
        weighted_similarity = (0.4 * topic_similarity) + (0.6 * desc_similarity)
        
        if weighted_similarity >= threshold:
            similar_sops.append((doc["sop_id"], weighted_similarity))
    
    similar_sops.sort(key=lambda x: x[1], reverse=True)
    return similar_sops 