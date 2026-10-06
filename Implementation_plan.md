# Agentic AI Project — Implementation Plan

## Project Objective

This project will be designed as a production-grade **Agentic AI / AI Agents** system rather than a simple chatbot.

The main goal is to demonstrate practical experience across:

- Agentic AI
- LLM application engineering
- Tool use and function calling
- Multi-step reasoning and execution
- Stateful workflows
- Multi-agent coordination
- Model Context Protocol (MCP)
- RAG and semantic retrieval
- Memory systems
- Evaluation and benchmarking
- Observability and tracing
- Backend engineering
- Security and guardrails
- DevOps
- MLOps / LLMOps / AgentOps
- Cloud deployment

The project should be strong enough to demonstrate both **Software Engineering** and **AI/ML Engineering** skills.

---

# Phase 0 - Selected Scope and Success Criteria

This section records the concrete scope I plan to implement. The capability sections below describe the broader project; optional technologies do not expand the initial release automatically. All numerical values here are initial configuration values or acceptance targets, not measured results.

## Objective and Problem Statement

I plan to monitor a simulated equipment-failure prediction service. Different faults can produce similar symptoms: changing sensor inputs, corrupted preprocessing, and a bad model deployment can all change predictions. My goal is to build an agent that distinguishes these causes using observable evidence, performs permitted recovery actions, and verifies the outcome. The simulation supports repeatable experiments without requiring access to a commercial production environment.

## Prediction Task and Data

- Task: binary classification of whether an equipment operating snapshot represents a failure event.
- Inputs: temperature in degrees Celsius, vibration in mm/s, pressure in bar, operating hours, and load percentage.
- Initial valid ranges: temperature 0-120, vibration 0-20, pressure 0-20, operating hours 0-50,000, and load 0-100. These are synthetic contract limits, not industrial safety limits.
- Output: failure probability, predicted class using a fixed 0.5 threshold, request ID, model version, preprocessing version, and measured inference latency.
- Dataset: a locally generated, seeded synthetic dataset with 30,000 training rows, 5,000 validation rows, and 5,000 held-out test rows. Production and benchmark streams use separate seeds and contain no rows from these splits.
- Generator: bounded sensor distributions with correlations between load, temperature, and vibration. A fixed nonlinear function of the underlying sensor values determines failure probability; Bernoulli sampling produces labels. Its parameters are calibrated on training data to a 20-40% positive rate and then frozen.
- Baseline model: a scikit-learn RandomForestClassifier with a fixed random seed. A deliberately degraded candidate is trained separately for deployment-fault experiments.
- Dataset splits, generator parameters, model artifacts, feature order, class threshold, and preprocessing versions are recorded together. Phase 1 implements and validates this recipe; no model has been trained in Phase 0.
- Labels are attached to the underlying operating snapshot before transport or preprocessing corruption. They become visible to quality monitoring after a simulated 120-second delay. The agent cannot access unreleased labels or the generator's hidden probability function.
- Synthetic equipment behavior is an experiment fixture. Results will support claims about the implemented scenarios, not real-world equipment reliability.

## Normal Production Behavior

I plan to start with one inference service and one active model in a local Docker Compose environment.

| Property | Initial definition |
|---|---|
| Traffic | 5 requests/second, with seeded variation between 2 and 10 requests/second |
| Reference data | Frozen validation feature distributions and quality measurements from the approved baseline model |
| Warm-up | At least 300 requests before distribution alerts and 1,000 released labels before quality alerts |
| Monitoring cadence | Every 30 seconds; 300-request rolling distribution and service windows; 1,000-label rolling quality windows |
| Service baseline | p95 end-to-end inference latency below 200 ms, server-error rate below 1%, availability at least 99% |
| Model baseline | Held-out ROC-AUC at least 0.80; PR-AUC above the held-out positive prevalence; F1, precision, recall, and Brier score also recorded |
| Input contract | Required numeric features, finite values, valid ranges, fixed feature order, and versioned preprocessing |
| Prediction behavior | Probability and positive-prediction distributions compared with the reference; confidence shifts are signals rather than proof of quality loss |

Health is assessed across data, quality, and serving signals. Missing telemetry or insufficient labels produces an unknown state rather than a healthy state. The 200 ms target is for the initial local environment; measured hardware and load accompany reported results.

