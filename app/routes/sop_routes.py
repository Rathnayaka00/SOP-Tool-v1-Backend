from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.sop_service import (
    create_sop, get_sop_pdf, get_sop_summary, create_sop_direct,
    create_task, get_task, get_all_tasks, update_task_status,
    edit_existing_sop, calculate_similarity_percentage
)
from app.utils.openai_embeddings import get_embedding
from app.utils.similarity_search import find_similar_sops
from app.models.sop import Task
from app.database import db
from pydantic import BaseModel
import os
from typing import Optional, List

router = APIRouter()

class SOPRequest(BaseModel):
    topic: str
    description: str

class EditSOPRequest(BaseModel):
    old_sop_id: str
    user_suggestion: str

class SimilarityResponse(BaseModel):
    sop_id: str
    similarity_score: float
    similar_sops: List[dict]

class ComparisonResponse(BaseModel):
    old_sop_id: str
    new_sop_id: Optional[str] = None
    similarity_percentage: int
    message: str

class SimilarityRequest(BaseModel):
    topic: str
    description: str

class TaskCreateRequest(BaseModel):
    sop_id: str
    topic: str

class TaskStatusUpdateRequest(BaseModel):
    status: str

@router.post("/generate_sop")
async def generate_sop_endpoint(sop_request: SOPRequest):
    try:
        response = await create_sop(sop_request.topic, sop_request.description)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/generate_sop_direct")
async def generate_sop_direct_endpoint(sop_request: SOPRequest):
    try:
        response = await create_sop_direct(sop_request.topic, sop_request.description)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop/{sop_id}/pdf")
async def get_pdf(sop_id: str):
    try:
        pdf_path = await get_sop_pdf(sop_id)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
        
        headers = {
            "Content-Disposition": f"inline; filename=sop_{sop_id}.pdf"
        }
        return FileResponse(
            pdf_path, 
            media_type="application/pdf", 
            filename=f"sop_{sop_id}.pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop/{sop_id}/summary")
async def get_summary(sop_id: str):
    try:
        summary = await get_sop_summary(sop_id)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sop/similar")
async def find_similar_sops_endpoint(request: SimilarityRequest, threshold: float = 0.6):
    try:
        topic_embedding = get_embedding(request.topic)
        description_embedding = get_embedding(request.description)
        
        similar_sops = await find_similar_sops(topic_embedding, description_embedding, threshold)
        
        response = []
        for sop_id, similarity in similar_sops:
            response.append({
                "sop_id": sop_id,
                "similarity_score": similarity,
                "is_existing": True
            })
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Task routes
@router.post("/tasks", response_model=Task)
async def create_task_endpoint(task_request: TaskCreateRequest):
    try:
        task = await create_task(
            sop_id=task_request.sop_id,
            topic=task_request.topic
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}", response_model=Task)
async def get_task_endpoint(task_id: str):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks", response_model=list[Task])
async def get_all_tasks_endpoint():
    return await get_all_tasks()

@router.patch("/tasks/{task_id}/status", response_model=Task)
async def update_task_status_endpoint(task_id: str, status_request: TaskStatusUpdateRequest):
    task = await update_task_status(task_id, status_request.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/edit_sop")
async def edit_sop_endpoint(edit_request: EditSOPRequest):
    try:
        response = await edit_existing_sop(edit_request.old_sop_id, edit_request.user_suggestion)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop/{sop_id}/comparison", response_model=ComparisonResponse)
async def get_sop_comparison(sop_id: str):
    try:
        # Check if the SOP has been edited
        edited_doc = await db.edited_sop_documents.find_one({"old_sop_id": sop_id})
        if not edited_doc:
            return ComparisonResponse(
                old_sop_id=sop_id,
                similarity_percentage=100,
                message="SOP has not been edited"
            )
        
        # Get the old SOP details
        old_sop = await db.sops.find_one({"sop_id": sop_id})
        if not old_sop:
            raise HTTPException(status_code=404, detail="Original SOP not found")
        
        # Get the new SOP details
        new_sop = await db.sops.find_one({"sop_id": edited_doc["new_sop_id"]})
        if not new_sop:
            raise HTTPException(status_code=404, detail="Edited SOP not found")
        
        # Calculate similarity percentage
        similarity_percentage = calculate_similarity_percentage(old_sop["details"], new_sop["details"])
        
        return ComparisonResponse(
            old_sop_id=sop_id,
            new_sop_id=edited_doc["new_sop_id"],
            similarity_percentage=similarity_percentage,
            message="Comparison calculated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))