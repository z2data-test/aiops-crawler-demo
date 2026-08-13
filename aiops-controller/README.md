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
