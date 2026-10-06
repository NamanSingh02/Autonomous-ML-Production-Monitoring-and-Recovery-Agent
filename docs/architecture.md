# Planned System Architecture

This document describes the component boundaries for the scope defined in Phase 0 of Implementation_plan.md. These are planned components; the repository scaffold does not imply that services are implemented.

## Production and Investigation Flow

```text
Simulation traffic -> FastAPI inference -> versioned preprocessing + model
       |                    |
       |                    +-> predictions, logs, latency, health
       +-> delayed labels             |
                                      v
                         monitoring + anomaly detection
                                      |
                                      v
                               incident intake
                                      |
                                      v
                          LangGraph investigation agent
                             |                  |
                             v                  v
                      monitoring MCP       retrieval tool
                             |                  |
                             v                  v
                     telemetry + versions   pgvector + documents
                             |                  |
                             +--------+---------+
                                      v
                         evidence + cause hypotheses
                                      |
                                      v
                         recovery proposal + policy
                                      |
                         operator approval when required
                                      |
                                      v
                        recovery MCP -> allowlisted action
                                      |
                                      v
                         fresh-window outcome verification
                                      |
                                      v
                       incident report + persistent memory
```

## Responsibilities

| Location | Responsibility |
|---|---|
| ml_service/training | Synthetic dataset recipe, split manifests, training, evaluation, and model metadata |
| ml_service/inference | Input contract, versioned preprocessing, predictions, latency, and health endpoints |
| ml_service/monitoring | Feature and prediction statistics, delayed-label quality, service metrics, and incident signals |
| simulation | Seeded traffic, isolated label generation, and fault injection controlled by the benchmark harness |
| backend | Incident lifecycle, application APIs, approvals, access control, and event streaming |
| agent | Stateful investigation, evidence references, hypotheses, bounded tool use, and verification decisions |
| rag | Document ingestion, hybrid retrieval, filtering, reranking, source attribution, and retrieval evaluation |
| mcp/monitoring_server | Authorized read access to operational telemetry, metadata, and retrieval |
| mcp/recovery_server | Allowlisted actions, approval validation, idempotency, locks, and durable action audit |
| evals | Hidden expected causes, case manifests, independent scorers, and architecture comparisons |
| tests | Deterministic software checks and integration/end-to-end checks |
| frontend | Later monitoring, incident, evidence, approval, and evaluation dashboard |
| infrastructure | Later Compose definitions, environment configuration, CI, and deployment configuration |

## Data and State

PostgreSQL stores request metadata, released labels, telemetry aggregates, deployment history, incidents, tool executions, approvals, verification results, and persistent LangGraph checkpoints. pgvector stores operational-document and historical-incident embeddings. Large datasets and model artifacts live in local artifact storage initially, with metadata and content hashes in the database; object storage can replace the local store during deployment.

Every investigation has an incident ID and run ID. Evidence records carry source, observation time, service, model/preprocessing version where applicable, and a reference to the tool call or retrieved document. State contains the plan, observed evidence, hypotheses, pending action, approval status, attempt counters, and terminal outcome. A recovered incident requires observed verification results.

Redis is optional initially. Durable investigation state and approval records remain in PostgreSQL if Redis is later introduced for caching or job queues. Health probing and bounded local fallback logging continue during a database outage. Recovery mutations stop while durable audit recording is unavailable.

## Trust and Recovery Boundaries

The LLM proposes actions; the recovery server authorizes and executes them. Retrieved documents and tool-output text cannot grant permissions. Mutations require an allowlisted target, checked preconditions, an idempotency key, a service lock, and an audit record. Approval binds the exact proposed action and target version. Evidence gathering and proposed execution are separate tool capabilities.

The agent never receives evaluator answers or direct fault-injection access. Ordinary raw inputs, released labels, health signals, and deployment logs remain available for legitimate diagnosis. Delayed labels are released according to simulation time, not made available early by the agent's request.

A restart, rollback, or successful tool response begins verification rather than resolving an incident automatically. Disjoint post-action windows establish recovery. Conflicting symptoms, insufficient labels, failed actions, unavailable telemetry, or exhausted budgets leave an unresolved or escalated outcome.

## Initial Deployment Boundary

The first runnable environment will use Docker Compose for inference, monitoring/traffic processes, backend/agent execution, MCP endpoints, and PostgreSQL with pgvector. Directory boundaries do not require independent microservices. The initial agent runs as one investigator with persistent checkpoints. Monitoring and recovery tools have separate permissions even if initially hosted in the same deployment.

The backend streams structured stage, evidence, action, approval, and outcome events to the later frontend. Traces correlate these events with LLM calls, retrieval, and tool calls. Cloud deployment and worker scaling follow after the local workflow and benchmark pass their acceptance gates.
