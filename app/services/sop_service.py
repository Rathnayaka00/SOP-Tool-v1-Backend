from app.utils.openai_helper import generate_sop, edit_sop
from app.utils.pdf_generator import create_pdf
from app.utils.openai_embeddings import get_embedding
from app.utils.similarity_search import find_similar_sops
from app.database import db
from app.models.embedding import Embedding
from app.models.sop import Task, SOPDocument, EditedSOPDocument
import uuid
import os
from datetime import datetime
import pytz
from typing import List, Optional

# Get Sri Lankan timezone
sri_lanka_tz = pytz.timezone('Asia/Colombo')

async def create_sop(topic: str, description: str):
    topic_embedding = get_embedding(topic)
    description_embedding = get_embedding(description)
    
    sop_id = str(uuid.uuid4())

    sop_data = await generate_sop(topic, description)

    if not isinstance(sop_data, dict) or "details" not in sop_data or "summary" not in sop_data:
        raise ValueError("Invalid SOP response from OpenAI")

    pdf_path = create_pdf(sop_id, topic, sop_data["details"])

    # Create SOP document with Sri Lankan timezone
    current_time = datetime.now(sri_lanka_tz)
    
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
    current_time = datetime.now(sri_lanka_tz)
    
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

async def edit_existing_sop(old_sop_id: str, user_suggestion: str):
    # Get the existing SOP
    existing_sop = await db.sops.find_one({"sop_id": old_sop_id})
    if not existing_sop:
        raise ValueError("SOP not found")
    
    # Get the current version from edited_sop_documents
    version = 1
    latest_edited = await db.edited_sop_documents.find_one(
        {"old_sop_id": old_sop_id},
        sort=[("version", -1)]
    )
    if latest_edited:
        version = latest_edited["version"] + 1
    
    # Generate new SOP based on user suggestion
    sop_data = await edit_sop(existing_sop["topic"], existing_sop["details"], user_suggestion)
    
    if not isinstance(sop_data, dict) or "details" not in sop_data:
        raise ValueError("Invalid SOP response from OpenAI")
    
    # Generate new SOP ID
    new_sop_id = str(uuid.uuid4())
    
    # Create PDF for the new SOP
    pdf_path = create_pdf(new_sop_id, existing_sop["topic"], sop_data["details"])
    
    # Get current time in Sri Lankan timezone
    current_time = datetime.now(sri_lanka_tz)
    
    # Store in edited_sop_documents collection
    edited_sop_doc = EditedSOPDocument(
        new_sop_id=new_sop_id,
        old_sop_id=old_sop_id,
        topic=existing_sop["topic"],
        details=sop_data["details"],
        version=version,
        created_at=current_time
    )
    await db.edited_sop_documents.insert_one(edited_sop_doc.dict())
    
    # Store in sops collection
    await db.sops.insert_one({
        "sop_id": new_sop_id,
        "topic": existing_sop["topic"],
        "description": existing_sop["description"],
        "details": sop_data["details"],
        "pdf_url": pdf_path
    })
    
    # Store in sop_documents collection
    sop_document = SOPDocument(
        sop_id=new_sop_id,
        topic=existing_sop["topic"],
        pdf_url=pdf_path,
        created_at=current_time
    )
    await db.sop_documents.insert_one(sop_document.dict())
    
    # Store summary
    await db.summaries.insert_one({
        "topic_id": new_sop_id,
        "sop_id": new_sop_id,
        "summary": sop_data.get("summary", "")
    })
    
    # Generate and store embeddings
    topic_embedding = get_embedding(existing_sop["topic"])
    summary_embedding = get_embedding(sop_data.get("summary", ""))
    
    embedding_doc = Embedding(
        sop_id=new_sop_id,
        topic_embedding=topic_embedding,
        summary_embedding=summary_embedding
    )
    
    await db.embeddings.insert_one(embedding_doc.dict())
    
    return {
        "new_sop_id": new_sop_id,
        "old_sop_id": old_sop_id,
        "version": version,
        "message": "SOP edited successfully",
        "pdf_url": pdf_path
    }