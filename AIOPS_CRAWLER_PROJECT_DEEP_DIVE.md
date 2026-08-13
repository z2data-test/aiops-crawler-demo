# Self-Healing AIOps Crawler System — Comprehensive Project Documentation

## 1. Executive Summary & System Overview

This project is an **Autonomous Self-Healing AIOps Pipeline** designed to monitor, diagnose, and remediate web crawler execution failures automatically.

The system combines:
- A **Python 3.12 Web Crawler** that fetches external API data, stores records in **MongoDB**, and emits structured **Elastic Common Schema (ECS)** JSON logs.
- An **ELK Stack (Elasticsearch, Logstash, Kibana)** for log aggregation, indexing, and visualization.
- An **AIOps Controller Service** that continuously polls Elasticsearch for crawler failures, collects surrounding log context, invokes an **NVIDIA AI NIM LLM (meta/llama-3.1-405b-instruct)** to diagnose the root cause, passes the proposed remediation action through a **Security Policy Gatekeeper**, executes approved remediation handlers, and verifies recovery.

---

## 2. End-to-End System Architecture

```
+-----------------------------------------------------------------------------------------------------------+
|                                           1. CRAWLER APPLICATION                                          |
|                                                                                                           |
|   [simulate_error.py] ---> [app/main.py] ---> [Crawler Engine] ---> Stores Records ---> [ MongoDB ]      |
|                                                     |                                                     |
|                                                     v (ECS Structured JSON Logs)                          |
|                                           [ /app/logs/crawler.log ]                                       |
+-----------------------------------------------------------------------------------------------------------+
                                                      |
                                                      v
+-----------------------------------------------------------------------------------------------------------+
|                                           2. LOG INGESTION & ELK STACK                                    |
|                                                                                                           |
|   [ /app/logs/crawler.log ] ---> [ Logstash ] ---> [ Elasticsearch ] (scrm-aiops-crawler-*)               |
|                                                           |                                               |
|                                                           v                                               |
|                                                    [ Kibana UI ]                                          |
+-----------------------------------------------------------------------------------------------------------+
                                                      |
                                                      v
+-----------------------------------------------------------------------------------------------------------+
|                                           3. AIOPS CONTROLLER ENGINE                                      |
|                                                                                                           |
|   [ Failure Detector ] (Polls ES for event.outcome == "failure")                                          |
|            |                                                                                              |
|            v                                                                                              |
|   [ Context Collector ] (Fetches complete log sequence for crawler.run_id from ES)                        |
|            |                                                                                              |
|            v                                                                                              |
|   [ AI Analyzer ] (NVIDIA LLaMA 3.1 405B NIM API / Rule-based Fallback)                                   |
|            | -> Proposes standard action (e.g. restart_crawler)                                            |
|            v                                                                                              |
|   [ Security Policy Gatekeeper ] (Registry validation & approval check)                                   |
|            |                                                                                              |
|            v                                                                                              |
|   [ Action Executor ] (Executes explicit Python remediation function)                                     |
|            |                                                                                              |
|            v                                                                                              |
|   [ Incident Verifier ] (Updates lifecycle state to RECOVERED / MANUAL_INVESTIGATION)                      |
+-----------------------------------------------------------------------------------------------------------+
```

---

## 3. Core Component Breakdown

### 3.1. Crawler Application (`app/`)
- **[app/main.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/app/main.py)**: CLI entry point. Generates a unique UUID `run_id` for every execution run and handles CLI error simulation flags.
- **[app/config.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/app/config.py)**: Pydantic-based configuration manager loading settings from environment variables.
- **[app/crawler.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/app/crawler.py)**: Core execution logic. Coordinates HTTP requests, JSON parsing, Pydantic validation (`models.py`), MongoDB insertion, and error handling.
- **[app/mongodb.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/app/mongodb.py)**: Manages MongoDB client connections, ping health checks, and record persistence in `aiops_demo.crawler_results`.
- **[app/logger.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/app/logger.py)**: Configures structured ECS JSON logging outputting to stdout and `/app/logs/crawler.log`.

### 3.2. AIOps Controller Service (`aiops-controller/app/`)
- **[main.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/main.py)**: Autonomous event loop. Continuously polls Elasticsearch every `POLL_INTERVAL_SECONDS` (default: 5s).
- **[detector.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/detector.py)**: Queries Elasticsearch index `scrm-aiops-crawler-*` for unhandled failure events (`event.outcome == "failure"`).
- **[context.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/context.py)**: Given a failed `crawler.run_id`, fetches all related logs ordered chronologically by `@timestamp` to reconstruct full incident context.
- **[ai_analyzer.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/ai_analyzer.py)**: Formats incident context into a structured prompt and calls NVIDIA AI NIM API (`meta/llama-3.1-405b-instruct`) with JSON schema enforcement. Features an automatic corporate proxy SSL fallback and an offline rule-based fallback analyzer.
- **[action_registry.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/action_registry.py)**: Validates proposed actions against an approved list:
  1. `database_health_check`
  2. `retry_crawler`
  3. `notify_devops`
  4. `restart_crawler`
