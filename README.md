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
