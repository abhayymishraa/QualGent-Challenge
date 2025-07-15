import uuid
import redis
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class JobPayload(BaseModel):
    org_id: str
    app_version_id: str
    test_path: str
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1=lowest, 10=highest)"
    )
    target: Literal["emulator", "device", "browserstack"]
    max_retries: int = Field(default=3, ge=0, le=5)


class JobSubmissionResponse(BaseModel):
    job_id: str
    status: str
    details: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    details: Dict[str, Any]


app = FastAPI()
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    decode_responses=True,
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
)


@app.get("/", summary="Health Check")
def read_root():
    """Root endpoint to check if the server is running."""
    return {"message": "QualGent Job Orchestrator is running!"}


@app.post(
    "/jobs",
    status_code=201,
    response_model=JobSubmissionResponse,
    summary="Submit a New Job",
)
def submit_job(job_payload: JobPayload):
    """
    Receives a job, generates a unique ID, stores its metadata,
    and pushes it to the appropriate priority queue.
    """
    job_id = str(uuid.uuid4())
    queue_name = f"queue:p{job_payload.priority}"

    job_data = {
        "job_id": job_id,
        "status": "queued",
        "payload": job_payload.model_dump_json(),
        "queue": queue_name,
        "retries_done": "0",
        "max_retries": str(job_payload.max_retries),
    }

    # Use a pipeline for atomic execution
    pipe = redis_client.pipeline()
    pipe.hset(f"job:{job_id}", mapping=job_data)
    pipe.lpush(queue_name, job_id)
    pipe.execute()

    print(f"Job Queued: {job_id} on queue {queue_name}")
    return {
        "job_id": job_id,
        "status": "queued",
        "details": f"Job enqueued to {queue_name}",
    }


@app.get("/jobs/{job_id}", response_model=JobStatusResponse, summary="Check Job Status")
def get_job_status(job_id: str):
    """Returns the detailed status and data of a job by its ID."""
    job_data = redis_client.hgetall(f"job:{job_id}")

    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Parse nested JSON payload for cleaner output
    if "payload" in job_data:
        job_data["payload"] = json.loads(job_data["payload"])

    return {
        "job_id": job_id,
        "status": job_data.get("status", "unknown"),
        "details": job_data,
    }