- **[action_policy.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/action_policy.py)**: Security Gatekeeper. Verifies that confidence is >= `AI_CONFIDENCE_THRESHOLD` (0.80) and that proposed actions adhere strictly to allowed policies.
- **[action_executor.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/action_executor.py)**: Maps action names to concrete Python module execution logic in `actions/`. **Strictly forbids arbitrary shell execution.**
- **[verifier.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/aiops-controller/app/verifier.py)**: Marks incident lifecycle as `RECOVERED` or `MANUAL_INVESTIGATION`.

---

## 4. Error Simulation Engine & Categories

The project features a built-in simulation suite ([scripts/simulate_error.py](file:///d:/Test%20folder/AIReviewer/Crawler_App/scripts/simulate_error.py)) that executes the **real crawler engine code path** with injected fault triggers (`error.simulated = true`).

| Error Category | Simulation Trigger | AI Diagnosis | AI Recommended Action | Action Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `mongodb_connection_error` | Simulates DB connection refusal | MongoDB unreachable | `database_health_check` | Checks MongoDB container status & ping |
| `mongodb_timeout` | Simulates 3000ms DB connection timeout | MongoDB socket timeout | `database_health_check` | Performs network connectivity test |
| `database_write_error` | Simulates DB write failure during insert | Transient DB write error | `retry_crawler` | Re-executes crawler with backoff |
| `source_connection_error` | Simulates HTTP connection failure | Source API offline | `retry_crawler` | Retries crawler after connection test |
| `source_timeout` | Simulates HTTP GET request timeout | Upstream API timeout | `retry_crawler` | Re-executes run with extended timeout |
| `invalid_response` | Injects malformed JSON schema payload | Upstream API schema drift | `notify_devops` | Alerts DevOps team for manual intervention |
| `crawler_process_error` | Throws unexpected Python runtime exception | Process execution error | `restart_crawler` | Requests container restart |

---

## 5. Security & Safety Model

1. **Zero Shell Execution**: The AI is **never** permitted to generate or execute arbitrary shell commands, PowerShell, SQL, or Python scripts.
2. **Action White-listing**: Actions MUST exist in the `ActionRegistry`. Any unrecognized action is immediately rejected.
3. **Confidence Threshold**: If AI diagnosis confidence is below `0.80`, the action automatically degrades to `notify_devops` and flags `MANUAL_INVESTIGATION`.
4. **Demo Mode Safety**: When `AIOPS_DEMO_MODE=true` (or when running demo actions), system modifications (such as docker container restarts or real alerts) are safely logged without executing invasive changes.

---

## 6. Docker Infrastructure & Environment Variables

### Docker Compose Stack (`docker-compose.yml`)
- **`mongodb`**: Mongo 7.0 database (`port 27017`)
- **`elasticsearch`**: Elastic 8.12.0 single-node cluster (`port 9200`)
- **`logstash`**: Logstash 8.12.0 log ingestion engine reading `/app/logs/crawler.log`
- **`kibana`**: Kibana 8.12.0 analytics dashboard (`port 5601`)
- **`crawler`**: Python crawler container
- **`aiops-controller`**: Autonomous AIOps remediation engine

### Core Environment Variables (`.env`)
```ini
CRAWLER_ID=crawler-001
CRAWLER_NAME=simple-crawler
SOURCE_URL=https://jsonplaceholder.typicode.com/posts
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=aiops_demo
MONGODB_COLLECTION=crawler_results
LOG_LEVEL=INFO
ENVIRONMENT=demo
ELASTICSEARCH_URL=http://elasticsearch:9200
ELASTICSEARCH_CRAWLER_INDEX=scrm-aiops-crawler-*
ELASTICSEARCH_CONTROLLER_INDEX=scrm-aiops-controller
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.1-405b-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
AIOPS_DEMO_MODE=false
POLL_INTERVAL_SECONDS=5
```

---

## 7. How to Run & Verify

1. **Start the Stack**:
   ```powershell
   docker-compose up -d --build
   ```

2. **Simulate a Failure**:
   ```powershell
   python scripts/simulate_error.py crawler_process_error
   ```

3. **Observe AIOps Remediation Logs**:
   ```powershell
   docker-compose logs -f aiops-controller
   ```

4. **Verify in Kibana**:
   - Access `http://localhost:5601`
   - Data View pattern: `scrm-aiops-crawler-*`
