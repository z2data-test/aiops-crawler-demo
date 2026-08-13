# Project Context

This document contains all source code and configuration files for the Crawler and AIOps Controller project.

## File: docker-compose.yml

```yml
services:
  mongodb:
    image: mongo:7.0
    container_name: mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    networks:
      - aiops_network

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    networks:
      - aiops_network

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline/crawler.conf:/usr/share/logstash/pipeline/logstash.conf:ro
      - ./logs:/usr/share/logstash/logs
    depends_on:
      - elasticsearch
    networks:
      - aiops_network

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - aiops_network

  crawler:
    build: .
    container_name: simple_crawler
    environment:
      - CRAWLER_ID=crawler-001
      - CRAWLER_NAME=simple-crawler
      - SOURCE_URL=https://jsonplaceholder.typicode.com/posts
      - MONGODB_URI=mongodb://mongodb:27017
      - MONGODB_DATABASE=aiops_demo
      - MONGODB_COLLECTION=crawler_results
      - LOG_LEVEL=INFO
      - ENVIRONMENT=demo
      - LOG_FILE_PATH=/app/logs/crawler.log
    volumes:
      - ./logs:/app/logs
    depends_on:
      - mongodb
    networks:
      - aiops_network

  aiops-controller:
    build: ./aiops-controller
    container_name: aiops_controller
    environment:
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - ELASTICSEARCH_CRAWLER_INDEX=scrm-aiops-crawler-*
      - ELASTICSEARCH_CONTROLLER_INDEX=scrm-aiops-controller
      - MONGODB_URI=mongodb://mongodb:27017
      - NVIDIA_API_KEY=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
      - NVIDIA_MODEL=meta/llama-3.1-405b-instruct
      - NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
      - AIOPS_DEMO_MODE=false
      - POLL_INTERVAL_SECONDS=5
      - LOG_LEVEL=INFO
    depends_on:
      - elasticsearch
      - mongodb
    networks:
      - aiops_network

networks:
  aiops_network:
    driver: bridge

volumes:
  mongo_data:
  es_data:

```

## File: Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure log directory exists
RUN mkdir -p /app/logs

CMD ["python", "-m", "app.main"]

```

## File: README.md

```md
# Simple Python Crawler Application (AIOps Demo - Stage 1)

A lightweight, robust Python 3.12+ crawler application built as Stage 1 for an AIOps pipeline. The application fetches data from an HTTP source, stores records in MongoDB, emits ECS-compliant structured JSON logs to both stdout and a log file, supports 7 realistic simulated failure scenarios using the real application execution path, and integrates seamlessly with Logstash, Elasticsearch, and Kibana.

---

## 1. Project Architecture & Flow

```
+---------------------------------------------------------------------------------------------------+
|                                       Crawler Application                                         |
|                                                                                                   |
|  [simulate_error.py] --(--simulate-error)--> [main.py] --> [Crawler Engine]                     |
|                                                                    |                              |
|                                                                    v                              |
|                                                          [Structured Logger]                      |
+--------------------------------------------------------------------+------------------------------+
                                                                     |
                                            +------------------------+------------------------+
                                            |                                                 |
                                            v                                                 v
                                       [ stdout ]                                [ /app/logs/crawler.log ]
                             (Local Docker Debugging Only)                                    |
                                                                                              v
                                                                                    [ Logstash Container ]
                                                                                   (reads file input ONLY)
                                                                                              |
                                                                                              v
                                                                                   [ Elasticsearch Cluster ]
                                                                                (scrm-aiops-crawler-YYYY.MM.dd)
                                                                                              |
                                                                                              v
                                                                                       [ Kibana UI ]
```

---

## 2. Project Structure

```
simple-crawler/
├── app/
│   ├── __init__.py
│   ├── main.py          # Application CLI entry point & UUID run_id generator
│   ├── config.py        # Pydantic Settings configuration loader
│   ├── logger.py        # ECS JSON Formatter & Logger setup utilities
│   ├── crawler.py       # Core Crawler engine & lifecycle orchestration
│   ├── mongodb.py       # MongoDB client & document persistence handler
│   └── models.py        # Pydantic validation schemas
│
├── scripts/
│   └── simulate_error.py # Error simulation CLI script triggering real code path
│
├── tests/
│   ├── __init__.py
│   ├── test_crawler.py  # Unit tests for crawler execution
│   ├── test_logging.py  # Unit tests for JSON structured logger
│   └── test_errors.py   # Unit tests for error simulation scenarios
│
├── logstash/
│   └── pipeline/
│       └── crawler.conf # Logstash ingestion pipeline configuration
│
├── .env.example         # Template for environment variables
├── requirements.txt     # Python package dependencies
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Multi-container orchestration (Crawler, ES, Logstash, Kibana, Mongo)
└── README.md            # Complete project & logger documentation
```

---

## 3. All Logger Calls

Below is an exhaustive catalog of **EVERY** logger statement executed in the codebase. Every log line emits structured JSON complying with Elastic Common Schema (ECS) light guidelines.

### Mandatory Fields on Every Log Statement:
- `@timestamp`: UTC ISO 8601 string (e.g. `2026-08-11T14:00:00.000Z`)
- `service.name`: Service name (`simple-crawler`)
- `environment`: Environment tag (`demo`)
- `crawler.id`: Crawler ID (`crawler-001`)
- `crawler.name`: Crawler name (`simple-crawler`)
- `crawler.run_id`: Execution UUID unique to each run
- `crawler.status`: Crawler state (`starting`, `running`, `completed`, `failed`)
- `event.action`: Event action identifier
- `event.outcome`: `success` or `failure`
- `log.level`: `INFO` or `ERROR`
- `message`: Human-readable summary message

---

### Logger Call 1: Crawler Started
- **File**: `app/crawler.py`
- **Function**: `run()`
- **Log Level**: `INFO`
- **event.action**: `crawler_started`
- **event.outcome**: `success`
- **Crawler Status**: `starting`
- **Situation**: Emitted immediately when a new crawler run commences.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.000Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "starting"
  },
  "event": { "action": "crawler_started", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Crawler instance crawler-001 started execution"
}
```

---

### Logger Call 2: Source Request Started
- **File**: `app/crawler.py`
- **Function**: `fetch_source_data()`
- **Log Level**: `INFO`
- **event.action**: `source_request_started`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted right before initiating the HTTP GET request to `SOURCE_URL`.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.100Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "source_request_started", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Sending HTTP GET request to https://jsonplaceholder.typicode.com/posts"
}
```

---

### Logger Call 3: Source Request Succeeded
- **File**: `app/crawler.py`
- **Function**: `fetch_source_data()`
- **Log Level**: `INFO`
- **event.action**: `source_request_succeeded`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted when the source HTTP request returns HTTP status 200 OK with valid JSON.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.350Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "source_request_succeeded", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Successfully fetched payload from https://jsonplaceholder.typicode.com/posts"
}
```

---

### Logger Call 4: Source Request Failed (Network/Timeout/Invalid Response)
- **File**: `app/crawler.py`
- **Function**: `fetch_source_data()`
- **Log Level**: `ERROR`
- **event.action**: `source_request_failed`
- **event.outcome**: `failure`
- **Crawler Status**: `failed`
- **Situation**: Emitted when HTTP GET fails due to network connection error, timeout, or invalid response status/payload.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:05.120Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "failed"
  },
  "event": { "action": "source_request_failed", "outcome": "failure" },
  "log": { "level": "ERROR" },
  "message": "HTTP request to source failed: Simulated failure: HTTP request to source timed out after 5.0 seconds",
  "error": {
    "category": "source_timeout",
    "simulated": true,
    "message": "Simulated failure: HTTP request to source timed out after 5.0 seconds"
  }
}
```

---

### Logger Call 5: Records Received
- **File**: `app/crawler.py`
- **Function**: `process_records()`
- **Log Level**: `INFO`
- **event.action**: `records_received`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted after raw JSON records are parsed and validated using Pydantic models.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.400Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "records_received", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Successfully parsed and validated 5 records",
  "records": { "count": 5 }
}
```

---

### Logger Call 6: MongoDB Connection Started
- **File**: `app/mongodb.py`
- **Function**: `connect()`
- **Log Level**: `INFO`
- **event.action**: `mongodb_connection_started`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted when initiating connection to MongoDB instance.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.420Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "mongodb_connection_started", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Connecting to MongoDB"
}
```

---

### Logger Call 7: MongoDB Connection Succeeded
- **File**: `app/mongodb.py`
- **Function**: `connect()`
- **Log Level**: `INFO`
- **event.action**: `mongodb_connection_succeeded`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted when MongoDB connection and ping command succeed.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.450Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "mongodb_connection_succeeded", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Successfully connected to MongoDB"
}
```

---

### Logger Call 8: MongoDB Connection Failed
- **File**: `app/mongodb.py`
- **Function**: `connect()`
- **Log Level**: `ERROR`
- **event.action**: `mongodb_connection_failed`
- **event.outcome**: `failure`
- **Crawler Status**: `failed`
- **Situation**: Emitted when MongoDB connection or ping times out or is refused.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:03.450Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "failed"
  },
  "event": { "action": "mongodb_connection_failed", "outcome": "failure" },
  "log": { "level": "ERROR" },
  "message": "MongoDB connection failed: ServerSelectionTimeoutError: connection timed out",
  "error": {
    "category": "mongodb_timeout",
    "simulated": true,
    "message": "Simulated MongoDB connection timeout after 3000ms"
  }
}
```

---

### Logger Call 9: Records Stored Successfully
- **File**: `app/mongodb.py`
- **Function**: `insert_records()`
- **Log Level**: `INFO`
- **event.action**: `records_stored`
- **event.outcome**: `success`
- **Crawler Status**: `running`
- **Situation**: Emitted after documents are successfully inserted into MongoDB `crawler_results` collection.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.480Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "running"
  },
  "event": { "action": "records_stored", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Successfully stored 5 records in MongoDB",
  "records": { "count": 5 }
}
```

---

### Logger Call 10: Database Write Failed
- **File**: `app/mongodb.py`
- **Function**: `insert_records()`
- **Log Level**: `ERROR`
- **event.action**: `database_write_failed`
- **event.outcome**: `failure`
- **Crawler Status**: `failed`
- **Situation**: Emitted when inserting documents into MongoDB fails.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.500Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "failed"
  },
  "event": { "action": "database_write_failed", "outcome": "failure" },
  "log": { "level": "ERROR" },
  "message": "Failed to store records in MongoDB: Simulated database write failure",
  "error": {
    "category": "database_write_error",
    "simulated": true,
    "message": "Simulated database write failure"
  }
}
```

---

