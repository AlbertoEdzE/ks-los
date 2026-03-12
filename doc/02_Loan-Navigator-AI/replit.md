# LoanAssist AI - Loan Origination System

## Overview
An AI-powered loan origination system with an agentic chat assistant for borrowers and a structured dashboard for loan officers. Includes a configurable loan lifecycle pipeline managed via officer chat.

## Architecture
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: Express.js + TypeScript
- **Database**: PostgreSQL (Drizzle ORM)
- **AI**: OpenAI GPT-5 for intelligent chat assistant
- **Design**: Three-mode theme system (Light, Dark Netflix-style, Glass Apple-style) with ThemeProvider. Apple-style rounded-3xl corners on cards/bubbles. Smooth animated transitions. Theme persisted in localStorage.
  - Light: Soft gradient (slate-50 → white → blue-50), teal accents, white cards
  - Dark: Netflix-style pure blacks (#0d0d0d, #141414, #1a1a1a), neutral tokens, teal accents
  - Glass: Dark base + frosted transparency (backdrop-blur, rgba backgrounds), Apple Control Center aesthetic

## Key Features
1. **Borrower Chat Interface** (`/`): AI-powered conversational assistant that understands borrower intent, urgency, affordability, and recommends loan products with trade-off analysis. Includes a visual phase progression tracker with clickable phases linking to phase detail pages.
2. **Officer Dashboard** (`/dashboard`): Loan officers see structured intent summaries, seriousness/fit scores, AI-recommended products, and suggested conversation angles. Nav links to Pipeline, Products, Lifecycle, and Borrower Chat.
3. **Loan Officer Assistant** (`/officer-chat`): Officers manage loan lifecycle phases AND create/manage loan applications via chat. AI performs deep analysis of borrower profiles, auto-populates all fields (interest rate, EMI, credit score, LTV, etc.), and officers can edit any field inline. Phase items are clickable.
4. **Loan Product Catalog** (`/loan-products`): Salesforce-style product catalog with search, filter, create, edit, delete, and detail view. 28 preseeded products across 9 categories.
5. **Phase Detail Pages** (`/phases/:id`): Rich detail page for each loan lifecycle phase showing typical timeline, key activities, required documents, stakeholders, and common bottlenecks.
6. **Loan Pipeline** (`/pipeline`): Kanban-style officer workspace for processing loan applications through all lifecycle phases. Phase advancement, status updates, and loan detail view.

## Data Model
- `users`: Basic user accounts
- `conversations`: Chat sessions with AI-extracted intent summaries, scores, recommended products, status tracking, and chatRole (borrower/officer)
- `messages`: Individual chat messages with metadata (intent analysis, loan recommendations, phase actions, loan actions)
- `loan_phases`: Configurable loan lifecycle phases with soft-delete (isActive flag), ordering, colors, icons
- `loans`: Structured loan applications with borrower details, financial analysis, AI-populated fields, lifecycle tracking
- `loan_product_catalog`: Salesforce Financial Cloud-style lending product templates — rate ranges, tenure, eligibility, docs, features, risk grade, status lifecycle (draft/active/suspended/archived)

## Loan Lifecycle Phases (Default)
1. Lead & Inquiry
2. Application Submission
3. Document Collection & KYC
4. Verification & Credit Appraisal
5. Underwriting & Credit Decision
6. Conditional Approval & Offer
7. Security & Legal Documentation
8. Pre-Disbursement Checks
9. Disbursement

## Project Structure (Modular Atomic Architecture)
```
client/src/
  pages/                                   - Slim orchestrator files (state + layout only)
    chat.tsx                               - Borrower chat page
    officer-dashboard.tsx                  - Officer dashboard page
    officer-chat.tsx                       - Officer lifecycle chat page
    loan-products.tsx                      - Product catalog page
    phase-detail.tsx                       - Phase detail page
    loan-pipeline.tsx                      - Kanban pipeline page

  components/
    layout/
      glass-panel.tsx                      - Shared GlassPanel (frosted glass card wrapper)
      page-header.tsx                      - Shared header with KSquare logo, nav, theme toggle
    dashboard/
      stats-card.tsx                       - Stats cards (Total Leads, Active, etc.)
      score-ring.tsx                       - SVG circular score indicator
      conversation-card.tsx                - Lead card in sidebar
      conversation-detail.tsx              - Full lead detail view with scores/intent/products
      intent-field.tsx                     - Intent summary field row
      empty-state.tsx                      - No-selection placeholder
    chat/
      phase-tracker.tsx                    - Phase progress tracker strip
      chat-bubble.tsx                      - Chat message bubble (imports loan-card)
      loan-card.tsx                        - Loan recommendation card
      typing-indicator.tsx                 - Typing animation dots
      welcome-state.tsx                    - Welcome screen with quick prompts
    officer/
      lifecycle-pipeline.tsx               - Phase pipeline sidebar
      loans-panel.tsx                      - Loans sidebar panel
      editable-loan-card.tsx               - Inline-editable loan card
      loan-type-icon.tsx                   - Icon selector by loan type
      officer-chat-bubble.tsx              - Officer chat message bubble
      officer-typing-indicator.tsx         - Officer typing animation
      phase-action-result.tsx              - Phase action success/error display
      loan-action-result.tsx               - Loan action success/error display
    products/
      constants.ts                         - Categories, statuses, risk grades, helpers
      badges.tsx                           - CategoryIcon, StatusBadge, RiskBadge
      product-card.tsx                     - Product catalog card
      product-form.tsx                     - Create/edit product modal
      product-detail.tsx                   - Product detail modal
    pipeline/
      pipeline-card.tsx                    - PipelineLoanCard + PhaseColumn
      loan-detail-panel.tsx                - Loan detail modal with phase/status controls

  constants/
    phase-knowledge.ts                     - Static knowledge base for 10 lifecycle phases (300+ lines)

  components/theme-provider.tsx            - ThemeProvider (Light/Dark/Glass) + ThemeToggle

server/
  openai.ts                                - OpenAI integration with role-based prompts
  routes.ts                                - API endpoints
  storage.ts                               - Database CRUD operations
  seed-phases.ts                           - Default phase seeder
  seed-products.ts                         - Loan product catalog seeder (28 products, 9 categories)
shared/schema.ts                           - Drizzle schema + Zod types
```

## API Endpoints
- `POST /api/conversations` - Create new conversation (body: { chatRole?: "borrower"|"officer" })
- `GET /api/conversations` - List all conversations
- `GET /api/conversations/:id` - Get single conversation
- `GET /api/conversations/:id/messages` - Get conversation messages
- `POST /api/conversations/:id/messages` - Send message (triggers AI response + phase actions for officer)
- `PATCH /api/conversations/:id` - Update conversation status/currentPhaseId
- `GET /api/phases` - Get all phases (including deactivated)
- `GET /api/phases/active` - Get only active phases
- `GET /api/loans` - Get all loan applications
- `GET /api/loans/:id` - Get single loan
- `PATCH /api/loans/:id` - Update loan fields (officer edits)
- `GET /api/catalog-products` - List all catalog products
- `GET /api/catalog-products/:id` - Get single catalog product
- `POST /api/catalog-products` - Create catalog product
- `PATCH /api/catalog-products/:id` - Update catalog product
- `DELETE /api/catalog-products/:id` - Delete catalog product

## Phase Management (Officer Chat)
Officers manage phases via natural language in the officer chat. The AI parses commands and emits `<phase_action>` XML blocks:
- **add**: Add new phase at specific position
- **modify**: Rename or update phase description/color
- **deactivate**: Soft-delete a phase (enterprise pattern: no hard deletes)
- **reactivate**: Bring back a deactivated phase
- **reorder**: Move a phase to a different position

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key for chat AI
- `SESSION_SECRET` - Session secret

## Conversation Status Flow
active -> reviewing -> qualified -> archived

## API Signature
`apiRequest(method, url, data)` — NOT `(url, options)`