## Initial Incident Catalogue

| ID | Cause category | Injected fault | Useful evidence | Expected response |
|---|---|---|---|---|
| D1 | Data | Sudden shift in temperature or vibration within contract ranges | Feature distributions, drift scores, request history, data runbook | Diagnose affected features; recommend data investigation or approved retraining; escalate if there is no safe remedy |
| D2 | Data | Gradual shift in load and correlated sensors | Distribution history and repeated drift windows | Distinguish gradual drift from a deployment change; investigate and escalate or propose approved retraining |
| D3 | Data | Missing, non-numeric, or out-of-range input features | Validation failures, schema-violation rates, input samples | Identify the contract violation and escalate to the data producer |
| M1 | Model | Deployment of the deliberately degraded model | Model versions, deployment history, delayed quality metrics, comparison on labeled requests | Propose approval-gated rollback to the known stable model |
| S1 | Serving/pipeline | Temperature conversion or feature-order corruption in preprocessing | Raw versus transformed features, preprocessing version, pipeline logs, quality metrics | Propose approval-gated rollback to the known stable preprocessing configuration |
| S2 | Serving/dependency | Added latency in a feature dependency | End-to-end and dependency spans, health checks, latency runbook | Identify the dependency; propose approval-gated rollback of the simulator's latency configuration |
| S3 | Serving | Inference-process crash while its database remains healthy | Failed health probes, request errors, process status | Perform one policy-permitted restart of the disposable inference service, then verify or escalate |
| I1 | Infrastructure | PostgreSQL unavailable | Connection errors, database health probes, telemetry gaps | Diagnose the outage and escalate; database repair is outside automatic recovery |

Two compound benchmark cases combine M1 with S2 and S1 with D3. The diagnosis can contain multiple causes; a partial fix cannot close an incident with remaining symptoms. Unknown or unsupported causes result in escalation.

Faults are injected by a separate simulation harness. The harness records the hidden incident ID, fault timing, affected component, and expected outcome for evaluation. The agent can inspect ordinary production telemetry and deployment records, but cannot read fault manifests, evaluator answers, hidden seeds, or fault-control tools.

## Initial Detection Rules

- Feature drift: population stability index (PSI) at least 0.20 for a monitored feature in two consecutive eligible windows. Numeric bins are fixed from the reference data, with overflow bins and epsilon smoothing. Constant or low-variation features use an explicit range or contract check when meaningful PSI bins cannot be formed.
- Prediction drift: PSI at least 0.20 for predicted probabilities in two consecutive eligible windows. This opens an investigation without claiming model-performance degradation.
- Input quality: more than 1% invalid requests in two consecutive eligible windows. Client validation failures are tracked separately from server errors.
- Model quality: ROC-AUC drops by at least 0.05 from the frozen reference in two consecutive eligible labeled windows. Both classes must be present; otherwise the metric is unavailable and the agent can escalate unresolved quality uncertainty.
- Serving latency: p95 above 500 ms in two consecutive eligible windows, measured end to end rather than only around model execution.
- Server errors: more than 5% 5xx responses or transport failures in two consecutive eligible windows.
- Availability: three consecutive failed probes at 10-second intervals for inference or a dependency. These probes continue independently of prediction storage.
- Severity: service or database unavailability is critical; sustained quality regression and server errors are high; drift and input violations are medium unless compounded with a higher-severity signal.
- Repeated alerts for the same service and signal are attached to the active incident. An incident can collect additional signals and causes without creating a separate investigation for every window.

These thresholds will be calibrated on development runs. Held-out benchmark results are not used to tune thresholds, prompts, or retrieval settings. Gradual-drift detection delay is measured from the first hidden fault window that crosses the configured drift threshold, with injection-to-detection delay also reported separately.

## Recovery Permissions and Verification

| Action | Policy |
|---|---|
| Read metrics, logs, runbooks, model metadata, and historical incidents | Automatic within authorized service scope |
| Record evidence, create an incident report, or mark an incident as requiring operator action | Automatic; escalation is an internal status change |
| Restart the disposable inference service | Automatic only after failed health probes, confirmation of the allowlisted service, and a healthy database; at most once per incident |
| Roll back or switch the model | Explicit operator approval |
| Roll back preprocessing or simulator dependency configuration | Explicit operator approval |
| Rerun a pipeline or start retraining | Explicit operator approval; implementation comes in later recovery phases |
| Repair a database, change cloud resources, delete data, run arbitrary shell commands, or send external notifications | No executable tool in the initial release; escalate internally |

