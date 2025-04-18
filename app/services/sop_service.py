from app.utils.openai_helper import generate_sop
from app.utils.pdf_generator import create_pdf
from app.utils.openai_embeddings import get_embedding
from app.utils.similarity_search import find_similar_sops
from app.database import db
from app.models.embedding import Embedding
from app.models.sop import Task, SOPDocument, EditedSOPDetails
import uuid
import os
from datetime import datetime
import pytz
from typing import List, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from difflib import SequenceMatcher

# Get Sri Lankan timezone
sri_lanka_tz = pytz.timezone('Asia/Colombo')

def get_sri_lankan_time():
    return datetime.now(sri_lanka_tz)

async def create_sop(topic: str, description: str):
    topic_embedding = get_embedding(topic)
    description_embedding = get_embedding(description)
    
    sop_id = str(uuid.uuid4())

    sop_data = await generate_sop(topic, description)

    if not isinstance(sop_data, dict) or "details" not in sop_data or "summary" not in sop_data:
        raise ValueError("Invalid SOP response from OpenAI")

    pdf_path = create_pdf(sop_id, topic, sop_data["details"])

    # Create SOP document with Sri Lankan timezone
    current_time = get_sri_lankan_time()
    
    # Store in sops collection
    await db.sops.insert_one({
        "sop_id": sop_id,
        "topic": topic,
        "description": description,
        "details": sop_data["details"],
        "pdf_url": pdf_path
    })

    # Store in new sop_documents collection
    sop_document = SOPDocument(
        sop_id=sop_id,
        topic=topic,
        pdf_url=pdf_path,
        created_at=current_time
    )
    await db.sop_documents.insert_one(sop_document.dict())

    await db.summaries.insert_one({
        "topic_id": sop_id,
        "sop_id": sop_id,
        "summary": sop_data["summary"]
    })

    summary_embedding = get_embedding(sop_data["summary"])

    embedding_doc = Embedding(
        sop_id=sop_id,
        topic_embedding=topic_embedding,
        summary_embedding=summary_embedding
    )

    await db.embeddings.insert_one(embedding_doc.dict())

    return {
        "sop_id": sop_id,
        "message": "New SOP created successfully",
        "is_existing": False
    }

async def create_sop_direct(topic: str, description: str):
    topic_embedding = get_embedding(topic)
    description_embedding = get_embedding(description)
    
    sop_id = str(uuid.uuid4())

    sop_data = await generate_sop(topic, description)

    if not isinstance(sop_data, dict) or "details" not in sop_data or "summary" not in sop_data:
        raise ValueError("Invalid SOP response from OpenAI")

    pdf_path = create_pdf(sop_id, topic, sop_data["details"])

    # Create SOP document with Sri Lankan timezone
    current_time = get_sri_lankan_time()
    
    # Store in sops collection
    await db.sops.insert_one({
        "sop_id": sop_id,
        "topic": topic,
        "description": description,
        "details": sop_data["details"],
        "pdf_url": pdf_path
    })

    # Store in new sop_documents collection
    sop_document = SOPDocument(
        sop_id=sop_id,
        topic=topic,
        pdf_url=pdf_path,
        created_at=current_time
    )
    await db.sop_documents.insert_one(sop_document.dict())

    await db.summaries.insert_one({
        "topic_id": sop_id,
        "sop_id": sop_id,
        "summary": sop_data["summary"]
    })

    summary_embedding = get_embedding(sop_data["summary"])

    embedding_doc = Embedding(
        sop_id=sop_id,
        topic_embedding=topic_embedding,
        summary_embedding=summary_embedding
    )

    await db.embeddings.insert_one(embedding_doc.dict())

    return {
        "sop_id": sop_id,
        "message": "New SOP created successfully",
        "is_existing": False
    }


async def get_sop_pdf(sop_id: str):
    sop = await db.sops.find_one({"sop_id": sop_id})
    if not sop or "pdf_url" not in sop:
        raise ValueError("SOP not found or PDF not generated")
    
    pdf_path = sop["pdf_url"]
    if not os.path.exists(pdf_path):
        raise ValueError("PDF file not found")
    
    return pdf_path

