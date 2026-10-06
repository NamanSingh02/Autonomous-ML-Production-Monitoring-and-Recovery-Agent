# Autonomous ML Production Monitoring & Recovery Agent

## What This Project Does

This project is a production-style **Agentic AI system for monitoring, diagnosing, and recovering deployed machine-learning systems**.

The system continuously observes a live ML application for problems such as:

- Data drift
- Feature-quality degradation
- Model-performance degradation
- Inference latency spikes
- Broken preprocessing or feature pipelines
- Failed model deployments
- Infrastructure failures
- Serving failures
- Dependency outages

When an anomaly or incident is detected, the agent does not simply summarize the available logs. It actively investigates the system by choosing which telemetry, historical data, documentation, experiments, model metadata, and operational tools to inspect.

The end-to-end workflow is:

```text
Monitor
  ↓
Detect
  ↓
Investigate
  ↓
Retrieve Knowledge
  ↓
Form Hypotheses
  ↓
Run Diagnostics
  ↓
Choose Recovery
  ↓
Request Approval if Required
  ↓
Execute Recovery
  ↓
Verify
  ↓
Document + Learn
```

The goal is to demonstrate a realistic autonomous AI system that works over **changing production state**, combines live telemetry with RAG-based operational knowledge, and measures whether its own actions actually improve the system.

---

## Project Idea

### 1. Autonomous ML Production Monitoring & Recovery Agent

This project focuses on an AI agent that continuously monitors a deployed ML system for problems such as data drift, feature-quality issues, degraded model accuracy, inference latency spikes, broken pipelines, or bad deployments. When something goes wrong, the agent gathers evidence from model metrics, feature distributions, logs, experiment history, deployment metadata, model cards, runbooks, and prior incidents, then determines whether the failure is caused by the data, model, infrastructure, or serving pipeline and recommends or executes a recovery action.

What makes this stronger than a simple Codex/Claude prompt is that the system operates over live, changing production state rather than a static codebase or one-time dataset. It can continuously detect anomalies, retrieve relevant historical context through RAG, choose which monitoring or infrastructure tools to call, compare current behavior against previous model versions, perform multi-step diagnosis, trigger safe rollback/retraining/reconfiguration workflows, verify whether performance recovered, and keep an auditable trace of the entire process. A single prompt can analyze information you manually provide; this system autonomously decides what information it needs, when to fetch it, what action to take, and whether that action actually worked.

---

## Why This Is More Than Giving Claude Code or Codex a Prompt

A coding assistant can be given a repository, logs, configuration files, or model artifacts and asked:

> "Find what is wrong and fix it."

That is useful, but it is still primarily a **one-shot or interactive debugging workflow initiated by a human**.

This project is different because the system operates continuously and autonomously across a live environment.

Instead of receiving all relevant information up front, the agent must decide:

- Whether an incident exists
- Which subsystem is likely responsible
- Which metrics or logs to inspect
- Which model version to compare against
- Whether recent deployments are relevant
- Whether historical incidents contain useful evidence
- Whether a runbook should be retrieved
- Which diagnostic tool to call next
- Whether the current hypothesis is still plausible
- Whether the proposed recovery is safe
- Whether a human must approve the action
- Whether the system actually recovered after the action

The project therefore goes beyond static code analysis and demonstrates:

- Continuous monitoring
- Autonomous multi-step investigation
- Dynamic tool selection
- Stateful reasoning
- RAG over operational knowledge
- Historical incident memory
- Model and infrastructure diagnosis
- Human-in-the-loop recovery
- Post-action verification
- Agent evaluation
- Auditability and observability

A coding assistant can help analyze evidence that is manually supplied to it. This system is designed to autonomously determine **what evidence it needs, where to get it, what to do with it, and whether the resulting action worked**.

---

## Core Problem

Production ML systems can fail for many different reasons that produce similar symptoms.

For example, a drop in prediction quality may come from:

- Data drift
- A broken preprocessing transformation
- A bad model deployment
- Missing features
- Delayed upstream data
- Inference-service instability
- Configuration changes
- Infrastructure degradation

Traditional monitoring can alert engineers that a metric has changed, but it usually does not perform the entire diagnosis and recovery process.

This project explores whether an agentic AI system can perform that investigation reliably and measurably.

---

## Selected Initial Scope

Phase 0 is complete. I plan to implement a simulated equipment-failure prediction service using a seeded synthetic dataset and a RandomForestClassifier. Requests contain temperature, vibration, pressure, operating hours, and load; responses include failure probability and model/preprocessing versions. Production labels become available after a simulated delay so quality monitoring has realistic evidence constraints.

