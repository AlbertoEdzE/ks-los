# Deployment Guide (LOS v2)

## Purpose

This guide defines how LOS v2 should be run locally for development and how it should be deployed for staged demos. It mirrors the rigor of v1 execution practices while being aligned to the v2 product surfaces defined by the Loan Navigator UI.

**Source of Truth (UI):**  
[/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## 1. Local Development Topology (Target)

Services:

- Frontend: Loan Navigator UI (React)
- Backend API: product API + agent core
- Database: PostgreSQL (recommended for workflow entities)
- Optional: Redis (caching, job scheduling, events)
- Optional: Local LLM runtime (if used by the agent core)

---

## 2. Environment Configuration (Target)

Define a `.env` strategy for:

- Backend base URL for frontend
- Database connection string
- Officer auth token configuration (POC boundary)
- LLM provider selection (local-first, cloud fallback)

---

## 3. Seed Data Requirements (Target)

To guarantee repeatable demos and deterministic E2E tests, the system must support idempotent seeding for:

- Loan phases (ordered)
- Minimal catalog products set
- Optional demo conversations and loans

---

## 4. CI/CD Expectations (Target)

Minimum pipeline stages:

- Lint + typecheck
- Unit tests
- Integration tests
- Playwright E2E suite (smoke on PR; full on main)
- Artifact upload (Playwright HTML report and phase validation docs)

---

## 5. Rollout Strategy (POC → Pilot)

- POC: header-based officer boundary and deterministic seed datasets
- Pilot: RBAC authentication, audit retention, PII policies, and expanded observability