The recovery server enforces these rules independently of the LLM. Approval is bound to incident ID, action, target, exact parameters, and expected current version, and expires after 10 minutes. A changed proposal requires fresh approval. Rejection or expiry resumes diagnosis or escalation without mutation.

Mutating tools require idempotency keys, precondition checks, timeouts, an audit record, and a per-service lock so concurrent incidents cannot execute conflicting changes. Each incident permits at most two recovery attempts, subject to the stricter single-restart limit. An unavailable audit store blocks mutations; infrastructure alerts use a bounded local fallback record and are reconciled when storage returns.

After an action, verification uses three fresh, non-overlapping windows of 300 requests. It requires availability of at least 99%, p95 latency below 200 ms, server errors below 1%, and invalid-input rate at or below 1%. Previously affected drift signals must fall below PSI 0.10. When quality was affected, at least 1,000 newly released labels with both classes must show ROC-AUC within 0.02 of the reference. Other active symptoms must also clear. Missing evidence leaves the incident unresolved. A 10-minute verification timeout leads to bounded replanning or escalation.

Natural distribution shifts may persist after a model change. The agent does not claim that rollback or retraining repaired the input distribution. Expected escalation is a valid outcome for those cases and is scored separately from successful recovery.

## Evaluation Protocol and Acceptance Targets

I plan to use 60 held-out end-to-end cases: six variants of each of the eight initial incident families (48), two compound cases, and ten healthy controls. Separate development seeds support tuning. Each case has expected causes, useful evidence, permitted actions, and a terminal outcome. Quality cases include enough traffic and released labels to satisfy the detection and verification windows.

| Metric | Definition and initial target |
|---|---|
| Incident detection recall | Detected faulty cases / 50 faulty cases; at least 90% |
| Healthy-case false alarm rate | Healthy cases with any incident / 10 controls; at most 10%; also report false alarms per healthy service-hour |
| Detection delay | Median and p95 by family; p95 at most 60 seconds after the first eligible threshold-crossing window for immediate faults, and at most 300 seconds for delayed quality faults |
| Root-cause accuracy | Exact expected cause set on all 50 faulty cases, with missed incidents scored incorrect; at least 80%; also report accuracy conditional on detection and per-family results |
| Recovery success | Verified recovery / all cases marked recoverable in the benchmark; at least 90%; report numerator and denominator and conditional success among attempted recoveries |
| Escalation correctness | Correct evidence-supported escalation / cases requiring escalation; at least 90% |
| End-to-end task success | Correct diagnosis and permitted verified recovery or expected escalation / all 60 cases; at least 80% |
| Unauthorized actions | Zero; any mutation without required approval or outside the allowlist fails the acceptance gate |
| False recovery actions | Zero mutating actions on healthy controls; failed and harmful actions on faulty cases reported separately |
| Tool-call validity | Schema-valid calls / all attempted tool calls; at least 99% |
| Retrieval precision@5 / recall@5 | Relevant retrieved sources / retrieved sources, and retrieved relevant sources / labeled relevant sources; targets at least 0.60 / 0.80 on 30 separate held-out queries |
| Investigation latency | p95 at most 120 seconds from incident intake to diagnosis and recovery proposal or escalation; approval waiting and outcome verification measured separately |
| Time to recovery | Injection-to-verified-resolution and action-to-verified-resolution, median and p95; action-to-verification target at most 600 seconds on recoverable cases, excluding operator wait |
| Agent budget | At most 20 tool calls and 30 graph transitions per investigation; exhaustion produces a recorded escalation |
| Cost | Mean LLM, embedding, and reranking API cost at most USD 0.50 per case; include retries, token counts, price configuration, and aggregate benchmark cost; infrastructure cost reported separately |
| Evidence quality | Every final diagnosis cites tool evidence or retrieved sources; unsupported factual claims reviewed and reported, with an initial target of at most 5% of audited claims |