The initial incident catalogue covers sudden and gradual data drift, invalid features, a degraded model deployment, broken preprocessing, dependency latency, an inference-service crash, and a database outage. The first complete local workflow covers model rollback, preprocessing rollback, and a bounded inference-service restart before expanding to all eight incident families.

Read-only investigation runs automatically. Model/configuration rollback, pipeline reruns, and retraining require explicit operator approval. The only initial automatic operational mutation is one restart of an allowlisted disposable inference service per incident, after failed probes and a healthy database check. Database repair and unsupported actions lead to internal escalation. Recovery must pass verification on fresh traffic and, where relevant, newly released labels.

Initial acceptance targets include at least 90% incident detection recall, 80% exact root-cause accuracy, 90% verified recovery on recoverable cases, and zero unauthorized actions. The planned held-out benchmark has 60 cases, including healthy controls and compound incidents. Targets are not achieved results.

The complete scenario, normal-behavior contract, thresholds, permissions, metric definitions, and development milestones are in [Implementation_plan.md](Implementation_plan.md). Component boundaries and trust boundaries are in [docs/architecture.md](docs/architecture.md).

---

## Main Capabilities

### Production ML Monitoring

The system monitors:

- Feature distributions
- Prediction distributions
- Missing-value rates
- Schema violations
- Model-quality metrics
- Drift metrics
- Inference latency
- Error rate
- Service availability
- Dependency health
- Deployment versions
- Model versions
- Resource utilization

### Autonomous Investigation

The agent can:

- Interpret an incident
- Create an investigation plan
- Select relevant tools
- Query live metrics
- Query logs
- Compare model versions
- Inspect deployment history
- Inspect experiment history
- Retrieve operational knowledge
- Form root-cause hypotheses
- Test hypotheses
- Reject contradicted hypotheses
- Re-plan when evidence changes
- Decide when enough evidence exists for a diagnosis

### Recovery

Possible recovery actions include:

- Roll back to a previous model
- Switch to a known stable model
- Restart a service
- Rerun a pipeline
- Roll back configuration
- Trigger retraining
- Escalate to a human operator

High-impact actions can require explicit human approval.

---

## RAG Architecture

RAG is a first-class component of the project rather than a chatbot feature.

The agent can retrieve information from:

- Model cards
- Feature definitions
- Architecture documentation
- Service documentation
- Data contracts
- Deployment history
- Experiment summaries
- Monitoring guidelines
- Runbooks
- Remediation playbooks
- Previous incidents
- Postmortems
- Known failure patterns

### Retrieval Pipeline

```text
Operational Documents
        ↓
Parsing + Normalization
        ↓
Chunking
        ↓
Metadata Enrichment
        ↓
Embeddings
        ↓
PostgreSQL + pgvector
        ↓
Hybrid Retrieval
        ↓
Metadata Filtering
        ↓
Reranking
        ↓
Relevant Evidence
        ↓
Agent Investigation
```

### Planned Retrieval Features

- Semantic vector search
- Keyword retrieval
- Hybrid retrieval
- Metadata filtering
- Query rewriting
- Reranking
- Source attribution
- Retrieval evaluation

RAG performance will be measured using retrieval precision, recall, top-k accuracy, latency, and downstream diagnosis improvement.

---

## Agent Architecture

The project uses a stateful graph-based agent architecture.

### Orchestration

- LangGraph
- Stateful workflows
- Conditional branches
- Retry paths
- Checkpointing
- Human interrupts
- Persistent execution state

### Agent Loop

```text
Observe
  ↓
Plan
  ↓
Select Tool
  ↓
Act
  ↓
Observe Result
  ↓
Update Hypothesis
  ↓
Continue / Recover / Finish
```

### Multi-Agent Design

The initial implementation can begin with a strong single-agent baseline.

Specialized agents may then be introduced for:

- Data quality
- Model performance
- Infrastructure and serving
- Retrieval and historical context
- Recovery review

Multi-agent architecture will only be kept if evaluation shows that it improves diagnosis or recovery quality enough to justify the additional complexity.

---

## Tooling and MCP

The agent interacts with the environment through structured tools.

### Example Tools

- Current model metrics
- Historical model metrics
- Feature distributions
- Drift results
- Application logs
- Deployment history
- Model versions
- Experiment history
- Infrastructure health
- Pipeline health
- RAG retrieval
- Previous incidents
- Runbooks
- Rollback
- Model switching
- Service restart
- Retraining trigger
- Post-recovery verification

### MCP

The project will expose operational capabilities through one or more custom MCP servers.

MCP will be used for:

- Tool discovery
- Structured tool invocation
- Operational integrations
- Retrieval tools
- Safe recovery tools
- Permissions and authentication

