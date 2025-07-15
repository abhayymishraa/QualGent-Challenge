import redis
import json
import time
import random
import uuid
import os  
from dotenv import load_dotenv  

load_dotenv()
PRIORITY_QUEUES = [f"queue:p{i}" for i in range(10, 0, -1)]  #
PROCESSING_QUEUE_PREFIX = "processing:"
DELAYED_QUEUE = "delayed_queue"
DEAD_LETTER_QUEUE = "dead_letter_queue"
RETRY_DELAY_SECONDS = 60



redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    decode_responses=True,
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
)


# --- LUA SCRIPT for Atomic Batch Fetching ---
# This script atomically finds a job, reserves it, and pulls other matching jobs.
# KEYS[1-N] = Priority queues (e.g., queue:p10, queue:p9...)
# ARGV[1] = ID of the processing queue for this worker
# ARGV[2] = Maximum number of jobs to pull for the batch
# Returns a list of job IDs for the batch.
lua_fetch_batch_script = """
    local a_job_id = redis.call('BRPOPLPUSH', unpack(KEYS), ARGV[1], 0)
    if not a_job_id then return nil end

    local job_key = 'job:' .. a_job_id
    local app_version_id = redis.call('HGET', job_key, 'payload')
    if not app_version_id then return {a_job_id} end
    app_version_id = cjson.decode(app_version_id)['app_version_id']

    local target = cjson.decode(redis.call('HGET', job_key, 'payload'))['target']
    
    local batch = {a_job_id}
    local max_batch_size = tonumber(ARGV[2])

    for i, queue in ipairs(KEYS) do
        if #batch >= max_batch_size then break end
        
        local job_ids_in_queue = redis.call('LRANGE', queue, 0, -1)
        for _, other_job_id in ipairs(job_ids_in_queue) do
            if #batch >= max_batch_size then break end

            local other_job_key = 'job:' .. other_job_id
            local other_payload_json = redis.call('HGET', other_job_key, 'payload')
            if other_payload_json then
                local other_payload = cjson.decode(other_payload_json)
                if other_payload['app_version_id'] == app_version_id and other_payload['target'] == target then
                    redis.call('LREM', queue, 1, other_job_id)
                    redis.call('RPUSH', ARGV[1], other_job_id)
                    table.insert(batch, other_job_id)
                end
            end
        end
    end

    return batch
"""
# Load the script into Redis and get its SHA hash for efficient calling
sha_script = redis_client.script_load(lua_fetch_batch_script)


def handle_failed_batch(batch_job_ids):
    """Handle a failed batch, retrying jobs if possible."""
    print(f"--- Handling FAILED batch: {batch_job_ids} ---")

    # Get job details for each job in the batch
    for job_id in batch_job_ids:
        pipe = redis_client.pipeline()
        pipe.hget(f"job:{job_id}", "retries_done")
        pipe.hget(f"job:{job_id}", "max_retries")
        pipe.hget(f"job:{job_id}", "queue")
        retries_done, max_retries, original_queue = pipe.execute()

        retries_done = int(retries_done or 0)
        max_retries = int(max_retries or 0)

        if retries_done < max_retries:
            new_retry_count = retries_done + 1
            print(
                f"  -> Job {job_id}: Retrying ({new_retry_count}/{max_retries}). Delaying for {RETRY_DELAY_SECONDS}s."
            )
            redis_client.hset(f"job:{job_id}", "retries_done", new_retry_count)
            redis_client.hset(f"job:{job_id}", "status", "queued_for_retry")
            # Add to sorted set with score as the timestamp for reprocessing
            redis_client.zadd(
                DELAYED_QUEUE, {job_id: int(time.time()) + RETRY_DELAY_SECONDS}
            )
        else:
            print(
                f"  -> Job {job_id}: Max retries reached. Moving to dead-letter queue."
            )
            redis_client.hset(f"job:{job_id}", "status", "failed")
            redis_client.lpush(DEAD_LETTER_QUEUE, job_id)


