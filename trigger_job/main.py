import os
import json
import base64
from google.cloud import run_v2

def trigger_job(request):
    """
    Simple HTTP Cloud Function to trigger pvpocket-job Cloud Run job.
    Receives scheduler requests and executes the job with JOB_TYPE parameter.
    """
    # Initialize Cloud Run client
    client = run_v2.JobsClient()
    
    # Get request data
    request_json = request.get_json(silent=True) or {}
    
    # Extract JOB_TYPE from request
    job_type = "scrape_sets"  # default
    if request_json and "data" in request_json:
        if "CHECK_TYPE" in request_json["data"]:
            check_type = request_json["data"]["CHECK_TYPE"]
            if check_type == "limitless_sets":
                job_type = "scrape_sets"
            elif check_type == "google_drive":
                job_type = "scrape_images"
        elif "JOB_TYPE" in request_json["data"]:
            job_type = request_json["data"]["JOB_TYPE"]
    
    # Set up job execution request
    project_id = "pvpocket-dd286"
    location = "us-central1"
    job_name = "pvpocket-job"
    
    # Build job path
    job_path = client.job_path(project_id, location, job_name)
    
    # Create execution request with environment variable override
    overrides = run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=[{"name": "JOB_TYPE", "value": job_type}]
            )
        ]
    )
    
    # Execute the job
    request_obj = run_v2.RunJobRequest(name=job_path, overrides=overrides)
    operation = client.run_job(request=request_obj)
    
    print(f"Triggered job '{job_name}' with JOB_TYPE='{job_type}'")
    return f"Job triggered: {job_type}", 200