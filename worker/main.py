import redis
import json
import time
import random

import redis.exceptions

print("Worker Started. Waiting for jobs...")

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def simulate_test_run(job_id):
    """Simulates running a test, then updates the status."""
    print(f"Processing job: {job_id}.")

    redis_client.hset(f"job:{job_id}", "status", "running")

    time.sleep(random.randint(15, 40))

    final_status = random.choice(["completed", "failed"])

    redis_client.hset(f"job:{job_id}", "status", final_status)

    print(f"Job {job_id} finished with status: {final_status}")

while True:
    try:
        _, job_json = redis_client.brpop("job_queue")

        job_data = json.loads(job_json)
        job_id = job_data["job_id"]

        simulate_test_run(job_id)

    except redis.exceptions.ConnectionError as e:
        print(f"Redis connection error: {e}")
        time.sleep(5)