async def get_sop_summary(sop_id: str):
    summary_doc = await db.summaries.find_one({"sop_id": sop_id})
    if not summary_doc or "summary" not in summary_doc:
        raise ValueError("Summary not found")
    
    return summary_doc["summary"]

async def create_task(sop_id: str, topic: str) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        sop_id=sop_id,
        topic=topic,
        created_at=datetime.utcnow(),
        status="pending"
    )
    await db.tasks.insert_one(task.dict())
    return task

async def get_task(task_id: str) -> Optional[Task]:
    task_doc = await db.tasks.find_one({"id": task_id})
    if task_doc:
        return Task(**task_doc)
    return None

async def get_all_tasks() -> List[Task]:
    tasks = []
    async for task_doc in db.tasks.find():
        tasks.append(Task(**task_doc))
    return tasks

async def update_task_status(task_id: str, status: str) -> Optional[Task]:
    result = await db.tasks.find_one_and_update(
        {"id": task_id},
        {"$set": {"status": status}},
        return_document=True
    )
    if result:
        return Task(**result)
    return None

async def get_sop_details(sop_id: str):
    # Get SOP document
    sop_doc = await db.sops.find_one({"sop_id": sop_id})
    if not sop_doc:
        raise ValueError("SOP not found")
    
    # Get summary
    summary_doc = await db.summaries.find_one({"sop_id": sop_id})
    summary = summary_doc["summary"] if summary_doc else None

    # Get effectiveness score from sop_documents collection
    sop_doc_score = await db.sop_documents.find_one({"sop_id": sop_id})
    effectiveness_score = sop_doc_score.get("effectiveness_score") if sop_doc_score else None
    version = sop_doc_score.get("version") if sop_doc_score else None

    return {
        "topic": sop_doc["topic"],
        "description": sop_doc["description"],
        "details": sop_doc["details"],
        "summary": summary,
        "pdf_url": sop_doc["pdf_url"],
        "effectiveness_score": effectiveness_score,
        "version":version
    }

async def edit_sop_details(sop_id: str, edited_details: str):
    # Get original SOP details
    original_sop = await db.sops.find_one({"sop_id": sop_id})
    if not original_sop:
        raise ValueError("Original SOP not found")
    
    # Get original summary
    original_summary = await db.summaries.find_one({"sop_id": sop_id})
    if not original_summary:
        raise ValueError("Original summary not found")
    
    # Get current version number
    current_version = await db.sop_documents.find_one({"sop_id": sop_id})
    new_version = (current_version.get("version", 1) if current_version else 1) + 1
    
    # Generate new SOP ID
    new_sop_id = str(uuid.uuid4())
    
    # Create new PDF with edited details
    pdf_path = create_pdf(new_sop_id, original_sop["topic"], edited_details)
    
    # Get current time in Sri Lankan timezone
    current_time = get_sri_lankan_time()
    
    # Store in edited_sop_details collection
    edited_sop = EditedSOPDetails(
        new_sop_id=new_sop_id,
        old_sop_id=sop_id,
        original_details=original_sop["details"],
        edited_details=edited_details,
        pdf_url=pdf_path,
        created_at=current_time,
        effectiveness_score=100,  # Set initial score to 100
        version=new_version
    )
    await db.edited_sop_details.insert_one(edited_sop.dict())
    
    # Store in sops collection with initial score 100
    await db.sops.insert_one({
        "sop_id": new_sop_id,
        "topic": original_sop["topic"],
        "description": original_sop["description"],
        "details": edited_details,
        "pdf_url": pdf_path,
        "effectiveness_score": 100,
        "version": new_version
    })
    
    # Store in sop_documents collection with initial score 100
    sop_document = SOPDocument(
        sop_id=new_sop_id,
        topic=original_sop["topic"],
        pdf_url=pdf_path,
        created_at=current_time,
        effectiveness_score=100,
        version=new_version
    )
    await db.sop_documents.insert_one(sop_document.dict())
    
    # Store summary
    await db.summaries.insert_one({
        "topic_id": new_sop_id,
        "sop_id": new_sop_id,
        "summary": original_summary["summary"]
    })
    
    # Get embeddings for the edited details
    topic_embedding = get_embedding(original_sop["topic"])
    summary_embedding = get_embedding(original_summary["summary"])
    
    # Store embeddings
    embedding_doc = Embedding(
        sop_id=new_sop_id,
        topic_embedding=topic_embedding,
        summary_embedding=summary_embedding
    )
    await db.embeddings.insert_one(embedding_doc.dict())
    
    return {
        "new_sop_id": new_sop_id,
        "message": "SOP details edited and stored successfully",
        "pdf_url": pdf_path,
        "version": new_version
    }

