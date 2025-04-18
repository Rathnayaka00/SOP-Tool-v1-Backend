from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.sop_service import (
    create_sop, get_sop_pdf, get_sop_summary, create_sop_direct,
    create_task, get_task, get_all_tasks, update_task_status, get_sop_details,
    edit_sop_details, calculate_effectiveness_score, update_effectiveness_score,get_effectiveness_score_by_sop_id
)
from app.utils.openai_embeddings import get_embedding
from app.utils.similarity_search import find_similar_sops
from app.models.sop import Task
from pydantic import BaseModel
import os
from typing import Optional
from app.database import db

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

class EditSOPDetailsRequest(BaseModel):
    edited_details: str

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

@router.get("/sop/{sop_id}/details")
async def get_sop_details_endpoint(sop_id: str):
    try:
        details = await get_sop_details(sop_id)
        return details
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop/{sop_id}/version_history")
async def get_sop_version_history(sop_id: str):
    try:
        # Get the original SOP document
        original_sop = await db.sops.find_one({"sop_id": sop_id})
        if not original_sop:
            raise ValueError("SOP not found")
        
        # Get all versions of this SOP
        versions = []
        
        # Get the original version
        original_doc = await db.sop_documents.find_one({"sop_id": sop_id})
        if original_doc:
            versions.append({
                "sop_id": original_doc["sop_id"],
                "version": original_doc.get("version", 1),
                "created_at": original_doc["created_at"],
                "effectiveness_score": original_doc.get("effectiveness_score"),
                "pdf_url": original_doc["pdf_url"]
            })
        
        # Get edited versions
        edited_versions = await db.edited_sop_details.find({"old_sop_id": sop_id}).to_list(None)
        for edited in edited_versions:
            new_sop = await db.sop_documents.find_one({"sop_id": edited["new_sop_id"]})
            if new_sop:
                versions.append({
                    "sop_id": new_sop["sop_id"],
                    "version": new_sop.get("version", 1),
                    "created_at": new_sop["created_at"],
                    "effectiveness_score": new_sop.get("effectiveness_score"),
                    "pdf_url": new_sop["pdf_url"]
                })
        
        # Sort versions by version number
        versions.sort(key=lambda x: x["version"])
        
        return {
            "topic": original_sop["topic"],
            "description": original_sop["description"],
            "versions": versions
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/sop/{sop_id}/edit")
async def edit_sop_details_endpoint(sop_id: str, edit_request: EditSOPDetailsRequest):
    try:
        response = await edit_sop_details(sop_id, edit_request.edited_details)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop/{old_sop_id}/effectiveness_score")
async def get_effectiveness_score_endpoint(old_sop_id: str):
    try:
        score = await calculate_effectiveness_score(old_sop_id)
        return {"effectiveness_score": score}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sop/{sop_id}/effectiveness_score")
async def update_effectiveness_score_endpoint(sop_id: str):
    try:
        await update_effectiveness_score(sop_id)
        return {"message": "Effectiveness score updated to 100%"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/sop/{sop_id}/direct_effectiveness_score")
async def get_direct_effectiveness_score(sop_id: str):
    try:
        result = await get_effectiveness_score_by_sop_id(sop_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sop_documents")
async def get_all_sop_documents():
    try:
        # Get all SOP documents
        sop_documents = []
        async for doc in db.sop_documents.find():
            sop_documents.append({
                "sop_id": doc["sop_id"],
                "topic": doc["topic"],
                "created_at": doc["created_at"],
                "version": doc.get("version", 1),
                "effectiveness_score": doc.get("effectiveness_score")
            })
        
        return sop_documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))