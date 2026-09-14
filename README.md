# AegisVoice

*Voice can request. Security decides.*

AegisVoice is a secure voice-control layer for financial operations, built under the Aegisyn product umbrella. 

Crucially, it implements a **Zero-Trust Security Gateway** architecture. The LLM is treated as an untrusted user-interface component. It can only *propose* a structured action. The backend Security Gateway deterministically evaluates the proposed action against RBAC, beneficiary whitelists, limits, and risk heuristics before deciding to ALLOW, DENY, or require STEP_UP authentication.

---

## ?? Vercel Deployment Guide

This repository has been strictly optimized and configured for a seamless **Vercel Serverless deployment**. 

### 1. Environment Variables
Before your app will work on Vercel, you must configure the following in your Vercel Project Settings -> **Environment Variables**:

*   **ASSEMBLYAI_API_KEY**: Your AssemblyAI API key. *(Required for the voice agent to transcribe speech)*
*   **SECRET_KEY**: A random secure string used for internal hashing.
*   **Database URL**: Vercel automatically creates a database variable when you attach a **Neon Postgres** database to your project (e.g., POSTGRES_URL or egis_POSTGRES_URL). The app will automatically detect it.

### 2. Initializing the Database (Important!)
Because Vercel Serverless functions cannot run command-line scripts, you must initialize your database tables over the web.

After your app deploys successfully, open your browser and visit:
`
https://<your-vercel-domain>.vercel.app/api/setup
`
*You will see a success message confirming the database tables and test users have been generated!*

### 3. Testing the Voice Commands
Go to your main Vercel dashboard and click **Connect**. Once the microphone is listening, try speaking the following commands:

*   *"Transfer  to BEN-001"* (Standard approved vendor)
*   *"Transfer  to SYN-1001"* (Also works without using BEN!)
*   *"Transfer ,000 to SYN-9999"* (Triggers a rejection for unapproved vendors)
trigger deploy
---

## Tech Stack & Architecture

*   **Backend Engine:** FastAPI, Python 3.12, SQLAlchemy, Pydantic (Optimized to stay under Vercel's 250MB limit)
*   **Database:** Vercel Neon PostgreSQL
*   **Voice Agent:** AssemblyAI Realtime Voice Agent API
*   **Frontend:** Vanilla JavaScript, Tailwind CSS, RecordRTC

## Documentation
Comprehensive planning and architecture documents are located in the docs/ directory:
1. [Product Requirements Document (PRD)](docs/01-PRD.md)
2. [Architecture & Component Responsibilities](docs/02-ARCHITECTURE.md)
3. [Security, Threat Model & Privacy](docs/03-SECURITY.md)
4. [Data Model & Policy Engine](docs/04-DATA_MODEL.md)
5. [API Contracts & AssemblyAI Tools](docs/05-API_CONTRACTS.md)
6. [Testing Strategy & Security Test Plan](docs/06-TESTING.md)
7. [Architectural Decision Records (ADRs)](docs/07-ADRs.md)
8. [Implementation Roadmap](docs/08-ROADMAP.md)