Initial retrieval queries cover model cards, data contracts, deployment records, runbooks, and past incidents. Relevance labels refer to source documents rather than duplicate chunks. The top five unique sources form the evaluation set. Benchmark outputs include raw counts and uncertainty intervals; the small initial benchmark is a starting point rather than proof of production reliability.

The first comparisons use a direct LLM with a fixed evidence bundle, a single tool-using agent without RAG, and the same agent with RAG. They share cases, model configuration, action policy, and budgets. Memory and multi-agent comparisons follow after those baselines work. Past-incident memory cannot contain answers from the held-out suite. All runs record model, prompt, graph, tool, retrieval, generator, and benchmark versions.

## Architecture and Implementation Boundaries

The planned component boundaries and data flow are documented in [docs/architecture.md](docs/architecture.md). The initial stack is Python, FastAPI, scikit-learn, LangGraph, PostgreSQL with pgvector, custom monitoring and recovery MCP servers, and Docker Compose. A single agent is the baseline. Redis and workers are added when background execution needs them; the Next.js dashboard, cloud provider selection, and optional specialists follow their roadmap phases.

I plan to ship the first complete local workflow for M1, S1, and S3 before expanding to every initial incident family. These three cases cover approved rollback, pipeline diagnosis, and bounded automatic recovery. The full initial acceptance benchmark then covers all eight families and the compound cases. No Kubernetes, arbitrary code execution, real equipment integration, or automatic cloud mutation is included in this scope.

## Development Milestones

| Milestone | Roadmap phases | Exit evidence |
|---|---|---|
| M0: Scope | 0 | Recorded scenario, contracts, incident catalogue, policies, metrics, architecture, and repository scaffold |
| M1: Observable simulation | 1-4 | Versioned baseline model, validated inference API, traffic generator, reproducible faults, and telemetry alerts |
| M2: Knowledge and tools | 5-9 | Operational corpus, retrieval evaluation, typed tools, and monitoring/recovery MCP integration |
| M3: First complete local workflow | 10-12, 14-18, with relevant testing from 24 | Single-agent investigation, approvals, enforced recovery policy, verification, traces, and M1/S1/S3 demonstrations |
| M4: Measured full incident coverage | Remaining initial cases, 19-21, and 13 only if justified | Held-out benchmark, architecture comparisons, versioned results, and evaluated memory or specialist additions |
| M5: Application and deployment | 22-27 | Backend, dashboard, CI, cloud deployment, and load/reliability checks |
| M6: Final evidence | 28-30 | Final quantitative results, reproducible demos, documentation, and portfolio presentation |

The roadmap groups capabilities; it is not a rule to postpone security, approvals, traces, or tests until after recovery code exists. Their minimum enforcement accompanies the first mutating tool.

---

# 1. LLM / Generative AI Core

The project will integrate one or more modern LLM providers and support production-style model interaction.

## Planned Components

- OpenAI API and/or Anthropic API and/or Gemini API
- Structured outputs
- JSON-schema-based responses
- Function calling
- Tool calling
- Prompt engineering
- System prompt design
- Context management
- Context-window optimization
- Model selection and routing
- Fallback models
- Retry policies for failed LLM calls
- Temperature and decoding configuration
- Token usage tracking
- Cost tracking

## Possible Model Routing

The application may route tasks to different models depending on:

- Task complexity
- Required latency
- Cost
- Tool-use capability
- Context-window requirements
- Reliability requirements

Example:

```text
Simple task        -> smaller / cheaper model
Complex planning   -> stronger reasoning model
Structured output  -> model optimized for schema adherence
Fallback           -> alternate provider/model
```

---

# 2. Agent Architecture

The project will implement a genuine agentic execution loop rather than a fixed sequence of LLM calls.

The core execution pattern will follow:

```text
Goal
  |
  v
Reason / Plan
  |
  v
Choose Action
  |
  v
Call Tool
  |
  v
Observe Result
  |
  v
Update State
  |
  v
Decide Next Action
  |
  +----> repeat if task is incomplete
  |
  v
Final Result
```

## Planned Agent Capabilities

- Goal interpretation
- Planning
- Task decomposition
- Dynamic tool selection
- Multi-step execution
- State management
- Conditional branching
- Retry logic
- Failure recovery
- Reflection / verification
- Self-correction
- Human approval checkpoints
- Completion detection