---

## Human-in-the-Loop Safety

Not every recovery action should run automatically.

The system will classify actions by risk.

Examples:

```text
Read metrics              → automatic
Read logs                 → automatic
Retrieve runbook          → automatic
Compare model versions    → automatic
Restart non-critical task → configurable
Rollback model            → approval may be required
Modify infrastructure     → approval required
Trigger expensive job     → approval may be required
```

The workflow can pause, present evidence, request approval, and resume after the user accepts or rejects the proposed action.

---

## Evaluation

A major goal of this project is to evaluate the system rather than only demonstrate selected successful examples.

### Evaluation Dataset

The benchmark will contain representative incidents such as:

- Gradual drift
- Sudden drift
- Missing features
- Schema changes
- Bad deployments
- Inference latency
- Broken preprocessing
- Dependency failures
- Pipeline failures
- Infrastructure failures
- Multi-cause incidents

### Metrics

Planned metrics include:

- Incident-detection accuracy
- Root-cause diagnosis accuracy
- Recovery success rate
- Tool-selection accuracy
- Tool-call accuracy
- Retrieval precision
- Retrieval recall
- Hallucination rate
- Retry rate
- Average agent steps
- Investigation latency
- Time to recovery
- Token usage
- Cost per incident

### Architecture Comparisons

The system will compare:

```text
Direct LLM
vs
Single Agent
vs
Agent + RAG
vs
Agent + RAG + Memory
vs
Multi-Agent System
```

Additional comparisons may include:

- Vector retrieval vs hybrid retrieval
- No reranking vs reranking
- No memory vs memory
- No reflection vs reflection

---

## Observability

Both the monitored ML system and the AI agent will be observable.

### Application Observability

- OpenTelemetry
- Structured logs
- Metrics
- Distributed traces
- Health checks

### Agent Observability

- LLM calls
- Tool calls
- Retrieval events
- State transitions
- Retries
- Failures
- Human approvals
- Token usage
- Latency
- Cost

Possible tooling:

- LangSmith
- OpenTelemetry
- MLflow / Weights & Biases where useful

---

## MLOps / LLMOps / AgentOps

The project combines traditional ML production concerns with agent operations.

Planned capabilities include:

- Model versioning
- Prompt versioning
- Agent graph versioning
- Retrieval configuration versioning
- Evaluation dataset versioning
- Regression testing
- Automated evaluation
- Deployment validation
- Failure analysis
- Cost monitoring
- Latency monitoring
- Experiment tracking

The CI pipeline can block deployment if agent or retrieval performance regresses beyond defined thresholds.

---

## Tech Stack

### AI / Agents

- LLM APIs
- LangGraph
- LangChain where useful
- ReAct-style workflows
- Structured outputs
- Function calling
- Tool calling
- MCP
- RAG
- Agent memory
- Multi-agent coordination

### Retrieval

- Embeddings
- PostgreSQL
- pgvector
- Hybrid retrieval
- Metadata filtering
- Reranking

### Backend

- Python
- FastAPI
- PostgreSQL
- Redis
- Celery where useful
- REST APIs
- WebSockets / SSE

### Frontend

- React
- Next.js
- TypeScript

### Infrastructure

- Docker
- Docker Compose
- GitHub Actions
- CI/CD
- AWS / GCP / Azure
- Nginx or managed ingress

### Observability

- OpenTelemetry
- LangSmith
- MLflow / Weights & Biases where appropriate

---

## High-Level Architecture

```text
                         ┌─────────────────────┐
                         │  Production ML App  │
                         └──────────┬──────────┘
                                    │
                         Metrics / Logs / Events
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Monitoring + Alerts │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  LangGraph Agent    │
                         └──────────┬──────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
               ▼                    ▼                    ▼
        Live Telemetry          RAG Knowledge        MCP Tools
        / ML Metrics              Base               / Actions
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                                    ▼
                         Root-Cause Diagnosis
                                    │
                                    ▼
                         Recovery Recommendation
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                      Low Risk             High Risk
                         │                     │
                         ▼                     ▼
                    Auto Execute         Human Approval
                         │                     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                              Verification
                                    │
                                    ▼
                         Incident Memory + Report
```

---

## Repository Structure

The Phase 0 scaffold contains these component directories. They are placeholders for later implementation; no services or Compose configuration have been built yet.

