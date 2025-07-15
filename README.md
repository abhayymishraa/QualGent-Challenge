# QualGent Backend Coding Challenge

A CLI tool and backend service for queuing, grouping, and deploying AppWright tests across local devices, emulators, and BrowserStack.

# Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  GitHub Actions │    │   CLI Tool      │    │   Backend API   │
│                 │───▶│   (qgjob)       │───▶│   (FastAPI)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Worker Pool   │    │   Job Queues    │    │   Redis Store   │
│                 │◀───│   (Priority)    │◀───│                 │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

1. **CLI Tool (`qgjob`)**: Node.js-based command-line interface for job submission and status checking
2. **Backend API**: FastAPI server that handles job orchestration and queuing
3. **Redis Queue System**: Priority-based job queuing with grouping capabilities
4. **Worker Pool**: Processes jobs in batches grouped by `app_version_id` and `target`
5. **GitHub Actions**: CI/CD integration for automated test execution

## Video Demonstrations

### Server Logs
[Watch server processing demonstration](./public/logs_server.mp4)

### GitHub Actions Workflow - Failed Test
[Watch failed workflow demonstration](./public/workflow_failed.mp4)

### GitHub Actions Workflow - Passed Test
[Watch successful workflow demonstration](./public/workflow_passsed.mp4)

## Quick Start

### Prerequisites

- Node.js 18+ 
- Python 3.12+
- Redis server (local or cloud)
- Docker (optional)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/abhayymishraa/QualGent-Challenge
   cd QualGent-Assignment
   ```

2. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp server/.env.example server/.env
   ```
   ```
   # Edit the .env file with your Redis credentials
   REDIS_HOST=your-redis-host
   REDIS_PORT=your-redis-port
   REDIS_USERNAME=your-redis-username
   REDIS_PASSWORD=your-redis-password
   ```

3. **Install CLI dependencies**
   ```bash
   cd cli
   npm install
   npm run build
   npm link 
   ```

4. **Install server dependencies**
   ```bash
   cd server
   python -m venv venv
   source venv/bin/activate     
   pip install -r requirements.txt
   ```

### Running the System

#### Option 1: Docker (Recommended)
```bash
cd server
docker build -t qualgent-server .
docker run -p 8000:8000 --env-file .env qualgent-server
```

#### Option 2: Manual Start
```bash
# Terminal 1: Start the API server
cd server
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start a worker
python worker.py worker

# Terminal 3: Start the requeuer (handles retries)
python worker.py requeuer
```

##  Examples

### CLI Commands

**Submit a test job:**
```bash
qgjob submit \
  --org-id=qualgent \
  --app-version-id=xyz123 \
  --test=tests/onboarding.spec.js \
  --target=emulator \
  --priority=8 \
  --max-retries=3
```

**Check job status:**
```bash
qgjob status abc456
```

### API Endpoints

- `POST /jobs` - Submit a new job
- `GET /jobs/{job_id}` - Get job status
- `GET /` - Health check

## Job Grouping & Scheduling Logic

The system optimizes test execution by:

1. **Priority-Based Queuing**: Jobs are placed in priority queues (p1-p10, where p10 is highest)
2. **Intelligent Batching**: Workers use Lua scripts to atomically:
   - Fetch a job from the highest priority queue
   - Find other jobs with the same `app_version_id` and `target`
   - Group them into a single batch for processing
3. **Efficient Execution**: Each batch:
   - Installs the app once per `app_version_id`
   - Runs all tests for that version sequentially
   - Minimizes setup overhead

### Batch Processing Flow

```
1. Worker fetches Job A (app_version=v1.0, target=emulator)
2. System searches for other jobs with same app_version + target
3. Finds Jobs B, C, D with matching criteria
4. Creates batch: [A, B, C, D]
5. Installs app v1.0 on emulator (once)
6. Runs mock-tests for jobs A, B, C, D sequentially
7. Reports results for all jobs in batch
```

## Retry & Failure Handling

- **Automatic Retries**: Failed jobs are retried up to `max_retries` times
- **Delayed Retry Queue**: Failed jobs wait 60 seconds before retry
- **Dead Letter Queue**: Jobs exceeding max retries are moved to DLQ
- **Crash Recovery**: Orphaned jobs are automatically re-queued on worker restart

## GitHub Actions Integration

The workflow automatically:
1. Submits test jobs via the CLI
2. Polls for completion (3-minute timeout)
3. Fails the build if any test fails
4. Provides clear success/failure feedback

## End-to-End Test Example

```bash
# 1. Start the system (server + worker + requeuer)
cd server && docker run -p 8000:8000 --env-file .env qualgent-server

# 2. Submit a job
qgjob submit --org-id=test-org --app-version-id=v1.0 --test=tests/login.spec.js --target=emulator --priority=5

# 3. Check status
qgjob status <job-id-from-step-2>

# 4. Submit more jobs with same app version (they'll be batched)
qgjob submit --org-id=test-org --app-version-id=v1.0 --test=tests/signup.spec.js --target=emulator --priority=5
qgjob submit --org-id=test-org --app-version-id=v1.0 --test=tests/dashboard.spec.js --target=emulator --priority=5
```

## Sample Output Logs

### Job Submission
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "queued",
  "details": "Job enqueued to queue:p5"
}
```

### Worker Processing
```
Worker 'a1b2c3d4' started. Listening for jobs on queues: ['queue:p10', 'queue:p9', ...]
Using processing queue: processing:a1b2c3d4

--- [Processing Batch: 3 jobs] ---
Starting batch for app_version 'v1.0' on target 'emulator'
Batch job IDs: ['job1', 'job2', 'job3']
Simulating app install and setup (10s)...
  -> Running test for job job1 (5s)...
  -> Running test for job job2 (5s)...
  -> Running test for job job3 (5s)...
Batch finished with status: COMPLETED
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `REDIS_USERNAME` | Redis username | `default` |
| `REDIS_PASSWORD` | Redis password | `your-password` |

### CLI Options

| Option | Description | Required | Default |
|--------|-------------|----------|---------|
| `--org-id` | Organization identifier | Yes | - |
| `--app-version-id` | App version to test | Yes | - |
| `--test` | Path to test file | Yes | - |
| `--target` | Target device type | Yes | - |
| `--priority` | Job priority (1-10) | No | 5 |
| `--max-retries` | Maximum retry attempts | No | 3 |

## Monitoring & Scaling

### Horizontal Scaling
- **Multiple Workers**: Run multiple worker processes to handle more jobs
- **Redis Clustering**: Use Redis Cluster for high availability
- **Load Balancing**: Deploy multiple API instances behind a load balancer

### Monitoring Endpoints
- `GET /` - Health check
- `GET /jobs/{job_id}` - Individual job status
- Redis metrics for queue lengths and processing times

## Reliability Features

- **Atomic Operations**: Lua scripts ensure consistent job batching
- **Crash Recovery**: Workers automatically recover orphaned jobs
- **Retry Logic**: Exponential backoff with dead letter queue
- **Deduplication**: Job IDs prevent duplicate submissions
- **Graceful Shutdown**: Workers complete current batches before stopping


## Backend is available at:
```bash
   https://qualgent-challenge-backend.onrender.com
```
   
*Built with ❤️ by abhay for the QualGent Backend Coding Challenge*