The system should be able to adapt its execution path based on the results of previous actions instead of following a completely hard-coded workflow.

---

# 3. Agent Orchestration

The main orchestration framework will likely be:

- **LangGraph**

LangChain may be used where useful, but LangGraph will be preferred for explicit agent-state and graph-based workflows.

## Planned LangGraph Concepts

- State graphs
- Nodes
- Edges
- Conditional edges
- Shared state
- Checkpointing
- Persistence
- Interrupts
- Human-in-the-loop execution
- Parallel branches
- Subgraphs
- Retry paths
- Failure states

## Architectural Goal

The execution flow should be visible and understandable as a state machine rather than hidden inside a single large agent prompt.

---

# 4. ReAct-Style Agent Loop

The project will implement a reasoning/action/observation pattern similar to ReAct.

Conceptually:

```text
Reason
  |
  v
Action
  |
  v
Tool Call
  |
  v
Observation
  |
  v
Reason Again
```

The agent should use tool outputs to determine its next action instead of producing a final answer immediately.

---

# 5. Tool / Function Calling

Tool use will be a central part of the project.

The agent should have access to multiple tools and determine which ones to use.

## Tool Categories

Potential tool types include:

- REST API tools
- Database query tools
- Search tools
- File tools
- Document retrieval tools
- Code execution tools
- External SaaS/API integrations
- Internal application tools
- Custom business logic tools

## Tool Engineering

Each tool should have:

- Clear schema
- Typed inputs
- Structured outputs
- Input validation
- Error handling
- Timeouts
- Authentication where needed
- Permissions
- Logging
- Retries
- Observability

Tool outputs should be machine-readable whenever possible.

---

# 6. Model Context Protocol (MCP)

MCP will be an important component of the project.

## Planned MCP Work

- Implement at least one custom MCP server
- Expose project-specific tools through MCP
- Connect the agent to MCP servers
- Support MCP tool discovery
- Handle MCP tool invocation
- Implement authentication or permissions where appropriate
- Support more than one MCP server if practical

## MCP Concepts to Demonstrate

- MCP server
- MCP client
- Tool discovery
- Resource discovery
- Structured tool interfaces
- External context providers
- Secure tool access

MCP should be used as a real architectural component rather than only added as a keyword.

---

# 7. RAG as an Agent Tool

The project will include retrieval, but RAG will not be the entire project.

Instead, retrieval will be one capability available to the agent.

## Planned RAG Components

- Document ingestion
- Chunking
- Embeddings
- Vector database
- Semantic search
- Metadata filtering
- Hybrid retrieval
- Reranking
- Query rewriting
- Retrieval evaluation

## Possible Vector Stores

- PostgreSQL + pgvector
- Qdrant
- Pinecone

PostgreSQL + pgvector is preferred if it fits naturally with the rest of the stack.

## Retrieval Flow

```text
Agent
  |
  v
Determines that external knowledge is needed
  |
  v
Calls retrieval tool
  |
  v
Hybrid search
  |
  v
Reranking
  |
  v
Relevant context returned
  |
  v
Agent continues task
```

---

# 8. Agent Memory

The system will support both temporary and persistent memory.

## Short-Term Memory

Used for:

- Current conversation
- Current task
- Intermediate reasoning state
- Previous tool results
- Current plan

## Long-Term Memory

Used for:

- Previously learned user preferences
- Past task outcomes
- Reusable facts
- Historical interactions
- Persistent agent state

## Memory Storage

Possible technologies:

- PostgreSQL
- Redis
- pgvector

## Memory Features

- Semantic memory retrieval
- Structured memory
- Episodic memory
- Memory summarization
- Memory relevance scoring
- Memory expiration
- Memory cleanup
- Deduplication
- Retrieval based on current task context

---

# 9. Multi-Agent Architecture

The project may include multiple specialized agents where doing so provides a real architectural benefit.

The design should avoid adding multiple agents purely for the sake of using the term "multi-agent."

## Possible Architecture

```text
                    Supervisor / Orchestrator
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
        Specialist A     Specialist B     Specialist C
             |                |                |
             +----------------+----------------+
                              |
                              v
                        Final Synthesizer
```

## Planned Multi-Agent Concepts

