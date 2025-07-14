import uuid 

from pydantic import BaseModel
from fastapi import FastAPI

class JobPayload(BaseModel):
    org_id: uuid.UUID
    app_version_id: str
    test_path: str
    priority: int = 1
    target: str = "emulator"

class Job(BaseModel):
    job_id: str
    status: str
    details: JobPayload 


fake_db = {}

app = FastAPI()

@app.get("/", status_code=200)
def read_root():
    """Root endpoint to check if the server is running."""
    return {"message": "QualGent Job Orchestrator is running!"}

@app.post("/jobs", status_code=201)
def submit_job(job_payload: JobPayload):
    """Recieves a job , gives it a unique ID, and stores it."""
    job_id = str(uuid.uuid4())[:8] # generate a short id

    job_data = Job(job_id=job_id, status="queued", details=job_payload)
    fake_db[job_id] = job_data

    print(f"Job submitted: {job_id} for {job_payload.app_version_id}")
    return {"job_id": job_id, "status": job_data.status, "details": job_data.details}

@app.get("/jobs/{job_id}", status_code=200)
def get_job_status(job_id: str):
    """Returns the status of a job by the ID."""
    if job_id not in fake_db:
        return {"error": "Job not found"}, 404
    
    job = fake_db[job_id]
    print(f"Status check for {job.job_id}: {job.status}")
    return  {"job_id": job.job_id, "status": job.status, "details": job.details}