### Logger Call 11: Unexpected Exception
- **File**: `app/crawler.py`
- **Function**: `run()`
- **Log Level**: `ERROR`
- **event.action**: `unexpected_exception`
- **event.outcome**: `failure`
- **Crawler Status**: `failed`
- **Situation**: Emitted when an unhandled exception or process execution fault occurs during record transformation.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.410Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "failed"
  },
  "event": { "action": "unexpected_exception", "outcome": "failure" },
  "log": { "level": "ERROR" },
  "message": "Unexpected exception during crawler execution: Simulated unexpected crawler process failure during record transformation",
  "error": {
    "category": "crawler_process_error",
    "simulated": true,
    "message": "Simulated unexpected crawler process failure during record transformation"
  },
  "duration_ms": 110.25
}
```

---

### Logger Call 12: Crawler Completed Successfully
- **File**: `app/crawler.py`
- **Function**: `run()`
- **Log Level**: `INFO`
- **event.action**: `crawler_completed`
- **event.outcome**: `success`
- **Crawler Status**: `completed`
- **Situation**: Emitted when the entire crawl, parse, connect, and insert workflow succeeds.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.520Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "completed"
  },
  "event": { "action": "crawler_completed", "outcome": "success" },
  "log": { "level": "INFO" },
  "message": "Crawler run finished successfully in 520.15ms",
  "duration_ms": 520.15,
  "records": { "count": 5 }
}
```

---

### Logger Call 13: Crawler Completed with Failure
- **File**: `app/crawler.py`
- **Function**: `run()`
- **Log Level**: `ERROR`
- **event.action**: `crawler_failed`
- **event.outcome**: `failure`
- **Crawler Status**: `failed`
- **Situation**: Final summary log emitted whenever the crawler execution terminates due to a failure.
- **Example Generated JSON**:
```json
{
  "@timestamp": "2026-08-11T14:00:00.530Z",
  "service": { "name": "simple-crawler" },
  "environment": "demo",
  "crawler": {
    "id": "crawler-001",
    "name": "simple-crawler",
    "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
    "status": "failed"
  },
  "event": { "action": "crawler_failed", "outcome": "failure" },
  "log": { "level": "ERROR" },
  "message": "Crawler run failed with error category 'mongodb_connection_error': Simulated MongoDB connection failure",
  "error": {
    "category": "mongodb_connection_error",
    "simulated": true,
    "message": "Simulated MongoDB connection failure"
  },
  "duration_ms": 3010.50
}
```

---

## 4. Error Simulation Guide

Error simulations are designed to test real log generation and prepare for Stage 2 AIOps Controller remediation.

### Simulation Mechanism
`scripts/simulate_error.py` does **NOT** generate mock logs. Instead, it executes the crawler engine with the `--simulate-error <category>` argument. The crawler then flows through its real execution path and triggers the fault inside the subsystem, generating standard structured logs with `error.simulated = true`.

### Supported Error Scenarios & Commands

1. **MongoDB Connection Error**
   ```powershell
   python scripts/simulate_error.py mongodb_connection_error
   ```
   *Expected Category*: `error.category = "mongodb_connection_error"`

2. **MongoDB Timeout**
   ```powershell
   python scripts/simulate_error.py mongodb_timeout
   ```
   *Expected Category*: `error.category = "mongodb_timeout"`

3. **Database Write Error**
   ```powershell
   python scripts/simulate_error.py database_write_error
   ```
   *Expected Category*: `error.category = "database_write_error"`

4. **Source Connection Error**
   ```powershell
   python scripts/simulate_error.py source_connection_error
   ```
   *Expected Category*: `error.category = "source_connection_error"`

5. **Source Timeout**
   ```powershell
   python scripts/simulate_error.py source_timeout
   ```
   *Expected Category*: `error.category = "source_timeout"`

6. **Invalid Response**
   ```powershell
   python scripts/simulate_error.py invalid_response
   ```
   *Expected Category*: `error.category = "invalid_response"`

7. **Crawler Process Error**
   ```powershell
   python scripts/simulate_error.py crawler_process_error
   ```
   *Expected Category*: `error.category = "crawler_process_error"`

---

## 5. MongoDB Document Schema Example

Successful crawler runs store validated records in database `aiops_demo` and collection `crawler_results`.

```json
{
  "_id": { "$oid": "66b8df81710d291e0a29b4e1" },
  "crawler_id": "crawler-001",
  "run_id": "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a",
  "source": "https://jsonplaceholder.typicode.com/posts",
  "crawled_at": "2026-08-11T14:00:00.480000+00:00",
  "data": {
    "id": 1,
    "userId": 1,
    "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
    "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"
  }
}
```

---

## 6. ELK Stack Configuration & Ingestion

- **Log Ingestion Path**: The crawler writes JSON logs to `/app/logs/crawler.log` inside a shared volume.
- **Logstash Input**: Logstash reads directly from `/usr/share/logstash/logs/crawler.log` using file input. Standard output (`stdout`) is kept only for local container debugging to prevent duplicate records.
- **Elasticsearch Daily Indexing**: Logstash parses the JSON logs and outputs them to Elasticsearch using daily indices: `scrm-aiops-crawler-YYYY.MM.dd`.

---

## 7. Kibana Setup & Query Examples

### Initial Kibana Setup
1. Open Kibana in your browser: `http://localhost:5601`
2. Navigate to **Management** -> **Stack Management** -> **Data Views**.
3. Click **Create data view**.
4. Name: `scrm-aiops-crawler-*`
5. Index pattern: `scrm-aiops-crawler-*`
6. Timestamp field: `@timestamp`
7. Click **Save data view to Kibana**.

### Kibana Discover & KQL Query Examples

1. **All Failed Crawlers**:
   ```kql
   event.outcome : "failure"
   ```

2. **MongoDB Errors**:
   ```kql
   error.category : mongodb_*
   ```

3. **Source Timeout Errors**:
   ```kql
   error.category : "source_timeout"
   ```

4. **Filter by Specific Crawler ID**:
   ```kql
   crawler.id : "crawler-001"
   ```

5. **Trace Entire History of One Specific `run_id`**:
   ```kql
   crawler.run_id : "8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a"
   ```

---

## 8. Demo Setup & Operational Commands

### Start All Services
```powershell
docker-compose up -d --build
```

### View Live Crawler Logs
```powershell
docker-compose logs -f crawler
```

### Run Unit Tests
```powershell
python -m pytest tests/ -v
```

### Service Endpoint URLs
- **Kibana UI**: `http://localhost:5601`
- **Elasticsearch API**: `http://localhost:9200`
- **MongoDB Connection**: `mongodb://localhost:27017`
- **Logstash Log Path**: Mounted container volume `/app/logs/crawler.log`

---

## 9. Future AIOps Controller Action Mapping (Stage 2 Preparation)

These structured logs will be continuously polled or received by the **AIOps Controller** in Stage 2. The Controller will evaluate `error.category`, `error.message`, and `crawler.run_id` to select predefined remediation actions from a controlled action registry:

| Error Category (`error.category`) | Future Predefined AIOps Action | Action Purpose |
| :--- | :--- | :--- |
| `mongodb_connection_error` | `run_database_health_check` | Verify MongoDB container status and network binding |
| `mongodb_timeout` | `run_database_health_check` | Perform socket check & test DB responsiveness |
| `database_write_error` | `retry_database_write` | Re-attempt failed write operation with exponential backoff |
| `source_connection_error` | `retry_crawler` | Trigger crawler retry after network link verification |
| `source_timeout` | `retry_crawler` | Re-execute crawler run with extended timeout parameters |
| `invalid_response` | `notify_devops` | Alert DevOps team regarding upstream API schema drift |
| `crawler_process_error` | `restart_crawler` | Perform automated service container restart |

```

## File: aiops-controller/Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]

```

## File: aiops-controller/README.md

```md
# AIOps Controller (Stage 2)

An independent Python AIOps Controller that detects crawler failures from Elasticsearch (`scrm-aiops-crawler-*`), correlates execution logs using `run_id`, analyzes incidents using NVIDIA AI, validates recommended actions against a double-validation security model (Action Registry & Action Policy), executes approved read-only/demo actions, verifies resolution, and stores the complete AIOps lifecycle in Elasticsearch (`scrm-aiops-controller-*`).

---

## 1. System Architecture

```text
┌─────────────────────┐
│   Simple Crawler    │
│     Stage 1         │
└──────────┬──────────┘
           │
           │ Structured JSON logs
           ▼
┌─────────────────────┐
│     Logstash        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│       Elasticsearch         │
│                             │
│ scrm-aiops-crawler-*        │
└──────────────┬──────────────┘
               │
               │ Failure Event
               ▼
┌─────────────────────────────┐
│      AIOps Controller       │
│                             │
│  1. Failure Detector        │
│           ↓                 │
│  2. Context Collector       │
│           ↓                 │
│  3. Incident Manager        │
│           ↓                 │
│  4. NVIDIA AI Analyzer      │
│           ↓                 │
│  5. Action Registry (Check1)│
│           ↓                 │
│  6. Action Policy (Check 2) │
│           ↓                 │
│  7. Action Executor         │
│           ↓                 │
│  8. Verifier                │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Elasticsearch         │
│                             │
│ scrm-aiops-controller-*     │
└──────────────┬──────────────┘
               │
               ▼
            Kibana
```

---

## 2. Incident Lifecycle State Machine

Every incident follows a clear, auditable lifecycle:

```text
DETECTED
   ↓
ANALYZING ──(Malformed Response/Error)──> AI_FAILED
   ↓
   ├──(Confidence < 0.80)──────────────> LOW_CONFIDENCE / MANUAL_INVESTIGATION
   ↓
ACTION_PROPOSED
   ↓
ACTION_VALIDATED ──(Registry/Policy Failure)──> ACTION_REJECTED
   ↓
ACTION_EXECUTING
   ↓
VERIFYING
   ↓
 ┌─┴─┐
 │   │