- Supervisor/orchestrator agent
- Specialized worker agents
- Agent-to-agent handoffs
- Role-specific prompts
- Role-specific tools
- Shared state
- Isolated context
- Controlled information sharing
- Parallel execution
- Review / critique agents
- Conflict resolution
- Result aggregation

---

# 10. Human-in-the-Loop

The project will include explicit human approval for actions that should not be performed autonomously.

## Possible Approval Points

- High-impact actions
- Destructive operations
- External API mutations
- Expensive operations
- Final deployment
- Sensitive data access

## Planned Capabilities

- Pause execution
- Present planned action
- Allow user approval/rejection
- Resume execution
- Modify plan after rejection

---

# 11. Evaluation Framework

Evaluation will be one of the most important components of the project.

The project should not only demonstrate that the agent works on selected examples. It should measure performance systematically.

## Evaluation Dataset

A dedicated benchmark dataset will be created containing representative tasks.

Possible size:

- 50-100+ evaluation tasks

Each task should have:

- Input
- Expected behavior
- Expected tool usage when relevant
- Success criteria
- Ground-truth output where possible
- Failure conditions

## Metrics

The system will measure:

- Task success rate
- Tool-call accuracy
- Tool-selection accuracy
- Structured-output validity
- Retrieval precision
- Retrieval recall
- Hallucination rate
- Failure rate
- Retry rate
- Number of agent steps
- Average execution time
- LLM latency
- Tool latency
- Token usage
- Cost per task
- Completion rate

## Comparative Evaluation

Possible comparisons:

```text
Single LLM
vs
Single ReAct Agent
vs
Agent + RAG
vs
Multi-Agent System
```

Possible model comparisons:

```text
Model A vs Model B
```

Possible architecture comparisons:

```text
No reranking vs reranking
No memory vs memory
Single-agent vs multi-agent
No reflection vs reflection
```

The project should produce quantitative results that can later be included in resume bullets.

---

# 12. LLM / Agent Observability

The full agent execution should be traceable.

## Planned Tools

- LangSmith
- OpenTelemetry

Other observability tools may be used if needed.

## Data to Trace

- LLM calls
- Prompts
- Model responses
- Tool calls
- Tool outputs
- Agent state transitions
- Errors
- Retries
- Latency
- Token usage
- Cost
- Retrieval events
- Agent decisions
- User approvals

## Goal

Every failed task should be diagnosable from logs and traces.

---

# 13. Backend Engineering

The project will include a production-style backend.

## Primary Stack

- Python
- FastAPI
- PostgreSQL
- Redis

## Planned Backend Features

- REST APIs
- Async endpoints
- WebSockets and/or Server-Sent Events
- Streaming responses
- Background tasks
- Authentication
- Authorization
- JWT
- Request validation
- Error handling
- Rate limiting
- API versioning where appropriate

## Background Processing

Possible technologies:

- Celery
- Redis queues

Background jobs may be used for:

- Long-running agent tasks
- Evaluation runs
- Data ingestion
- Embedding generation
- Scheduled processing

---

# 14. Frontend

A frontend may be built using:

- React
- Next.js
- TypeScript

## Planned UI Features

- User task submission
- Streaming agent output
- Real-time execution progress
- Current plan display
- Tool-call visualization
- Intermediate state visualization
- Human approval prompts
- Agent execution history
- Final result display
- Evaluation dashboard
- Cost/latency metrics
- Trace inspection

The frontend should make the agent's execution understandable rather than showing only a final chatbot response.

---

# 15. Security and Guardrails

Security will be treated as a first-class part of the architecture.

## Planned Security Features

- Authentication
- Authorization
- Role-based access where appropriate
- Tool permissions
- Input validation
- Output validation
- Secret management
- API key protection
- Rate limiting
- Audit logs

## Agent-Specific Security

- Prompt-injection defenses
- Tool-use restrictions
- Allowed-action policies
- Sandboxed execution
- Restricted filesystem access
- Restricted network access where needed
- Human approval for sensitive actions
- Validation before executing model-generated commands

## Principle

The LLM should not automatically have unrestricted access to every tool.

---

# 16. Sandboxed Execution

If the project requires code execution or potentially unsafe actions, those actions will run in a controlled environment.

Possible technologies:

- Docker containers
- Ephemeral containers
- Restricted subprocess execution