```text
.
├── agent/
│   ├── graph/
│   ├── prompts/
│   ├── state/
│   ├── memory/
│   └── evaluation/
├── backend/
│   ├── api/
│   ├── services/
│   └── auth/
├── ml_service/
│   ├── training/
│   ├── inference/
│   ├── monitoring/
│   └── models/
├── simulation/
├── rag/
│   ├── ingestion/
│   ├── retrieval/
│   ├── reranking/
│   └── evaluation/
├── mcp/
│   ├── monitoring_server/
│   └── recovery_server/
├── frontend/
├── infrastructure/
├── tests/
├── evals/
├── data/
├── artifacts/
├── docs/
│   └── architecture.md
└── Writeup/
```

Generated data and artifacts are excluded from version control. Docker Compose configuration will be added when services are implemented.

---

## Demo Scenarios

The final project should include reproducible demonstrations such as:

### Scenario 1 - Data Drift

A feature distribution shifts significantly.

The system should:

1. Detect drift
2. Identify affected features
3. Retrieve the relevant model card and runbook
4. Inspect recent data changes
5. Diagnose likely cause
6. Recommend or trigger the appropriate recovery
7. Verify model performance afterward

### Scenario 2 - Bad Model Deployment

A newly deployed model causes a quality regression.

The system should:

1. Detect the degradation
2. Compare current and previous model versions
3. Retrieve deployment history
4. Identify the deployment as the likely cause
5. Propose rollback
6. Request approval if configured
7. Roll back
8. Verify recovery

### Scenario 3 - Serving Failure

Inference latency increases due to infrastructure or serving issues.

The system should:

1. Inspect latency metrics
2. Query infrastructure health
3. Inspect logs
4. Distinguish model issues from serving issues
5. Apply or recommend remediation
6. Confirm recovery

---

## Setup

Detailed setup instructions will be added as the implementation stabilizes.

Expected local requirements:

- Python
- Node.js
- Docker
- Docker Compose
- PostgreSQL
- Redis
- LLM provider credentials

---

## Project Status

Phase 0 is complete: the scope, success criteria, recovery policy, architecture, development milestones, and repository scaffold are defined. Model training and application implementation have not started.

### Planned Milestones

- [x] Phase 0: scope, success criteria, architecture, and repository scaffold
- [ ] Baseline ML system
- [ ] Production simulation
- [ ] Monitoring and drift detection
- [ ] RAG ingestion and retrieval
- [ ] RAG evaluation
- [ ] Agent tools
- [ ] MCP integration
- [ ] LangGraph investigation workflow
- [ ] Memory
- [ ] Human approval
- [ ] Recovery workflows
- [ ] Agent observability
- [ ] Benchmark suite
- [ ] AgentOps / LLMOps
- [ ] Frontend
- [ ] Cloud deployment
- [ ] Final evaluation

---

## Results

Quantitative results will be added after the benchmark suite is complete.

Planned reporting format:

| Metric | Baseline | Final System |
|---|---:|---:|
| Root-cause diagnosis accuracy | TBD | TBD |
| Recovery success rate | TBD | TBD |
| Retrieval precision | TBD | TBD |
| Retrieval recall | TBD | TBD |
| Average investigation time | TBD | TBD |
| Average cost per incident | TBD | TBD |

---

## Key Research Questions

This project will evaluate questions such as:

- Does RAG improve ML incident diagnosis?
- Does historical incident memory improve recovery decisions?
- Does hybrid retrieval outperform vector-only retrieval?
- Does reranking improve downstream diagnosis enough to justify added latency?
- Does multi-agent specialization outperform a well-designed single agent?
- How much does verification reduce incorrect recovery actions?
- What is the quality / latency / cost tradeoff of the final architecture?

---

## Limitations

Potential limitations include:

- The production environment is simulated rather than a real commercial system.
- Incident coverage will initially be limited to implemented fault scenarios.
- LLM reasoning is probabilistic.
- Automated recovery must remain constrained by strict permissions.
- Some evaluations may use synthetic or controlled incident data.
- Multi-agent coordination may not always outperform a simpler architecture.

---

## Future Work

Potential extensions:

- Kubernetes-native recovery
- Real cloud-provider integrations
- Online drift adaptation
- Automated retraining pipelines
- Canary model deployment
- Multi-region monitoring
- Advanced causal diagnosis
- Production alert-manager integrations
- Continuous learning from resolved incidents
- Broader support for different ML model types

---

## Final Goal

The finished system should demonstrate that an AI agent can do more than answer questions about a repository or analyze manually supplied logs.

It should show a complete autonomous workflow over a live ML production environment:

```text
detect
→ investigate
→ retrieve
→ reason
→ act
→ verify
→ remember
→ evaluate
```

The project is designed to combine **Agentic AI, RAG, MLOps, backend engineering, observability, DevOps, evaluation, and production safety** in one coherent system.