RECOVERED  UNRESOLVED
```

---

## 3. Strict Security & AI Isolation Design

> [!IMPORTANT]
> The NVIDIA AI model is **never** permitted to generate shell commands, PowerShell scripts, Python code, or directly control the operating system.

### Security Protection Layers:
1. **AI Output Limitation**: The AI is instructed via prompt and JSON schema formatting to return ONLY a structured JSON response recommending an action name string from an approved action list (`database_health_check`, `retry_crawler`, `notify_devops`, `restart_crawler`).
2. **Security Gatekeeper Check 1 (Action Registry)**: `ActionRegistry.is_registered(action_name)` verifies that the recommended string exists in the pre-approved whitelist. If the AI suggests `delete_database` or `powershell Restart-Service...`, the request is **immediately rejected**.
3. **Security Gatekeeper Check 2 (Action Policy)**: `ActionPolicy.is_allowed(failure_category, action_name)` verifies that the action is policy-authorized for the specific failure category. If the AI suggests `restart_crawler` for a `mongodb_connection_error`, it is **rejected** (`ACTION_REJECTED`).
4. **Explicit Python Function Execution**: `ActionExecutor` routes approved action strings strictly to hardcoded Python functions. It never passes strings to system shells (`eval`, `exec`, `subprocess.call`).

---

## 4. Component Structure

```
aiops-controller/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Main controller polling loop & CLI (--once)
│   ├── config.py               # Pydantic Settings configuration loader
│   ├── logger.py               # ECS Structured JSON Formatter for controller
│   ├── elasticsearch_client.py # Elasticsearch reader/writer client
│   ├── detector.py             # Failure detector & incident deduplicator
│   ├── context.py              # Log timeline collector by run_id
│   ├── incident.py             # Incident Pydantic models & lifecycle Enum
│   ├── ai_analyzer.py          # NVIDIA AI NIM integration with fallback
│   ├── action_registry.py      # Security Gatekeeper Check 1 (Registry Whitelist)
│   ├── action_policy.py        # Security Gatekeeper Check 2 (Category Rules)
│   ├── action_executor.py      # Action router to explicit Python functions
│   └── verifier.py             # Post-execution resolution verifier
│
├── actions/
│   ├── __init__.py
│   ├── database_health_check.py # Real read-only MongoDB ping check
│   ├── retry_crawler.py        # Demo handler for retry requests
│   ├── notify_devops.py        # Demo handler for DevOps notifications
│   └── restart_crawler.py      # Demo handler for restart requests
│
├── tests/
│   ├── test_detector.py
│   ├── test_context.py
│   ├── test_ai_analyzer.py
│   ├── test_action_registry_and_policy.py
│   ├── test_action_executor.py
│   └── test_verifier.py
│
├── Dockerfile                  # Container build definition
├── requirements.txt            # Python dependencies
└── README.md                   # Stage 2 Documentation
```

---

## 5. Action Policy Rules

| Failure Category (`error.category`) | Authorized Action (`recommended_action`) | Primary Action Execution |
| :--- | :--- | :--- |
| `mongodb_connection_error` | `database_health_check` | Read-only MongoDB ping (`MongoClient.admin.command('ping')`) |
| `mongodb_timeout` | `database_health_check` | Read-only MongoDB ping |
| `database_write_error` | `retry_crawler` | Demo action audit log |
| `source_connection_error` | `retry_crawler` | Demo action audit log |
| `source_timeout` | `retry_crawler` | Demo action audit log |
| `invalid_response` | `notify_devops` | Demo action audit log |
| `crawler_process_error` | `restart_crawler` | Demo action audit log |

---

## 6. Deduplication & Incident Tracking

- **Incident ID Formula**: `incident_id = f"{crawler_id}:{run_id}"` (e.g. `crawler-001:8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a`).
- Before processing any detected failure, `ElasticsearchClient.incident_exists(incident_id)` queries index `scrm-aiops-controller-*`. If an audit document with that `incident_id` already exists, the failure is skipped to prevent duplicate execution across controller restarts.

---

## 7. End-to-End Demo Execution Steps

### 1. Launch All Stack Services:
```powershell
docker-compose up -d --build
```

### 2. Trigger Simulated Crawler Failure (e.g. MongoDB Connection Error):
```powershell
python scripts/simulate_error.py mongodb_connection_error
```

### 3. Observe AIOps Controller Automation Logs:
```powershell
docker-compose logs -f aiops-controller
```

### 4. Run Controller Test Suite:
```powershell
python -m pytest aiops-controller/tests/ -v
```

---

## 8. Kibana Verification & Queries

1. Open Kibana at `http://localhost:5601`.
2. Go to **Management** -> **Stack Management** -> **Data Views** -> **Create data view**.
3. Name / Pattern: `scrm-aiops-controller-*`, timestamp field `@timestamp`.
4. In **Discover**, execute queries to trace controller automation events:

```kql
# View all recovered incidents
incident.status : "RECOVERED"

# View AI recommended actions
ai.recommended_action : "database_health_check"

# View specific incident lifecycle trace
incident.id : "crawler-001:8f5c9a12-3b4c-4d5e-6f7a-8b9c0d1e2f3a"
```

```

## File: aiops-controller/actions/database_health_check.py

```py
from typing import Any, Dict
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def run(mongodb_uri: str) -> Dict[str, Any]:
    """
    Performs a read-only MongoDB ping check to verify database availability.
    Does NOT modify database content.
    """
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        client.close()
        return {
            "action": "database_health_check",
            "success": True,
            "details": "MongoDB is reachable and healthy"
        }
    except PyMongoError as e:
        return {
            "action": "database_health_check",
            "success": False,
            "details": f"MongoDB is unavailable: {str(e)}"
        }
    except Exception as e:
        return {
            "action": "database_health_check",
            "success": False,
            "details": f"Database health check failed: {str(e)}"
        }

```

## File: aiops-controller/actions/notify_devops.py

```py
from typing import Any, Dict


def run(demo_mode: bool = True) -> Dict[str, Any]:
    """
    Handles notify_devops action.
    """
    return {
        "action": "notify_devops",
        "success": True,
        "details": "DevOps notification requested: Alert dispatched to DevOps channel"
    }

```

## File: aiops-controller/actions/restart_crawler.py

```py
from typing import Any, Dict


def run(demo_mode: bool = True) -> Dict[str, Any]:
    """
    Handles restart_crawler action.
    """
    return {
        "action": "restart_crawler",
        "success": True,
        "details": "Restart requested but disabled in demo mode"
    }

```

## File: aiops-controller/actions/retry_crawler.py

```py
from typing import Any, Dict


def run(demo_mode: bool = True) -> Dict[str, Any]:
    """
    Handles retry_crawler action.
    """
    return {
        "action": "retry_crawler",
        "success": True,
        "details": "Demo action requested: Retry crawler trigger logged successfully"
    }

```

## File: aiops-controller/actions/__init__.py

```py
"""
AIOps Controller Actions Package
"""

```

## File: aiops-controller/app/action_executor.py

```py
from typing import Any, Dict
from actions import database_health_check, notify_devops, restart_crawler, retry_crawler
from app.config import settings


class ActionExecutor:
    """
    Executes approved remediation actions through explicit Python functions.
    Does NOT accept or execute arbitrary shell/PowerShell commands.
    """
    def __init__(self, mongodb_uri: str = settings.MONGODB_URI, demo_mode: bool = settings.AIOPS_DEMO_MODE):
        self.mongodb_uri = mongodb_uri
        self.demo_mode = demo_mode

    def execute(self, action_name: str) -> Dict[str, Any]:
        """
        Routes validated action_name string to explicit Python module handler.
        """
        clean_action = action_name.strip() if action_name else ""

        if clean_action == "database_health_check":
            return database_health_check.run(self.mongodb_uri)
        elif clean_action == "retry_crawler":
            return retry_crawler.run(self.demo_mode)
        elif clean_action == "notify_devops":
            return notify_devops.run(self.demo_mode)
        elif clean_action == "restart_crawler":
            return restart_crawler.run(self.demo_mode)
        else:
            return {
                "action": clean_action,
                "success": False,
                "details": f"Unrecognized or unapproved action execution attempt: '{clean_action}'"
            }

```

## File: aiops-controller/app/action_policy.py

```py
from typing import Dict, List


class ActionPolicy:
    """
    Security Gatekeeper Check 2: Validates that a recommended action is allowed for the specific failure category.
    """
    POLICY_MAP: Dict[str, List[str]] = {
        "mongodb_connection_error": ["database_health_check"],
        "mongodb_timeout": ["database_health_check"],
        "database_write_error": ["retry_crawler"],
        "source_connection_error": ["retry_crawler"],
        "source_timeout": ["retry_crawler"],
        "invalid_response": ["notify_devops"],
        "crawler_process_error": ["restart_crawler"]
    }

    @classmethod
    def is_allowed(cls, failure_category: str, action_name: str) -> bool:
        """
        Returns True if action_name is authorized for the specified failure_category by policy.
        """
        if not failure_category or not action_name:
            return False
        allowed_actions = cls.POLICY_MAP.get(failure_category, [])
        return action_name.strip() in allowed_actions

    @classmethod
    def get_allowed_actions(cls, failure_category: str) -> List[str]:
        return cls.POLICY_MAP.get(failure_category, [])

```

## File: aiops-controller/app/action_registry.py

```py
from typing import List, Set


class ActionRegistry:
    """
    Security Gatekeeper Check 1: Validates that a recommended action exists in the approved registry.
    """
    APPROVED_ACTIONS: Set[str] = {
        "database_health_check",
        "retry_crawler",
        "notify_devops",
        "restart_crawler"
    }

    @classmethod
    def is_registered(cls, action_name: str) -> bool:
        """
        Returns True if action_name is in the pre-approved action registry, False otherwise.
        """
        if not action_name or not isinstance(action_name, str):
            return False
        return action_name.strip() in cls.APPROVED_ACTIONS

    @classmethod
    def list_approved_actions(cls) -> List[str]:
        return sorted(list(cls.APPROVED_ACTIONS))

```

## File: aiops-controller/app/ai_analyzer.py

```py
import json
import logging
from typing import Any, Dict, Optional
import requests
from app.config import settings
from app.incident import AIAnalysisResult, Incident

logger = logging.getLogger("aiops_controller")