The sandbox should limit:

- Filesystem access
- Network access
- CPU usage
- Memory usage
- Execution time

---

# 17. Testing

The project will include comprehensive software testing.

## Planned Testing Layers

- Unit tests
- Integration tests
- API tests
- Agent workflow tests
- Tool tests
- Retrieval tests
- End-to-end tests
- Evaluation tests

Possible frameworks:

- pytest
- Playwright or Cypress for frontend testing

Agent tests should include deterministic assertions wherever possible.

---

# 18. DevOps

DevOps will be part of the project, but it will support the AI-agent system rather than become the main focus.

## Planned DevOps Technologies

- Docker
- Docker Compose
- GitHub Actions
- CI/CD
- AWS / GCP / Azure
- Nginx or managed ingress
- Environment management
- Secret management
- Health checks
- Logging
- Monitoring

## CI Pipeline

The CI pipeline should perform tasks such as:

```text
Code Push
  |
  v
Lint
  |
  v
Unit Tests
  |
  v
Integration Tests
  |
  v
Agent Evaluation Suite
  |
  v
Security / Validation Checks
  |
  v
Build Docker Image
  |
  v
Deploy
```

## Kubernetes

Kubernetes will only be added if the application architecture actually benefits from it.

It should not be included purely as a resume keyword.

Possible reasons to use Kubernetes:

- Multiple independently deployed services
- Agent workers
- Scalable inference services
- Background job workers
- High concurrency
- Horizontal scaling

---

# 19. Cloud Deployment

The project will be deployed publicly on a cloud platform.

Possible platforms:

- AWS
- GCP
- Azure

## Possible Cloud Components

- Compute instances
- Managed PostgreSQL
- Redis
- Object storage
- DNS
- HTTPS
- Load balancing
- Secrets manager
- Logging
- Monitoring

The final system should be accessible through a real deployed application rather than only running locally.

---

# 20. MLOps / LLMOps / AgentOps

MLOps will be part of the project, but the implementation will focus primarily on **LLMOps / AgentOps** because the main system is based on LLM agents rather than traditional model training.

## Planned LLMOps / AgentOps Features

- Prompt versioning
- Agent graph versioning
- Model version tracking
- Evaluation dataset versioning
- Regression testing
- Automated evaluation
- Model comparison
- Prompt comparison
- Architecture comparison
- Cost monitoring
- Latency monitoring
- Failure analysis
- Production tracing
- Experiment tracking
- Deployment validation

## Example Deployment Workflow

```text
Change Prompt / Tool / Agent Graph / Model
                  |
                  v
           Run Eval Suite
                  |
                  v
      Measure Quality / Cost / Latency
                  |
                  v
          Compare to Baseline
                  |
                  v
      Regression Detected?
           /            \
         Yes             No
          |               |
          v               v
     Block Deploy      Deploy
```

---

# 21. Experiment Tracking

Experiments should be reproducible.

Each experiment should track:

- Model
- Prompt version
- Agent architecture version
- Retrieval settings
- Tool configuration
- Memory configuration
- Evaluation dataset version
- Success metrics
- Latency
- Token usage
- Cost

Possible tools:

- MLflow
- Weights & Biases
- LangSmith

---

# 22. Failure Recovery

The agent should explicitly handle failures.

Examples:

- Tool timeout
- Invalid tool arguments
- External API failure
- Malformed structured output
- Retrieval failure
- LLM refusal
- Context overflow
- Rate limits
- Database errors
- Partial task completion

## Recovery Strategies

- Retry with backoff
- Correct malformed arguments
- Call alternate tool
- Use alternate model
- Re-plan
- Ask for human input
- Roll back action
- Gracefully terminate

---

# 23. Reliability Engineering

The system should include production reliability features.

## Planned Features

- Timeouts
- Retries
- Exponential backoff
- Circuit breakers where appropriate
- Idempotent operations
- Graceful degradation
- Error boundaries
- Fallback models
- Health checks
- Structured logging

---

# 24. Data and State Architecture

The system will separate different categories of data.

## PostgreSQL

Possible uses:

- Users
- Tasks
- Agent runs
- Tool executions
- Persistent memory
- Evaluation datasets
- Experiment results

## pgvector

Possible uses:

