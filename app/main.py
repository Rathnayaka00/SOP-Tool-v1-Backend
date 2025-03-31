from fastapi import FastAPI
from app.routes.sop_routes import router as sop_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SOP Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(sop_router, prefix="/api")

@app.get("/")
def home():
    return {"message": "Welcome to the SOP Generator Tool"}