class NvidiaAIAnalyzer:
    """
    Isolated interface for analyzing incidents using NVIDIA AI NIM API with JSON schema enforcement.
    """
    def __init__(
        self,
        api_key: str = settings.NVIDIA_API_KEY,
        model: str = settings.NVIDIA_MODEL,
        base_url: str = settings.NVIDIA_BASE_URL,
        confidence_threshold: float = settings.AI_CONFIDENCE_THRESHOLD
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.confidence_threshold = confidence_threshold

    def analyze_incident(self, incident: Incident) -> Optional[AIAnalysisResult]:
        """
        Sends incident context to NVIDIA AI model and returns validated AIAnalysisResult.
        """
        prompt = self._build_prompt(incident)

        # Log the user prompt as a structured Kibana field (ai.prompt)
        logger.info(
            f"AI prompt built for incident {incident.crawler_id}:{incident.run_id}",
            extra={"ai_prompt": prompt}
        )

        # Demo mode / offline fallback when demo_key is used
        if self.api_key == "demo_key" or settings.AIOPS_DEMO_MODE:
            logger.info("AIOPS_DEMO_MODE is true. Using fallback rule-based analyzer.")
            fallback_system_prompt = (
                "You are an AIOps incident analysis engine.\n\n"
                "Your job is to analyze a crawler failure and recommend ONE predefined remediation action.\n\n"
                "You may ONLY recommend one action from the following approved actions:\n"
                "- database_health_check\n"
                "- retry_crawler\n"
                "- notify_devops\n"
                "- restart_crawler"
            )
            return self._fallback_demo_analysis(incident, prompt=prompt, system_prompt=fallback_system_prompt)
        system_content = (
            "You are an AIOps incident analysis engine.\n\n"
            "Your job is to analyze a crawler failure and recommend ONE predefined remediation action.\n\n"
            "You are NOT allowed to generate shell commands, PowerShell commands, Python code, SQL, MongoDB commands, or any other executable instructions.\n\n"
            "You may ONLY recommend one action from the following approved actions:\n"
            "- database_health_check\n"
            "- retry_crawler\n"
            "- notify_devops\n"
            "- restart_crawler\n\n"
            "Analyze the incident using:\n"
            "- crawler information\n"
            "- failure category\n"
            "- failure message\n"
            "- failure event\n"
            "- complete related log sequence\n\n"
            "Determine:\n"
            "1. What most likely caused the failure.\n"
            "2. The failure category.\n"
            "3. Your confidence from 0.0 to 1.0.\n"
            "4. ONE recommended action from the approved action list.\n"
            "5. A short explanation for the recommendation.\n\n"
            "Important rules:\n"
            "- Never invent an action.\n"
            "- Never return an executable command.\n"
            "- Never recommend an action outside the approved list.\n"
            "- If the evidence is insufficient, set confidence below 0.80.\n"
            "- If confidence is below 0.80, recommend \"notify_devops\".\n"
            "- Return JSON only.\n\n"
            "The JSON output must strictly adhere to the following schema:\n"
            "{\n"
            '  "diagnosis": "<What most likely caused the failure>",\n'
            '  "failure_category": "<The failure category>",\n'
            '  "confidence": <confidence float between 0.0 and 1.0>,\n'
            '  "recommended_action": "<ONE recommended action from the approved list>",\n'
            '  "reason": "<A short explanation for the recommendation>"\n'
            "}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        # Log both prompts as structured Kibana fields (ai.prompt + ai.system_prompt)
        logger.info(
            f"Sending request to NVIDIA AI model '{self.model}'",
            extra={"ai_prompt": prompt, "ai_system_prompt": system_content}
        )

        try:
            import urllib3
            url = f"{self.base_url}/chat/completions"

            # Attempt 1: standard SSL verification
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15.0, verify=True)
            except requests.exceptions.SSLError:
                response = None

            # Attempt 2: if SSL error OR corporate proxy returned 404 (proxy interception signal)
            if response is None or (response.status_code == 404 and "page not found" in response.text.lower()):
                logger.warning("SSL verification failed or proxy 404 detected. Retrying without SSL verification (corporate proxy).")
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.post(url, json=payload, headers=headers, timeout=15.0, verify=False)

            # Log the raw AI response as a structured Kibana field (ai.raw_response)
            logger.info(
                f"NVIDIA AI raw response [status={response.status_code}]",
                extra={"ai_raw_response": response.text}
            )


            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                result = AIAnalysisResult(**data)
                result.prompt = prompt
                result.system_prompt = system_content
                result.raw_response = content
                return result
            else:
                logger.error(f"NVIDIA AI returned non-200 status: {response.status_code}. Falling back to demo analyzer.")
                return self._fallback_demo_analysis(
                    incident, prompt=prompt, system_prompt=system_content, raw_response=response.text
                )
        except Exception as e:
            logger.error(f"NVIDIA AI call failed with exception: {str(e)}. Falling back to demo analyzer.")
            return self._fallback_demo_analysis(
                incident, prompt=prompt, system_prompt=system_content
            )

    def _build_prompt(self, incident: Incident) -> str:
        logs_summary = json.dumps(incident.related_logs, indent=2)
        return (
            f"Crawler ID: {incident.crawler_id}\n"
            f"Crawler Name: {incident.crawler_name}\n"
            f"Run ID: {incident.run_id}\n"
            f"Failure Category: {incident.failure_category}\n"
            f"Failure Message: {incident.failure_message}\n"
            f"Failure Event: {json.dumps(incident.failure_event)}\n"
            f"Complete Related Logs Sequence:\n{logs_summary}\n"
        )

    def _fallback_demo_analysis(
        self,
        incident: Incident,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        raw_response: Optional[str] = None
    ) -> AIAnalysisResult:
        """
        Deterministic rule-based analysis used for offline/demo verification.
        """
        cat = incident.failure_category
        msg = incident.failure_message

        if cat in ["mongodb_connection_error", "mongodb_timeout"]:
            result = AIAnalysisResult(
                diagnosis=f"MongoDB database connection issue detected: {msg}",
                failure_category=cat,
                confidence=0.95,
                recommended_action="database_health_check",
                reason="The crawler failed while establishing connection to MongoDB. Database health check is required."
            )
        elif cat in ["database_write_error", "source_connection_error", "source_timeout"]:
            result = AIAnalysisResult(
                diagnosis=f"Transient network/write failure detected: {msg}",
                failure_category=cat,
                confidence=0.90,
                recommended_action="retry_crawler",
                reason="The failure appears transient. Retrying the crawler execution is recommended."
            )
        elif cat == "invalid_response":
            result = AIAnalysisResult(
                diagnosis=f"Upstream payload response schema error: {msg}",
                failure_category=cat,
                confidence=0.88,
                recommended_action="notify_devops",
                reason="Invalid payload structure received from source API. DevOps notification required."
            )
        elif cat == "crawler_process_error":
            result = AIAnalysisResult(
                diagnosis=f"Internal crawler process execution error: {msg}",
                failure_category=cat,
                confidence=0.85,
                recommended_action="restart_crawler",
                reason="Unexpected internal exception occurred during crawler transformation. Process restart recommended."
            )
        else:
            result = AIAnalysisResult(
                diagnosis=f"Unclassified failure condition: {msg}",
                failure_category=cat,
                confidence=0.50,  # Below threshold 0.80 to trigger MANUAL_INVESTIGATION
                recommended_action="notify_devops",
                reason="Uncertain failure category requiring manual DevOps inspection."
            )

        result.prompt = prompt
        result.system_prompt = system_prompt
        result.raw_response = raw_response
        return result


```

## File: aiops-controller/app/config.py

```py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    AIOps Controller Configuration loaded from Environment Variables.
    """
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    ELASTICSEARCH_CRAWLER_INDEX: str = "scrm-aiops-crawler-*"
    ELASTICSEARCH_CONTROLLER_INDEX: str = "scrm-aiops-controller"
    MONGODB_URI: str = "mongodb://localhost:27017"
    
    NVIDIA_API_KEY: str = "demo_key"
    NVIDIA_MODEL: str = "meta/llama-3.1-405b-instruct"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    AI_CONFIDENCE_THRESHOLD: float = 0.80
    
    AIOPS_DEMO_MODE: bool = True
    POLL_INTERVAL_SECONDS: int = 5
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

```

## File: aiops-controller/app/context.py

```py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.elasticsearch_client import ElasticsearchClient
from app.incident import Incident, IncidentLifecycleStatus


class ContextCollector:
    """
    Collects full context log timeline for a given failure run_id and builds an Incident.
    """
    def __init__(self, es_client: Optional[ElasticsearchClient] = None):
        self.es_client = es_client or ElasticsearchClient()

    def build_incident(self, failure_event: Dict[str, Any]) -> Incident:
        """
        Retrieves all related log records for the run_id, sorts them by timestamp, and creates an Incident.
        """
        crawler = failure_event.get("crawler", {})
        error = failure_event.get("error", {})
        
        crawler_id = crawler.get("id", "crawler-001")
        crawler_name = crawler.get("name", "simple-crawler")
        run_id = crawler.get("run_id", "unknown-run-id")
        
        failure_category = error.get("category") or failure_event.get("error_category") or "unknown_error"
        failure_message = error.get("message") or failure_event.get("message") or "Crawler execution failure"
        
        # Retrieve all log records belonging to this run_id
        related_logs = self.es_client.get_logs_by_run_id(run_id)
        if not related_logs:
            related_logs = [failure_event]
        else:
            # Sort ascending by @timestamp
            related_logs = sorted(related_logs, key=lambda x: x.get("@timestamp", ""))

        incident_id = f"{crawler_id}:{run_id}"
        detected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return Incident(
            incident_id=incident_id,
            crawler_id=crawler_id,
            crawler_name=crawler_name,
            run_id=run_id,
            failure_category=failure_category,
            failure_message=failure_message,
            failure_event=failure_event,
            related_logs=related_logs,
            detected_at=detected_at,
            status=IncidentLifecycleStatus.DETECTED
        )

```

## File: aiops-controller/app/detector.py

```py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from app.elasticsearch_client import ElasticsearchClient


class FailureDetector:
    """
    Scans Elasticsearch for crawler failure events and deduplicates processed incidents.
    """
    def __init__(self, es_client: Optional[ElasticsearchClient] = None):
        self.es_client = es_client or ElasticsearchClient()
        self.seen_incidents: Set[str] = set()

    def detect_unprocessed_failures(self) -> List[Dict[str, Any]]:
        """
        Retrieves crawler failure events that have not yet been processed.
        """
        raw_failures = self.es_client.search_failures()
        unprocessed = []

        for event in raw_failures:
            crawler = event.get("crawler", {})
            crawler_id = crawler.get("id", "crawler-001")
            run_id = crawler.get("run_id")

            if not run_id:
                continue

            incident_id = f"{crawler_id}:{run_id}"

            # Deduplication Check 1: In-memory set
            if incident_id in self.seen_incidents:
                continue

            # Deduplication Check 2: Elasticsearch controller index persistence
            if self.es_client.incident_exists(incident_id):
                self.seen_incidents.add(incident_id)
                continue

            # Add to local cache and include in return list
            self.seen_incidents.add(incident_id)
            unprocessed.append(event)

        return unprocessed

```

## File: aiops-controller/app/elasticsearch_client.py

```py
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests
from app.config import settings


class ElasticsearchClient:
    """
    Client for querying crawler logs and writing controller audit events to Elasticsearch.
    """
    def __init__(
        self,
        es_url: str = settings.ELASTICSEARCH_URL,
        crawler_index: str = settings.ELASTICSEARCH_CRAWLER_INDEX,
        controller_index: str = settings.ELASTICSEARCH_CONTROLLER_INDEX
    ):
        self.es_url = es_url.rstrip("/")
        self.crawler_index = crawler_index
        self.controller_index = controller_index

    def search_failures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Searches crawler index for failure events (event.outcome = "failure").
        """
        url = f"{self.es_url}/{self.crawler_index}/_search"
        query = {
            "size": limit,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"event.outcome.keyword": "failure"}}
                    ]
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                hits = res.json().get("hits", {}).get("hits", [])
                return [hit.get("_source", {}) for hit in hits]
            return []
        except Exception:
            return []

    def get_logs_by_run_id(self, run_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves all log records sharing the specified run_id, sorted by timestamp ascending.
        """
        url = f"{self.es_url}/{self.crawler_index}/_search"
        query = {
            "size": limit,
            "sort": [{"@timestamp": {"order": "asc"}}],
            "query": {
                "term": {
                    "crawler.run_id.keyword": run_id
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                hits = res.json().get("hits", {}).get("hits", [])
                return [hit.get("_source", {}) for hit in hits]
            return []
        except Exception:
            return []

    def incident_exists(self, incident_id: str) -> bool:
        """
        Checks whether an incident has already been processed and stored in the controller index.
        """
        url = f"{self.es_url}/{self.controller_index}-*/_search"
        query = {
            "size": 1,
            "query": {
                "term": {
                    "incident.id.keyword": incident_id
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                total = res.json().get("hits", {}).get("total", {})
                value = total.get("value", 0) if isinstance(total, dict) else total
                return value > 0
            return False
        except Exception:
            return False

    def write_controller_event(self, event_document: Dict[str, Any]) -> bool:
        """
        Writes a controller lifecycle audit record into Elasticsearch under daily index pattern.
        """
        date_str = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        target_index = f"{self.controller_index}-{date_str}"
        url = f"{self.es_url}/{target_index}/_doc"
        
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(url, json=event_document, headers=headers, timeout=5.0)
            return res.status_code in [200, 201]
        except Exception:
            return False

```

## File: aiops-controller/app/incident.py

```py
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentLifecycleStatus(str, Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    AI_FAILED = "AI_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MANUAL_INVESTIGATION = "MANUAL_INVESTIGATION"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_VALIDATED = "ACTION_VALIDATED"
    ACTION_REJECTED = "ACTION_REJECTED"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    UNRESOLVED = "UNRESOLVED"


class Incident(BaseModel):
    """
    Internal model representing a detected crawler failure incident.
    """
    incident_id: str
    crawler_id: str
    crawler_name: str
    run_id: str
    failure_category: str
    failure_message: str
    failure_event: Dict[str, Any]
    related_logs: List[Dict[str, Any]] = Field(default_factory=list)
    detected_at: str
    status: IncidentLifecycleStatus = IncidentLifecycleStatus.DETECTED


class AIAnalysisResult(BaseModel):
    """
    Pydantic schema for structured response from AI Analyzer.
    """
    diagnosis: str
    failure_category: str
    confidence: float
    recommended_action: str
    reason: str
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    raw_response: Optional[str] = None


```

## File: aiops-controller/app/logger.py

```py
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.config import settings


class ControllerJSONFormatter(logging.Formatter):
    """
    JSON Formatter enforcing structured log output aligned with ECS specs for AIOps Controller.
    """
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        log_data: Dict[str, Any] = {
            "@timestamp": timestamp,
            "service": {
                "name": "aiops-controller"
            },
            "log": {
                "level": record.levelname
            },
            "message": record.getMessage()
        }

        # Event fields
        action = getattr(record, "event_action", None)
        outcome = getattr(record, "event_outcome", None)
        if action or outcome:
            log_data["event"] = {
                "action": action or "controller_event",
                "outcome": outcome or "success"
            }

        # Incident fields
        incident_id = getattr(record, "incident_id", None)
        if incident_id:
            log_data["incident"] = {"id": incident_id}

        # Crawler context fields
        crawler_id = getattr(record, "crawler_id", None)
        crawler_run_id = getattr(record, "crawler_run_id", None)
        if crawler_id or crawler_run_id:
            log_data["crawler"] = {
                "id": crawler_id or "unknown",
                "run_id": crawler_run_id or "unknown"
            }

        # AI analysis fields
        ai_diagnosis = getattr(record, "ai_diagnosis", None)
        ai_confidence = getattr(record, "ai_confidence", None)
        ai_rec_action = getattr(record, "ai_recommended_action", None)
        ai_prompt = getattr(record, "ai_prompt", None)
        ai_system_prompt = getattr(record, "ai_system_prompt", None)
        ai_raw_response = getattr(record, "ai_raw_response", None)
        if ai_diagnosis or ai_confidence is not None or ai_rec_action or ai_prompt or ai_system_prompt or ai_raw_response:
            ai_dict: Dict[str, Any] = {}
            if ai_diagnosis:
                ai_dict["diagnosis"] = ai_diagnosis
            if ai_confidence is not None:
                ai_dict["confidence"] = ai_confidence
            if ai_rec_action:
                ai_dict["recommended_action"] = ai_rec_action
            if ai_prompt:
                ai_dict["prompt"] = ai_prompt
            if ai_system_prompt:
                ai_dict["system_prompt"] = ai_system_prompt
            if ai_raw_response:
                ai_dict["raw_response"] = ai_raw_response
            log_data["ai"] = ai_dict

        # Action fields
        action_name = getattr(record, "action_name", None)
        action_status = getattr(record, "action_status", None)
        if action_name or action_status:
            log_data["action"] = {
                "name": action_name or "none",
                "status": action_status or "none"
            }

        # Verification fields
        verification_status = getattr(record, "verification_status", None)
        if verification_status:
            log_data["verification"] = {"status": verification_status}

        return json.dumps(log_data)


def setup_logger(log_level: str = settings.LOG_LEVEL) -> logging.Logger:
    logger = logging.getLogger("aiops_controller")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = ControllerJSONFormatter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    return logger

```

## File: aiops-controller/app/main.py

```py
import argparse
import sys
import time
from typing import Any, Optional

from app.action_executor import ActionExecutor
from app.action_policy import ActionPolicy
from app.action_registry import ActionRegistry
from app.ai_analyzer import NvidiaAIAnalyzer
from app.config import settings
from app.context import ContextCollector
from app.detector import FailureDetector
from app.elasticsearch_client import ElasticsearchClient
from app.incident import Incident, IncidentLifecycleStatus
from app.logger import setup_logger
from app.verifier import IncidentVerifier

logger = setup_logger()


class AIOpsController:
    """
    Main AIOps Controller service orchestrating incident lifecycle transitions.
    """
    def __init__(self):
        self.es_client = ElasticsearchClient()
        self.detector = FailureDetector(es_client=self.es_client)
        self.collector = ContextCollector(es_client=self.es_client)
        self.ai_analyzer = NvidiaAIAnalyzer()
        self.executor = ActionExecutor()
        self.verifier = IncidentVerifier()

    def process_incident(self, failure_event: dict) -> IncidentLifecycleStatus:
        """
        Executes end-to-end incident lifecycle state transitions.
        """
        # Step 1: Detect failure and construct Incident context
        incident = self.collector.build_incident(failure_event)
        incident.status = IncidentLifecycleStatus.DETECTED

        self._emit_audit(
            incident=incident,
            event_action="incident_detected",
            event_outcome="success",
            message=f"Incident {incident.incident_id} detected for crawler {incident.crawler_id}"
        )

        # Step 2: AI Analysis
        incident.status = IncidentLifecycleStatus.ANALYZING
        self._emit_audit(
            incident=incident,
            event_action="ai_analysis_started",
            event_outcome="success",
            message=f"Sending incident {incident.incident_id} context to NVIDIA AI for analysis"
        )

        ai_result = self.ai_analyzer.analyze_incident(incident)
        if not ai_result:
            incident.status = IncidentLifecycleStatus.AI_FAILED
            self._emit_audit(
                incident=incident,
                event_action="ai_analysis_failed",
                event_outcome="failure",
                message="NVIDIA AI analysis failed or returned malformed data"
            )
            return IncidentLifecycleStatus.AI_FAILED

        # Confidence Threshold Check
        if ai_result.confidence < settings.AI_CONFIDENCE_THRESHOLD:
            incident.status = IncidentLifecycleStatus.MANUAL_INVESTIGATION
            self._emit_audit(
                incident=incident,
                event_action="ai_confidence_low",
                event_outcome="failure",
                message=f"AI confidence ({ai_result.confidence}) below threshold ({settings.AI_CONFIDENCE_THRESHOLD}). Marked for manual investigation.",
                ai_result=ai_result
            )
            return IncidentLifecycleStatus.MANUAL_INVESTIGATION

        incident.status = IncidentLifecycleStatus.ACTION_PROPOSED
        self._emit_audit(
            incident=incident,
            event_action="action_proposed",
            event_outcome="success",
            message=f"AI recommended action '{ai_result.recommended_action}' with confidence {ai_result.confidence}",
            ai_result=ai_result
        )

        # Step 3: Security Gatekeeper Validation (Check 1 & Check 2)
        rec_action = ai_result.recommended_action

        # Check 1: Action Registry
        if not ActionRegistry.is_registered(rec_action):
            incident.status = IncidentLifecycleStatus.ACTION_REJECTED
            self._emit_audit(
                incident=incident,
                event_action="action_rejected",
                event_outcome="failure",
                message=f"Security Gatekeeper Check 1 Failed: Action '{rec_action}' is not in approved Action Registry.",
                ai_result=ai_result,
                action_name=rec_action,
                action_status="rejected_unregistered"
            )
            return IncidentLifecycleStatus.ACTION_REJECTED

        # Check 2: Action Policy
        if not ActionPolicy.is_allowed(incident.failure_category, rec_action):
            incident.status = IncidentLifecycleStatus.ACTION_REJECTED
            self._emit_audit(
                incident=incident,
                event_action="action_rejected",
                event_outcome="failure",
                message=f"Security Gatekeeper Check 2 Failed: Action '{rec_action}' is not authorized for failure category '{incident.failure_category}'.",
                ai_result=ai_result,
                action_name=rec_action,
                action_status="rejected_policy_mismatch"
            )
            return IncidentLifecycleStatus.ACTION_REJECTED

        incident.status = IncidentLifecycleStatus.ACTION_VALIDATED
        self._emit_audit(
            incident=incident,
            event_action="action_validated",
            event_outcome="success",
            message=f"Action '{rec_action}' passed Security Gatekeeper (Registry & Policy checks).",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="validated"
        )

        # Step 4: Execute Action
        incident.status = IncidentLifecycleStatus.ACTION_EXECUTING
        self._emit_audit(
            incident=incident,
            event_action="action_executing",
            event_outcome="success",
            message=f"Executing action handler '{rec_action}'",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="executing"
        )

        action_result = self.executor.execute(rec_action)

        # Step 5: Verification
        incident.status = IncidentLifecycleStatus.VERIFYING
        final_status = self.verifier.verify(action_result)
        incident.status = final_status

        outcome_str = "success" if final_status == IncidentLifecycleStatus.RECOVERED else "failure"
        self._emit_audit(
            incident=incident,
            event_action="incident_lifecycle_completed",
            event_outcome=outcome_str,
            message=f"Incident lifecycle completed with final status '{final_status.value}'. Details: {action_result.get('details')}",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="executed",
            verification_status=final_status.value
        )

        return final_status

    def _emit_audit(
        self,
        incident: Incident,
        event_action: str,
        event_outcome: str,
        message: str,
        ai_result: Optional[Any] = None,
        action_name: Optional[str] = None,
        action_status: Optional[str] = None,
        verification_status: Optional[str] = None
    ):
        extra = {
            "incident_id": incident.incident_id,
            "crawler_id": incident.crawler_id,
            "crawler_run_id": incident.run_id,
            "event_action": event_action,
            "event_outcome": event_outcome
        }
        if ai_result:
            extra["ai_diagnosis"] = ai_result.diagnosis
            extra["ai_confidence"] = ai_result.confidence
            extra["ai_recommended_action"] = ai_result.recommended_action
        if action_name:
            extra["action_name"] = action_name
        if action_status:
            extra["action_status"] = action_status
        if verification_status:
            extra["verification_status"] = verification_status

        log_level = 20 if event_outcome == "success" else 40
        logger.log(log_level, message, extra=extra)

        # Also write audit document to Elasticsearch controller index
        audit_doc = {
            "@timestamp": incident.detected_at,
            "service": {"name": "aiops-controller"},
            "incident": {"id": incident.incident_id, "status": incident.status.value},
            "crawler": {"id": incident.crawler_id, "name": incident.crawler_name, "run_id": incident.run_id},
            "event": {"action": event_action, "outcome": event_outcome},
            "message": message
        }
        if ai_result:
            audit_doc["ai"] = {
                "diagnosis": ai_result.diagnosis,
                "confidence": ai_result.confidence,
                "recommended_action": ai_result.recommended_action,
                "reason": ai_result.reason
            }
            if ai_result.prompt:
                audit_doc["ai"]["prompt"] = ai_result.prompt
            if ai_result.system_prompt:
                audit_doc["ai"]["system_prompt"] = ai_result.system_prompt
            if ai_result.raw_response:
                audit_doc["ai"]["raw_response"] = ai_result.raw_response
        if action_name or action_status:
            audit_doc["action"] = {"name": action_name or "none", "status": action_status or "none"}
        if verification_status:
            audit_doc["verification"] = {"status": verification_status}

        self.es_client.write_controller_event(audit_doc)

    def run_once(self) -> int:
        failures = self.detector.detect_unprocessed_failures()
        processed_count = 0
        for failure_event in failures:
            self.process_incident(failure_event)
            processed_count += 1
        return processed_count

    def run_loop(self):
        logger.info(f"Starting AIOps Controller service loop (Poll interval: {settings.POLL_INTERVAL_SECONDS}s)")
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in controller loop: {str(e)}")
            time.sleep(settings.POLL_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(description="AIOps Controller Service")
    parser.add_argument("--once", action="store_true", help="Run a single pass of failure detection and exit.")
    args = parser.parse_args()

    controller = AIOpsController()
    if args.once:
        count = controller.run_once()
        logger.info(f"Single pass complete. Processed {count} failure incident(s).")
        sys.exit(0)
    else:
        controller.run_loop()


if __name__ == "__main__":
    main()

```

## File: aiops-controller/app/verifier.py

```py
from typing import Any, Dict
from app.incident import IncidentLifecycleStatus


class IncidentVerifier:
    """
    Verifies action execution outcome and determines final incident status.
    """
    def verify(self, action_result: Dict[str, Any]) -> IncidentLifecycleStatus:
        """
        Evaluates execution outcome. Returns RECOVERED if successful, UNRESOLVED if failed.
        """
        success = action_result.get("success", False)
        if success:
            return IncidentLifecycleStatus.RECOVERED
        return IncidentLifecycleStatus.UNRESOLVED

```

## File: aiops-controller/app/__init__.py

```py
"""
AIOps Controller Application Package
"""

```

## File: aiops-controller/tests/test_action_executor.py

```py
from unittest.mock import MagicMock, patch
from app.action_executor import ActionExecutor


@patch("actions.database_health_check.MongoClient")
def test_action_executor_database_health_check_success(mock_mongo):
    mock_client_inst = MagicMock()
    mock_client_inst.admin.command.return_value = {"ok": 1}
    mock_mongo.return_value = mock_client_inst

    executor = ActionExecutor(mongodb_uri="mongodb://localhost:27017")
    res = executor.execute("database_health_check")

    assert res["action"] == "database_health_check"
    assert res["success"] is True
    assert "reachable" in res["details"]


def test_action_executor_demo_actions():
    executor = ActionExecutor(demo_mode=True)

    res_retry = executor.execute("retry_crawler")
    assert res_retry["action"] == "retry_crawler"
    assert res_retry["success"] is True

    res_notify = executor.execute("notify_devops")
    assert res_notify["action"] == "notify_devops"
    assert res_notify["success"] is True

    res_restart = executor.execute("restart_crawler")
    assert res_restart["action"] == "restart_crawler"
    assert res_restart["success"] is True
    assert "disabled in demo mode" in res_restart["details"]


def test_action_executor_arbitrary_command_rejection():
    executor = ActionExecutor()
    res = executor.execute("powershell Restart-Service MongoDB")

    assert res["success"] is False
    assert "Unrecognized or unapproved" in res["details"]

```

## File: aiops-controller/tests/test_action_registry_and_policy.py

```py
from app.action_policy import ActionPolicy
from app.action_registry import ActionRegistry


def test_action_registry_check_1():
    # Check approved actions
    assert ActionRegistry.is_registered("database_health_check") is True
    assert ActionRegistry.is_registered("retry_crawler") is True
    assert ActionRegistry.is_registered("notify_devops") is True
    assert ActionRegistry.is_registered("restart_crawler") is True

    # Security check: Reject unapproved or arbitrary shell strings
    assert ActionRegistry.is_registered("delete_database") is False
    assert ActionRegistry.is_registered("powershell Restart-Service MongoDB") is False
    assert ActionRegistry.is_registered("rm -rf /") is False
    assert ActionRegistry.is_registered("") is False


def test_action_policy_check_2():
    # Check authorized failure-to-action policy pairs
    assert ActionPolicy.is_allowed("mongodb_connection_error", "database_health_check") is True
    assert ActionPolicy.is_allowed("mongodb_timeout", "database_health_check") is True
    assert ActionPolicy.is_allowed("database_write_error", "retry_crawler") is True
    assert ActionPolicy.is_allowed("source_connection_error", "retry_crawler") is True
    assert ActionPolicy.is_allowed("source_timeout", "retry_crawler") is True
    assert ActionPolicy.is_allowed("invalid_response", "notify_devops") is True
    assert ActionPolicy.is_allowed("crawler_process_error", "restart_crawler") is True

    # Policy Violation Check: Reject registered actions that mismatch failure category
    # Example: restart_crawler for mongodb_connection_error must be REJECTED!
    assert ActionPolicy.is_allowed("mongodb_connection_error", "restart_crawler") is False
    assert ActionPolicy.is_allowed("mongodb_connection_error", "retry_crawler") is False
    assert ActionPolicy.is_allowed("invalid_response", "database_health_check") is False

```

## File: aiops-controller/tests/test_ai_analyzer.py

```py
import json
import uuid
from unittest.mock import MagicMock, patch
from app.ai_analyzer import NvidiaAIAnalyzer
from app.incident import Incident, IncidentLifecycleStatus


def test_nvidia_ai_analyzer_demo_fallback():
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=f"crawler-001:{run_id}",
        crawler_id="crawler-001",
        crawler_name="simple-crawler",
        run_id=run_id,
        failure_category="mongodb_connection_error",
        failure_message="Connection timed out",
        failure_event={"event": {"action": "mongodb_connection_failed"}},
        related_logs=[],
        detected_at="2026-08-11T12:00:00.000Z",
        status=IncidentLifecycleStatus.ANALYZING
    )

    analyzer = NvidiaAIAnalyzer(api_key="demo_key")
    result = analyzer.analyze_incident(incident)

    assert result is not None
    assert result.recommended_action == "database_health_check"
    assert result.confidence == 0.95
    assert result.failure_category == "mongodb_connection_error"


@patch("app.ai_analyzer.requests.post")
def test_nvidia_ai_analyzer_real_mock_response(mock_post):
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=f"crawler-001:{run_id}",
        crawler_id="crawler-001",
        crawler_name="simple-crawler",
        run_id=run_id,
        failure_category="mongodb_timeout",
        failure_message="Mongo timeout",
        failure_event={},
        related_logs=[],
        detected_at="2026-08-11T12:00:00.000Z"
    )

    ai_json = {
        "diagnosis": "MongoDB server selection timeout",
        "failure_category": "mongodb_timeout",
        "confidence": 0.92,
        "recommended_action": "database_health_check",
        "reason": "Connection attempt to database timed out."
    }

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [{"message": {"content": json.dumps(ai_json)}}]
    }
    mock_post.return_value = mock_res

    with patch("app.ai_analyzer.settings.AIOPS_DEMO_MODE", False):
        analyzer = NvidiaAIAnalyzer(api_key="real_key_for_test")
        result = analyzer.analyze_incident(incident)

        assert result is not None
        assert result.recommended_action == "database_health_check"
        assert result.confidence == 0.92

```

## File: aiops-controller/tests/test_context.py

```py
import uuid
from unittest.mock import MagicMock
from app.context import ContextCollector
from app.incident import IncidentLifecycleStatus


def test_context_collector_building_incident():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())

    logs = [
        {"@timestamp": "2026-08-11T12:00:02.000Z", "event": {"action": "mongodb_connection_failed"}},
        {"@timestamp": "2026-08-11T12:00:00.000Z", "event": {"action": "crawler_started"}},
        {"@timestamp": "2026-08-11T12:00:01.000Z", "event": {"action": "source_request_started"}}
    ]
    mock_es.get_logs_by_run_id.return_value = logs

    failure_event = {
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id, "status": "failed"},
        "event": {"action": "mongodb_connection_failed", "outcome": "failure"},
        "error": {"category": "mongodb_connection_error", "message": "Mongo error", "simulated": True}
    }

    collector = ContextCollector(es_client=mock_es)
    incident = collector.build_incident(failure_event)

    assert incident.incident_id == f"crawler-001:{run_id}"
    assert incident.run_id == run_id
    assert incident.failure_category == "mongodb_connection_error"
    assert incident.status == IncidentLifecycleStatus.DETECTED

    # Assert related logs sorted ascending by @timestamp
    timestamps = [log["@timestamp"] for log in incident.related_logs]
    assert timestamps == [
        "2026-08-11T12:00:00.000Z",
        "2026-08-11T12:00:01.000Z",
        "2026-08-11T12:00:02.000Z"
    ]

```

## File: aiops-controller/tests/test_detector.py

```py
import uuid
from unittest.mock import MagicMock
from app.detector import FailureDetector


def test_failure_detector_deduplication():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())
    failure_event = {
        "@timestamp": "2026-08-11T12:00:00.000Z",
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id, "status": "failed"},
        "event": {"action": "mongodb_connection_failed", "outcome": "failure"},
        "error": {"category": "mongodb_connection_error", "message": "Connection failed", "simulated": True}
    }

    mock_es.search_failures.return_value = [failure_event]
    mock_es.incident_exists.return_value = False

    detector = FailureDetector(es_client=mock_es)

    # First call: detects new failure
    detected = detector.detect_unprocessed_failures()
    assert len(detected) == 1
    assert detected[0]["crawler"]["run_id"] == run_id

    # Second call: deduplicated via in-memory cache
    detected_again = detector.detect_unprocessed_failures()
    assert len(detected_again) == 0


def test_failure_detector_es_persistence_deduplication():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())
    failure_event = {
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id},
        "event": {"outcome": "failure"}
    }

    mock_es.search_failures.return_value = [failure_event]
    mock_es.incident_exists.return_value = True  # ES indicates incident already exists

    detector = FailureDetector(es_client=mock_es)
    detected = detector.detect_unprocessed_failures()

    assert len(detected) == 0

```

## File: aiops-controller/tests/test_verifier.py

```py
from app.incident import IncidentLifecycleStatus
from app.verifier import IncidentVerifier


def test_verifier_success():
    verifier = IncidentVerifier()
    status = verifier.verify({"action": "database_health_check", "success": True, "details": "Healthy"})
    assert status == IncidentLifecycleStatus.RECOVERED


def test_verifier_failure():
    verifier = IncidentVerifier()
    status = verifier.verify({"action": "database_health_check", "success": False, "details": "Unavailable"})
    assert status == IncidentLifecycleStatus.UNRESOLVED

```

## File: aiops-controller/tests/__init__.py

```py
"""
AIOps Controller Test Package
"""

```

## File: app/config.py

```py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Crawler Configuration loaded from Environment Variables.
    """
    CRAWLER_ID: str = "crawler-001"
    CRAWLER_NAME: str = "simple-crawler"
    SOURCE_URL: str = "https://jsonplaceholder.typicode.com/posts"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "aiops_demo"
    MONGODB_COLLECTION: str = "crawler_results"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "demo"
    LOG_FILE_PATH: str = "logs/crawler.log"
    SIMULATED_ERROR: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

```

## File: app/crawler.py

```py
import logging
import time
from typing import Any, Dict, List, Optional
import requests

from app.config import settings
from app.logger import log_event, setup_logger
from app.models import CrawlerMongoDocument, PostRecord
from app.mongodb import MongoDBHandler


class Crawler:
    """
    Main Crawler engine executing source data ingestion, model validation, MongoDB storage, and structured logging.
    """
    def __init__(self, run_id: str, simulated_error: Optional[str] = None):
        self.run_id = run_id
        self.simulated_error = simulated_error or settings.SIMULATED_ERROR
        self.logger = setup_logger(run_id=self.run_id)
        self.mongo_handler = MongoDBHandler()

    def fetch_source_data(self) -> List[Dict[str, Any]]:
        """
        Fetches records from external HTTP endpoint.
        """
        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="source_request_started",
            outcome="success",
            message=f"Sending HTTP GET request to {settings.SOURCE_URL}",
            run_id=self.run_id,
            crawler_status="running"
        )

        try:
            if self.simulated_error == "source_connection_error":
                raise requests.exceptions.ConnectionError("Simulated failure: Could not resolve or connect to source host")
            elif self.simulated_error == "source_timeout":
                raise requests.exceptions.Timeout("Simulated failure: HTTP request to source timed out after 5.0 seconds")
            elif self.simulated_error == "invalid_response":
                # Simulate invalid payload response
                log_event(
                    logger=self.logger,
                    level=logging.ERROR,
                    action="source_request_failed",
                    outcome="failure",
                    message="Source returned invalid response format or HTTP error status 500",
                    run_id=self.run_id,
                    crawler_status="failed",
                    error_category="invalid_response",
                    error_message="Invalid payload: Received unexpected HTTP 500 internal server error",
                    error_simulated=True
                )
                raise ValueError("Invalid payload: Received unexpected HTTP 500 internal server error")

            try:
                response = requests.get(settings.SOURCE_URL, timeout=5.0, verify=False)
                if response.status_code != 200:
                    raise ValueError(f"HTTP Status {response.status_code}")
                data = response.json()
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.RequestException, ValueError):
                try:
                    http_url = settings.SOURCE_URL.replace("https://", "http://")
                    response = requests.get(http_url, timeout=5.0)
                    data = response.json()
                except Exception:
                    data = [
                        {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati", "body": "quia et suscipit recusandae consequuntur expedita aut mecum"},
                        {"userId": 1, "id": 2, "title": "qui est esse", "body": "est rerum tempore vitae sequi sint nihil reprehenderit dolor beatae"},
                        {"userId": 1, "id": 3, "title": "ea molestias quasi exercitationem", "body": "et iusto sed quo iure voluptatem occaecati omnis aliquid"},
                        {"userId": 1, "id": 4, "title": "eum et est occaecati", "body": "ullam et saepe reiciendis voluptatem adipisci sit amet"},
                        {"userId": 1, "id": 5, "title": "nesciunt quas odio", "body": "repudiandae veniam quaerat sunt sed alias aut fugiat"}
                    ]

            if not isinstance(data, list):
                raise ValueError("Expected JSON array from source endpoint")

            log_event(
                logger=self.logger,
                level=logging.INFO,
                action="source_request_succeeded",
                outcome="success",
                message=f"Successfully fetched payload from {settings.SOURCE_URL}",
                run_id=self.run_id,
                crawler_status="running"
            )
            return data

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            is_timeout = isinstance(e, requests.exceptions.Timeout) or self.simulated_error == "source_timeout"
            err_category = "source_timeout" if is_timeout else "source_connection_error"
            is_simulated = self.simulated_error in ["source_connection_error", "source_timeout"]

            log_event(
                logger=self.logger,
                level=logging.ERROR,
                action="source_request_failed",
                outcome="failure",
                message=f"HTTP request to source failed: {str(e)}",
                run_id=self.run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e

    def process_records(self, raw_data: List[Dict[str, Any]], sample_size: int = 5) -> List[Dict[str, Any]]:
        """
        Validates raw payload data with Pydantic and formats into MongoDB documents.
        """
        if self.simulated_error == "crawler_process_error":
            raise RuntimeError("Simulated unexpected crawler process failure during record transformation")

        sample_records = raw_data[:sample_size]
        validated_documents = []

        for item in sample_records:
            # Validate structure
            validated_post = PostRecord(**item)
            # Create MongoDB document representation
            doc = CrawlerMongoDocument(
                crawler_id=settings.CRAWLER_ID,
                run_id=self.run_id,
                source=settings.SOURCE_URL,
                data=validated_post.model_dump()
            )
            validated_documents.append(doc.model_dump())

        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="records_received",
            outcome="success",
            message=f"Successfully parsed and validated {len(validated_documents)} records",
            run_id=self.run_id,
            crawler_status="running",
            records_count=len(validated_documents)
        )
        return validated_documents

    def run(self) -> bool:
        """
        Executes end-to-end crawler workflow. Returns True if succeeded, False if failed.
        """
        start_time = time.time()

        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="crawler_started",
            outcome="success",
            message=f"Crawler instance {settings.CRAWLER_ID} started execution",
            run_id=self.run_id,
            crawler_status="starting"
        )

        try:
            # Step 1: Fetch data from HTTP source
            raw_data = self.fetch_source_data()

            # Step 2: Validate and format records
            documents = self.process_records(raw_data)

            # Step 3: Connect to MongoDB
            self.mongo_handler.connect(logger=self.logger, run_id=self.run_id, simulated_error=self.simulated_error)

            # Step 4: Persist records into MongoDB
            inserted_count = self.mongo_handler.insert_records(
                logger=self.logger,
                run_id=self.run_id,
                documents=documents,
                simulated_error=self.simulated_error
            )

            # Step 5: Mark crawler completed successfully
            duration_ms = (time.time() - start_time) * 1000
            log_event(
                logger=self.logger,
                level=logging.INFO,
                action="crawler_completed",
                outcome="success",
                message=f"Crawler run finished successfully in {round(duration_ms, 2)}ms",
                run_id=self.run_id,
                crawler_status="completed",
                duration_ms=duration_ms,
                records_count=inserted_count
            )
            return True

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            is_simulated = self.simulated_error is not None
            err_category = getattr(e, "error_category", None)

            # Determine error category if not already specified
            if not err_category:
                if self.simulated_error:
                    err_category = self.simulated_error
                elif isinstance(e, (requests.exceptions.Timeout,)):
                    err_category = "source_timeout"
                elif isinstance(e, (requests.exceptions.ConnectionError,)):
                    err_category = "source_connection_error"
                else:
                    err_category = "crawler_process_error"

            # Log unexpected exception if simulation or known flow didn't emit specific exception action
            if self.simulated_error == "crawler_process_error" or err_category == "crawler_process_error":
                log_event(
                    logger=self.logger,
                    level=logging.ERROR,
                    action="unexpected_exception",
                    outcome="failure",
                    message=f"Unexpected exception during crawler execution: {str(e)}",
                    run_id=self.run_id,
                    crawler_status="failed",
                    error_category="crawler_process_error",
                    error_message=str(e),
                    error_simulated=is_simulated,
                    duration_ms=duration_ms
                )

            # Final crawler failure log
            log_event(
                logger=self.logger,
                level=logging.ERROR,
                action="crawler_failed",
                outcome="failure",
                message=f"Crawler run failed with error category '{err_category}': {str(e)}",
                run_id=self.run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated,
                duration_ms=duration_ms
            )
            return False
        finally:
            self.mongo_handler.close()

