# API Specifications (LOS v2 — Loan Navigator Contract)

## Overview

This document specifies the **product API** required to make the Loan Navigator UI functional. The endpoints and payload shapes are derived from the UI calls and the shared schema in `/doc/02_Loan-Navigator-AI`.

**UI Source:** [/doc/02_Loan-Navigator-AI/client](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client)  
**Data Schema Source:** [schema.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/shared/schema.ts)

---

## Conventions

### Correlation IDs

- Clients may send `X-Correlation-ID`.
- Server generates one if absent and returns it.

### Officer Authorization (POC Boundary)

The Loan Navigator reference server uses a header token boundary:

- Header: `x-officer-role`
- Token: `loan-officer-access`

Reference: [routes.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/server/routes.ts)

LOS v2 must enforce this boundary for officer-only endpoints until upgraded to RBAC.

---

## 1) Conversations

### 1.1 Create Conversation

- **POST** `/api/conversations`
- **Body (optional)**:
  ```json
  { "chatRole": "borrower" }
  ```
- **Response (200)**:
  ```json
  { "conversation": { "id": "...", "status": "active", "chatRole": "borrower", "currentPhaseId": "..." }, "greeting": "..." }
  ```

### 1.2 List Conversations (Officer)

- **GET** `/api/conversations`
- **Officer required**
- **Response (200)**: array of conversations

### 1.3 Get Conversation

- **GET** `/api/conversations/:id`
- **Response (200)**: conversation

### 1.4 Update Conversation (Officer)

- **PATCH** `/api/conversations/:id`
- **Officer required**
- **Body**:
  ```json
  {
    "status": "active",
    "borrowerName": "string",
    "assignedOfficer": "string",
    "currentPhaseId": "string"
  }
  ```
- **Response (200)**: updated conversation

---

## 2) Messages

### 2.1 List Messages

- **GET** `/api/conversations/:id/messages`
- **Response (200)**: array of messages

### 2.2 Send Message (Borrower or Officer)

- **POST** `/api/conversations/:id/messages`
- **Body**:
  ```json
  { "content": "string" }
  ```
- **Response (200)**:
  ```json
  {
    "message": { "id": "...", "role": "assistant", "content": "..." },
    "intentAnalysis": { "seriousnessScore": 0, "fitScore": 0, "nextConversationAngle": "..." },
    "loanRecommendations": [],
    "phaseAction": null,
    "loanAction": null
  }
  ```

The server may also update the Conversation record after message handling.

---

## 3) Loan Phases

### 3.1 List All Phases

- **GET** `/api/phases`
- **Response (200)**: array of phases

### 3.2 List Active Phases

- **GET** `/api/phases/active`
- **Response (200)**: array of active phases ordered by `sortOrder`

---

## 4) Loans (Officer)

### 4.1 List Loans

- **GET** `/api/loans`
- **Officer required**
- **Response (200)**: array of loans

### 4.2 Patch Loan

- **PATCH** `/api/loans/:id`
- **Officer required**
- **Body**: partial loan fields (as per UI needs)
- **Response (200)**: updated loan

---

## 5) Catalog Products (Officer)

### 5.1 List Catalog Products

- **GET** `/api/catalog-products`
- **Officer required**
- **Response (200)**: array of products

### 5.2 Create Catalog Product

- **POST** `/api/catalog-products`
- **Officer required**
- **Body**: product fields (draft allowed)
- **Response (200)**: created product

### 5.3 Update Catalog Product

- **PATCH** `/api/catalog-products/:id`
- **Officer required**
- **Body**: partial product fields
- **Response (200)**: updated product

---

## Error Handling (Standard)

- **400** invalid body (include field errors)
- **401** unauthorized (invalid/missing auth token when required)
- **403** forbidden (borrower requesting officer resource)
- **404** not found
- **500** unexpected error (include correlation ID)

