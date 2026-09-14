# AegisVoice

*Voice can request. Security decides.*

AegisVoice is a secure voice-control layer for financial operations, built as a hackathon project under the Aegisyn product umbrella.

## Overview

AegisVoice allows authorized financial staff to use natural voice commands to initiate sensitive financial operations. It integrates with AssemblyAI for speech-to-text and intent extraction via tool calling. 

Crucially, it implements a **Zero-Trust Security Gateway** architecture. The LLM is treated as an untrusted user-interface component. It can only *propose* a structured action. The backend Security Gateway deterministically evaluates the proposed action against RBAC, beneficiary whitelists, limits, and risk heuristics before deciding to `ALLOW`, `DENY`, or require `STEP_UP` authentication.

This architecture renders prompt injection and LLM manipulation harmless from an execution standpoint.

## Tech Stack & Architecture

### LOCAL DEMO (Hackathon/Development)
*   **Backend Engine:** FastAPI, Python 3.14, SQLAlchemy, Pydantic.
*   **Database:** SQLite (local file).
*   **Caching/Rate Limiting:** In-Memory rate limiter (slowapi).
*   **Voice Agent:** AssemblyAI Realtime Voice Agent API.
*   **Frontend:** Vanilla JavaScript, Tailwind, RecordRTC.

*Note: The local configuration is suitable for single-process development and hackathon demonstrations only. It does not provide multi-worker concurrency safety or distributed rate limiting.*

### PRODUCTION (Deployment)
*   **Backend Engine:** FastAPI, Uvicorn/Gunicorn workers behind a TLS reverse proxy (Nginx/Envoy).
*   **Database:** PostgreSQL (for strict row-level locking, execution isolation, and `SELECT ... FOR UPDATE` support).
*   **Caching/Rate Limiting:** Redis (for distributed rate limit counters via slowapi).
*   **Secret Management:** Secrets injected via platform-level managers (AWS Secrets Manager, GCP).

## Documentation

Comprehensive planning and architecture documents are located in the `docs/` directory:

1. [Product Requirements Document (PRD)](docs/01-PRD.md)
2. [Architecture & Component Responsibilities](docs/02-ARCHITECTURE.md)
3. [Security, Threat Model & Privacy](docs/03-SECURITY.md)
4. [Data Model & Policy Engine](docs/04-DATA_MODEL.md)
5. [API Contracts & AssemblyAI Tools](docs/05-API_CONTRACTS.md)
6. [Testing Strategy & Security Test Plan](docs/06-TESTING.md)
7. [Architectural Decision Records (ADRs)](docs/07-ADRs.md)
8. [Implementation Roadmap](docs/08-ROADMAP.md)

## Current Status

*   **Phase 1:** Core Security Engine (Authentication, State Machine) - **COMPLETE**
*   **Phase 2:** IAM & Deterministic Policy Gateway (RBAC, Risk, Gateway) - **COMPLETE**
*   **Phase 3:** Execution & Approval Workflows - **COMPLETE**
*   **Phase 4:** AssemblyAI Voice Integration - **COMPLETE**
*   **Phase 5:** Live Integration, Rate Limiting, & Hardening - **COMPLETE**

The core backend architecture has been scaffolded and the security gateway is fully operational. 
- Implemented Authentication and JWT session management.
- Built explicit Identity -> RBAC -> Policy -> Risk evaluation flow.
- Configured synthetic Seed Data for isolated testing.
- Created `SecurityGateway` to deterministically block unapproved intents.
- Proven via extensive test suite that role spoofing and privilege escalation are blocked.


## Next Steps

With the architecture planned, implementation will proceed according to the [Implementation Roadmap](docs/08-ROADMAP.md), starting with initializing the backend and frontend repositories.

### Testing the Application

Once the database is initialized, you can test the voice interface. Try speaking the following commands:
- *"Transfer  to BEN-001"*
- *"Transfer  to SYN-1001"* (Works with other seeded vendors without using BEN)
- *"Transfer ,000 to SYN-9999"* (Triggers a rejection for unapproved vendors)