def process_batch(batch_job_ids):
    """Simulates processing a batch of jobs."""
    if not batch_job_ids:
        return

    print(f"\n--- [Processing Batch: {len(batch_job_ids)} jobs] ---")

    first_job_info = json.loads(redis_client.hget(f"job:{batch_job_ids[0]}", "payload"))
    app_version_id = first_job_info["app_version_id"]
    target = first_job_info["target"]

    print(f"Starting batch for app_version '{app_version_id}' on target '{target}'")
    print(f"Batch job IDs: {batch_job_ids}")

    for job_id in batch_job_ids:
        redis_client.hset(f"job:{job_id}", "status", "running")

    # mocking install for appwrights
    print("Simulating app install and setup (10s)...")
    time.sleep(10)

    # mocking time to test
    for job_id in batch_job_ids:
        print(f"  -> Running test for job {job_id} (5s)...")
        time.sleep(5)

    final_status = random.choice(["completed", "failed"])
    print(f"Batch finished with status: {final_status.upper()}")

    if final_status == "completed":
        for job_id in batch_job_ids:
            redis_client.hset(f"job:{job_id}", "status", "completed")
    else:
        handle_failed_batch(batch_job_ids)


def run_worker():
    """Main worker loop."""
    worker_id = str(uuid.uuid4())
    processing_queue = f"{PROCESSING_QUEUE_PREFIX}{worker_id}"
    print(
        f"Worker '{worker_id}' started. Listening for jobs on queues: {PRIORITY_QUEUES}"
    )
    print(f"Using processing queue: {processing_queue}")

    # Crash recovery: Check for orphaned jobs from a previous run
    orphaned_jobs = redis_client.lrange(processing_queue, 0, -1)
    if orphaned_jobs:
        print(f"Found {len(orphaned_jobs)} orphaned jobs. Re-queueing...")
        for job_id in orphaned_jobs:
            original_queue = redis_client.hget(f"job:{job_id}", "queue")
            if original_queue:
                redis_client.lpush(original_queue, job_id)
        redis_client.delete(processing_queue)  # Clear our processing list

    while True:
        try:
            # Atomically fetch a batch of jobs using the Lua script
            batch_job_ids = redis_client.evalsha(
                sha_script, len(PRIORITY_QUEUES), *PRIORITY_QUEUES, processing_queue, 5
            )

            if batch_job_ids:
                process_batch(batch_job_ids)
                # On success, clear the jobs from the processing queue
                redis_client.delete(processing_queue)

        except redis.exceptions.RedisError as e:
            print(f"Redis error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Recovering...")
            # Re-queue jobs from the processing list before exiting or sleeping
            failed_batch = redis_client.lrange(processing_queue, 0, -1)
            if failed_batch:
                handle_failed_batch(failed_batch)
                redis_client.delete(processing_queue)
            time.sleep(5)


def run_requeuer():
    """Monitors the delayed queue and re-queues jobs when their delay has passed."""
    print("Re-queuer process started. Monitoring delayed jobs...")
    while True:
        # Fetch jobs whose delay timestamp is now or in the past
        job_to_requeue = redis_client.zrangebyscore(
            DELAYED_QUEUE, "-inf", int(time.time()), start=0, num=1
        )

        if not job_to_requeue:
            time.sleep(5)  # Wait if no jobs are ready
            continue

        job_id = job_to_requeue[0]
        # Atomically remove from sorted set to prevent other requeuers from grabbing it
        if redis_client.zrem(DELAYED_QUEUE, job_id):
            original_queue = redis_client.hget(f"job:{job_id}", "queue")
            if original_queue:
                print(f"Re-queueing job {job_id} to {original_queue}")
                redis_client.hset(f"job:{job_id}", "status", "queued")
                redis_client.lpush(original_queue, job_id)


if __name__ == "__main__":
    #  we can run them in separate terminals:
    # `python worker.py worker`
    # `python worker.py requeuer`
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        run_worker()
    elif len(sys.argv) > 1 and sys.argv[1] == "requeuer":
        run_requeuer()
    else:
        print("Usage: python worker.py [worker|requeuer]")