- Document embeddings
- Semantic memory
- Retrieval index

## Redis

Possible uses:

- Caching
- Temporary agent state
- Queues
- Rate limiting
- Sessions

---

# 25. Streaming and Real-Time Execution

Agent runs can take time, so the application should stream progress to the user.

Possible technologies:

- Server-Sent Events
- WebSockets

Events may include:

```text
Task received
Planning
Calling tool
Tool completed
Retrieving context
Running specialist agent
Waiting for approval
Retrying
Generating final answer
Completed
```

---

# 26. Architecture Principles

The project should follow these principles:

1. The LLM should decide at least part of the workflow dynamically.
2. Tools should be modular and independently testable.
3. Agent state should be explicit.
4. Failures should be recoverable.
5. Every important execution step should be observable.
6. Evaluation should be quantitative.
7. Security should restrict what the agent can do.
8. RAG should be a capability, not the entire architecture.
9. Multi-agent design should only be used where specialization adds value.
10. Infrastructure should support the AI architecture instead of overshadowing it.

---

# 27. Core Technology Stack

The preferred stack currently includes:

## AI / Agents

- LLM APIs
- LangGraph
- LangChain where useful
- ReAct
- Structured Outputs
- Function Calling
- Tool Calling
- MCP
- Multi-Agent Systems
- RAG
- Agent Memory

## Retrieval

- Embeddings
- PostgreSQL
- pgvector
- Hybrid Retrieval
- Reranking

## Backend

- Python
- FastAPI
- PostgreSQL
- Redis
- Celery
- REST APIs
- WebSockets / SSE

## Frontend

- React
- Next.js
- TypeScript

## Infrastructure

- Docker
- Docker Compose
- GitHub Actions
- CI/CD
- AWS / GCP / Azure
- Nginx
- Kubernetes only if justified

## Evaluation / Observability

- LangSmith
- OpenTelemetry
- MLflow or Weights & Biases where useful

---

# 28. Highest-Priority Resume Skills

The project should ideally provide real experience with the following resume keywords:

- Agentic AI
- AI Agents
- LLMs
- Generative AI
- LangGraph
- MCP
- Tool Calling
- Function Calling
- Multi-Agent Systems
- ReAct
- RAG
- Vector Databases
- Embeddings
- Hybrid Retrieval
- Reranking
- Agent Memory
- Structured Outputs
- Human-in-the-Loop
- LLM Evaluation
- Agent Evaluation
- Agent Observability
- LLMOps
- AgentOps
- FastAPI
- PostgreSQL
- pgvector
- Redis
- Docker
- GitHub Actions
- CI/CD
- Cloud Deployment
- OpenTelemetry
- LangSmith

---

# 29. Priority Order

The most important parts of the project are:

## Tier 1 — Essential

- Genuine agentic workflow
- LangGraph orchestration
- Tool calling
- Multi-step execution
- Stateful agent
- MCP
- RAG as a tool
- Agent memory
- Failure recovery
- Evaluation framework
- Observability
- Production backend
- Docker
- Cloud deployment

## Tier 2 — Strong Differentiators

- Multi-agent architecture
- Human-in-the-loop
- Hybrid retrieval
- Reranking
- Prompt-injection protection
- Sandboxed execution
- Automated agent regression testing
- Cost/latency benchmarking
- Model routing
- Model fallback

## Tier 3 — Add When Architecturally Justified

- Kubernetes
- Multiple independent microservices
- Advanced distributed workers
- Multiple LLM providers
- Complex autoscaling
- Full experiment-tracking platform

---

# 30. Final Project Standard

The final project should demonstrate more than:

> "I built an application that calls an LLM API."

It should demonstrate:

> "I designed, evaluated, deployed, and operated a production-style agentic AI system that autonomously plans multi-step tasks, selects and invokes tools, retrieves knowledge, maintains state and memory, coordinates specialized agents, recovers from failures, and is evaluated through measurable quality, cost, latency, and reliability metrics."

The project should ultimately provide strong evidence of skills across:

```text
Software Engineering
        +
AI Engineering
        +
Agentic AI
        +
LLMOps / AgentOps
        +
Cloud / DevOps
```

while avoiding unnecessary duplication with existing projects in traditional ML, computer vision, distributed ML, and general full-stack development.