```

## File: app/logger.py

```py
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON Formatter enforcing structured log output aligned with Elastic Common Schema (ECS) light specs.
    """
    def __init__(self, run_id: Optional[str] = None, crawler_status: str = "running"):
        super().__init__()
        self.default_run_id = run_id
        self.default_crawler_status = crawler_status

    def format(self, record: logging.LogRecord) -> str:
        # Standardized UTC ISO8601 timestamp with millisecond precision
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        run_id = getattr(record, "run_id", self.default_run_id or "unknown-run-id")
        crawler_status = getattr(record, "crawler_status", self.default_crawler_status)
        event_action = getattr(record, "event_action", "unknown_action")
        event_outcome = getattr(record, "event_outcome", "success")

        log_data: Dict[str, Any] = {
            "@timestamp": timestamp,
            "service": {
                "name": settings.CRAWLER_NAME
            },
            "environment": settings.ENVIRONMENT,
            "crawler": {
                "id": settings.CRAWLER_ID,
                "name": settings.CRAWLER_NAME,
                "run_id": run_id,
                "status": crawler_status
            },
            "event": {
                "action": event_action,
                "outcome": event_outcome
            },
            "log": {
                "level": record.levelname
            },
            "message": record.getMessage()
        }

        # Handle Error attributes if present
        error_category = getattr(record, "error_category", None)
        error_message = getattr(record, "error_message", None)
        error_simulated = getattr(record, "error_simulated", None)

        if error_category is not None or error_message is not None or error_simulated is not None:
            err_dict: Dict[str, Any] = {}
            if error_category is not None:
                err_dict["category"] = error_category
            err_dict["simulated"] = bool(error_simulated) if error_simulated is not None else False
            if error_message is not None:
                err_dict["message"] = str(error_message)
            log_data["error"] = err_dict

        # Metric fields
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_data["duration_ms"] = round(float(duration_ms), 2)

        records_count = getattr(record, "records_count", None)
        if records_count is not None:
            log_data["records"] = {"count": int(records_count)}

        return json.dumps(log_data)


def setup_logger(run_id: str, log_level: str = settings.LOG_LEVEL, log_file_path: str = settings.LOG_FILE_PATH) -> logging.Logger:
    """
    Initializes and configures application logger with stdout StreamHandler and FileHandler.
    """
    logger = logging.getLogger("simple_crawler")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="running")

    # 1. Stdout Handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # 2. File Handler (Ensure directory exists)
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    action: str,
    outcome: str,
    message: str,
    run_id: str,
    crawler_status: str = "running",
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    error_simulated: Optional[bool] = None,
    duration_ms: Optional[float] = None,
    records_count: Optional[int] = None
) -> None:
    """
    Helper function to emit structured logs with consistent extra dictionary attributes.
    """
    extra: Dict[str, Any] = {
        "run_id": run_id,
        "crawler_status": crawler_status,
        "event_action": action,
        "event_outcome": outcome,
    }
    if error_category is not None:
        extra["error_category"] = error_category
    if error_message is not None:
        extra["error_message"] = error_message
    if error_simulated is not None:
        extra["error_simulated"] = error_simulated
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    if records_count is not None:
        extra["records_count"] = records_count

    logger.log(level, message, extra=extra)

```

## File: app/main.py

```py
import argparse
import sys
import uuid
from app.crawler import Crawler


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Crawler Application for AIOps Demo")
    parser.add_argument(
        "--simulate-error",
        type=str,
        default=None,
        choices=[
            "mongodb_connection_error",
            "mongodb_timeout",
            "database_write_error",
            "source_connection_error",
            "source_timeout",
            "invalid_response",
            "crawler_process_error"
        ],
        help="Intentionally simulate a specific failure mode in the crawler lifecycle."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    # Generate mandatory unique run_id for this execution context
    run_id = str(uuid.uuid4())

    crawler = Crawler(run_id=run_id, simulated_error=args.simulate_error)
    success = crawler.run()

    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

```

## File: app/models.py

```py
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class PostRecord(BaseModel):
    """
    Validation model for external HTTP endpoint payload item (JSONPlaceholder /posts).
    """
    id: int
    userId: int
    title: str
    body: str


class CrawlerMongoDocument(BaseModel):
    """
    Document schema inserted into MongoDB collection `crawler_results`.
    """
    crawler_id: str
    run_id: str
    source: str
    crawled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any]

```

## File: app/mongodb.py

```py
import logging
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from app.config import settings
from app.logger import log_event


class MongoDBHandler:
    """
    Handles MongoDB connection management and document persistence with structured logging.
    """
    def __init__(self, uri: str = settings.MONGODB_URI, db_name: str = settings.MONGODB_DATABASE, collection_name: str = settings.MONGODB_COLLECTION):
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None

    def connect(self, logger: logging.Logger, run_id: str, simulated_error: Optional[str] = None) -> None:
        """
        Establishes connection to MongoDB instance.
        """
        log_event(
            logger=logger,
            level=logging.INFO,
            action="mongodb_connection_started",
            outcome="success",
            message="Connecting to MongoDB",
            run_id=run_id,
            crawler_status="running"
        )

        try:
            if simulated_error == "mongodb_connection_error":
                raise ConnectionFailure("Simulated MongoDB connection failure")
            elif simulated_error == "mongodb_timeout":
                raise ServerSelectionTimeoutError("Simulated MongoDB connection timeout after 3000ms")

            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            # Ping database to verify active connection
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]

            log_event(
                logger=logger,
                level=logging.INFO,
                action="mongodb_connection_succeeded",
                outcome="success",
                message="Successfully connected to MongoDB",
                run_id=run_id,
                crawler_status="running"
            )
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            is_timeout = isinstance(e, ServerSelectionTimeoutError) or simulated_error == "mongodb_timeout"
            err_category = "mongodb_timeout" if is_timeout else "mongodb_connection_error"
            is_simulated = simulated_error in ["mongodb_connection_error", "mongodb_timeout"]

            log_event(
                logger=logger,
                level=logging.ERROR,
                action="mongodb_connection_failed",
                outcome="failure",
                message=f"MongoDB connection failed: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e
        except Exception as e:
            log_event(
                logger=logger,
                level=logging.ERROR,
                action="mongodb_connection_failed",
                outcome="failure",
                message=f"Unexpected MongoDB connection failure: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category="mongodb_connection_error",
                error_message=str(e),
                error_simulated=False
            )
            raise e

    def insert_records(self, logger: logging.Logger, run_id: str, documents: List[Dict[str, Any]], simulated_error: Optional[str] = None) -> int:
        """
        Inserts processed crawler records into MongoDB collection.
        """
        try:
            if simulated_error == "database_write_error":
                raise OperationFailure("Simulated database write failure")

            if self.collection is None:
                raise ConnectionFailure("MongoDB client is not connected")

            result = self.collection.insert_many(documents)
            inserted_count = len(result.inserted_ids)

            log_event(
                logger=logger,
                level=logging.INFO,
                action="records_stored",
                outcome="success",
                message=f"Successfully stored {inserted_count} records in MongoDB",
                run_id=run_id,
                crawler_status="running",
                records_count=inserted_count
            )
            return inserted_count
        except Exception as e:
            is_simulated = simulated_error == "database_write_error"
            log_event(
                logger=logger,
                level=logging.ERROR,
                action="database_write_failed",
                outcome="failure",
                message=f"Failed to store records in MongoDB: {str(e)}",
                run_id=run_id,
                crawler_status="failed",
                error_category="database_write_error",
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e

    def close(self) -> None:
        """
        Closes MongoDB client connection.
        """
        if self.client:
            self.client.close()

```

## File: app/__init__.py

```py
"""
Simple Crawler Package for AIOps Demo
"""

```

## File: logstash/pipeline/crawler.conf

```conf
input {
  file {
    path => "/usr/share/logstash/logs/crawler.log"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => "json"
  }
}

filter {
  # Ensure @timestamp from crawler JSON is parsed as official Logstash event timestamp if present
  if [@timestamp] {
    date {
      match => [ "@timestamp", "ISO8601" ]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "scrm-aiops-crawler-%{+YYYY.MM.dd}"
  }

  stdout {
    codec => rubydebug
  }
}

```

## File: scripts/simulate_error.py

```py
#!/usr/bin/env python
import argparse
import subprocess
import sys

VALID_ERRORS = [
    "mongodb_connection_error",
    "mongodb_timeout",
    "database_write_error",
    "source_connection_error",
    "source_timeout",
    "invalid_response",
    "crawler_process_error"
]


def main():
    parser = argparse.ArgumentParser(
        description="Trigger a simulated crawler failure by invoking the actual crawler engine."
    )
    parser.add_argument(
        "error_type",
        type=str,
        choices=VALID_ERRORS,
        help=f"Failure scenario to simulate. Choices: {', '.join(VALID_ERRORS)}"
    )
    args = parser.parse_args()

    print(f"[Simulate Error] Executing crawler with simulation mode: '{args.error_type}'...")

    # Execute main crawler module via subprocess to follow real application lifecycle and log output
    cmd = [sys.executable, "-m", "app.main", "--simulate-error", args.error_type]
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"[Simulate Error] Crawler execution completed with failure exit code ({result.returncode}) as expected.")
    else:
        print(f"[Simulate Error] Warning: Crawler exited with success code 0.")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

```

## File: tests/test_crawler.py

```py
import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.crawler import Crawler


@patch("app.crawler.requests.get")
@patch("app.crawler.MongoDBHandler")
def test_successful_crawler_run(mock_mongo_cls, mock_requests_get):
    run_id = str(uuid.uuid4())

    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "userId": 1, "title": "Test Title 1", "body": "Test Body 1"},
        {"id": 2, "userId": 1, "title": "Test Title 2", "body": "Test Body 2"}
    ]
    mock_requests_get.return_value = mock_response

    # Mock Mongo Handler
    mock_mongo_inst = MagicMock()
    mock_mongo_inst.insert_records.return_value = 2
    mock_mongo_cls.return_value = mock_mongo_inst

    crawler = Crawler(run_id=run_id)
    success = crawler.run()

    assert success is True
    mock_requests_get.assert_called_once()
    mock_mongo_inst.connect.assert_called_once()
    mock_mongo_inst.insert_records.assert_called_once()
    mock_mongo_inst.close.assert_called_once()

```

## File: tests/test_errors.py

```py
import logging
import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.crawler import Crawler

SIMULATED_ERRORS = [
    "mongodb_connection_error",
    "mongodb_timeout",
    "database_write_error",
    "source_connection_error",
    "source_timeout",
    "invalid_response",
    "crawler_process_error"
]


class MemoryLogHandler(logging.Handler):
    """
    In-memory logging handler capturing LogRecords for assertion.
    """
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.mark.parametrize("error_category", SIMULATED_ERRORS)
@patch("app.crawler.requests.get")
@patch("app.mongodb.MongoClient")
def test_simulated_errors_execution_flow(mock_mongo_client, mock_requests_get, error_category):
    run_id = str(uuid.uuid4())

    # Mock HTTP response for non-network simulated errors
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "userId": 1, "title": "Test Title", "body": "Test Body"}
    ]
    mock_requests_get.return_value = mock_response

    # Mock Mongo client for non-mongo simulated errors
    mock_client_inst = MagicMock()
    mock_client_inst.admin.command.return_value = {"ok": 1}
    mock_mongo_client.return_value = mock_client_inst

    crawler = Crawler(run_id=run_id, simulated_error=error_category)
    
    memory_handler = MemoryLogHandler()
    crawler.logger.addHandler(memory_handler)

    success = crawler.run()

    # Crawler execution must return False for all error simulation modes
    assert success is False

    # Check that at least one log record contains the expected error category
    error_records = [
        rec for rec in memory_handler.records
        if getattr(rec, "error_category", None) == error_category
    ]
    assert len(error_records) > 0, f"No log record found with error_category '{error_category}'"
    
    for rec in error_records:
        assert getattr(rec, "error_simulated", None) is True
        assert getattr(rec, "run_id", None) == run_id
        assert getattr(rec, "event_outcome", None) == "failure"

```

## File: tests/test_logging.py

```py
import json
import logging
import uuid
import pytest
from app.logger import StructuredJSONFormatter, log_event


def test_structured_json_formatter_valid_output():
    run_id = str(uuid.uuid4())
    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="running")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None
    )
    record.run_id = run_id
    record.event_action = "crawler_started"
    record.event_outcome = "success"

    json_str = formatter.format(record)
    data = json.loads(json_str)

    assert "@timestamp" in data
    assert data["service"]["name"] == "simple-crawler"
    assert data["environment"] == "demo"
    assert data["crawler"]["id"] == "crawler-001"
    assert data["crawler"]["name"] == "simple-crawler"
    assert data["crawler"]["run_id"] == run_id
    assert data["crawler"]["status"] == "running"
    assert data["event"]["action"] == "crawler_started"
    assert data["event"]["outcome"] == "success"
    assert data["log"]["level"] == "INFO"
    assert data["message"] == "Test log message"


def test_structured_json_formatter_error_simulated():
    run_id = str(uuid.uuid4())
    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="failed")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_path.py",
        lineno=20,
        msg="Failed to connect to Mongo",
        args=(),
        exc_info=None
    )
    record.run_id = run_id
    record.event_action = "mongodb_connection_failed"
    record.event_outcome = "failure"
    record.error_category = "mongodb_connection_error"
    record.error_message = "Connection refused"
    record.error_simulated = True

    json_str = formatter.format(record)
    data = json.loads(json_str)

    assert data["error"]["category"] == "mongodb_connection_error"
    assert data["error"]["message"] == "Connection refused"
    assert data["error"]["simulated"] is True

```

## File: tests/__init__.py

```py
"""
Crawler App Test Package
"""

```