def calculate_content_similarity(original: str, edited: str) -> float:
    # Split content into sections
    original_sections = re.split(r'\n---\n', original)
    edited_sections = re.split(r'\n---\n', edited)
    
    # Calculate section similarity
    section_similarities = []
    for orig_sec, edit_sec in zip(original_sections, edited_sections):
        # Get embeddings for each section
        orig_embedding = get_embedding(orig_sec)
        edit_embedding = get_embedding(edit_sec)
        
        # Calculate cosine similarity
        similarity = cosine_similarity(
            np.array(orig_embedding).reshape(1, -1),
            np.array(edit_embedding).reshape(1, -1)
        )[0][0]
        section_similarities.append(similarity)
    
    # Calculate average section similarity
    section_similarity = np.mean(section_similarities) if section_similarities else 0
    
    # Calculate content length ratio
    length_ratio = min(len(edited), len(original)) / max(len(edited), len(original))
    
    # Calculate sequence similarity
    sequence_similarity = SequenceMatcher(None, original, edited).ratio()
    
    # Combine scores with weights
    final_score = (
        0.4 * section_similarity +  # Semantic similarity
        0.3 * sequence_similarity +  # Exact content similarity
        0.3 * length_ratio  # Content length ratio
    )
    
    return final_score

async def calculate_effectiveness_score(old_sop_id: str) -> float:
    # Get the edited SOP details
    edited_sop = await db.edited_sop_details.find_one({"old_sop_id": old_sop_id})
    if not edited_sop:
        raise ValueError("No edited version found for this SOP")
    
    # Calculate content similarity
    similarity = calculate_content_similarity(
        edited_sop["original_details"],
        edited_sop["edited_details"]
    )
    
    # Convert similarity to percentage (0-100)
    effectiveness_score = round(similarity * 100, 2)
    
    # Update the edited_sop_details document with the score
    await db.edited_sop_details.update_one(
        {"old_sop_id": old_sop_id},
        {"$set": {"effectiveness_score": effectiveness_score}}
    )
    
    # Update the sops collection with the score for both old and new SOP IDs
    await db.sops.update_one(
        {"sop_id": edited_sop["old_sop_id"]},
        {"$set": {"effectiveness_score": effectiveness_score}}
    )
    await db.sops.update_one(
        {"sop_id": edited_sop["new_sop_id"]},
        {"$set": {"effectiveness_score": 100}}
    )
    
    # Update the sop_documents collection with the score for both old and new SOP IDs
    await db.sop_documents.update_one(
        {"sop_id": edited_sop["old_sop_id"]},
        {"$set": {"effectiveness_score": effectiveness_score}}
    )
    await db.sop_documents.update_one(
        {"sop_id": edited_sop["new_sop_id"]},
        {"$set": {"effectiveness_score": 100}}
    )
    
    return effectiveness_score

async def update_effectiveness_score(sop_id: str):
    # Update edited_sop_details collection
    await db.edited_sop_details.update_one(
        {"old_sop_id": sop_id},
        {"$set": {"effectiveness_score": 100.0}}
    )
    
    # Update sops collection
    await db.sops.update_one(
        {"sop_id": sop_id},
        {"$set": {"effectiveness_score": 100.0}}
    )
    
    # Update sop_documents collection
    await db.sop_documents.update_one(
        {"sop_id": sop_id},
        {"$set": {"effectiveness_score": 100.0}}
    )

async def get_effectiveness_score_by_sop_id(sop_id: str) -> dict:
    sop_doc = await db.sops.find_one({"sop_id": sop_id})

    if not sop_doc or "effectiveness_score" not in sop_doc:
        raise ValueError("Effectiveness score not found for this SOP ID")

    return {
        "effectiveness_score": sop_doc["effectiveness_score"],
        "version": sop_doc.get("version")  # Optional
    }