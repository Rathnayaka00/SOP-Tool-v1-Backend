from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.sop_service import (
    create_sop, get_sop_pdf, get_sop_summary, create_sop_direct,
    create_task, get_task, get_all_tasks, update_task_status
)
from app.utils.openai_embeddings import get_embedding
from app.utils.similarity_search import find_similar_sops
from app.models.sop import Task
from pydantic import BaseModel
import os
from typing import Optional

router = APIRouter()

class SOPRequest(BaseModel):
    topic: str
    description: str

class SimilarityResponse(BaseModel):
    sop_id: str
    similarity_score: float
    is_existing: bool

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
