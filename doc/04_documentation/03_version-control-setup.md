# Version Control Setup

**Document ID:** VCS-001
**Version:** 1.0
**Phase:** 0.3
**Status:** Draft
**Last Updated:** February 2026

---

## 1. Purpose and Scope

This document establishes the complete version control infrastructure for the AI-Driven Agentic System for Loan Prequalification and Financial Advisory. The version control system is the backbone of collaborative development, enabling multiple agents and team members to work concurrently while maintaining code integrity and historical traceability. Every line of code, every configuration change, and every document in this project flows through the version control system.

The version control setup described herein implements a trunk-based development approach optimized for multiagent parallel development. The strategy balances the need for rapid iteration with the requirement for code stability in a financial system subject to regulatory oversight. The branching model, protection rules, and commit conventions are specifically designed to support the Multiagent Antigravity IDE workflow, where multiple specialized agents work simultaneously on different components of the system.

This document covers the Git repository structure, branching strategy, branch protection configuration, commit conventions, and integration with the issue tracking system. The setup assumes Git as the version control system and GitHub as the hosting platform, though the principles apply equally to GitLab, Bitbucket, or other Git hosting services.

---

## 2. Repository Structure

### 2.1 Directory Layout

The repository follows a modular structure that maps to the agent topology defined in the ontology. Each agent has a dedicated directory containing its source code, tests, and configuration. Shared resources reside in common directories accessible to all agents.

```
/
├── .github/
│   ├── workflows/          # GitHub Actions CI/CD pipelines
│   └── ISSUE_TEMPLATE/    # Issue templates
├── .gitignore             # Global gitignore rules
├── .editorconfig          # Editor configuration
├── LICENSE                # Project license
├── README.md              # Project overview
├── Makefile               # Build automation
├── docker-compose.yml     # Local development environment
├── src/
│   ├── agents/
│   │   ├── journey_coach/       # Journey Coach Agent
│   │   ├── data_synthesizer/    # Data Synthesizer Agent
│   │   │   └── scdg/            # Synthetic Credit Data Generator
│   │   ├── risk_engine/         # Risk Engine Agent
│   │   ├── advisory/            # Advisory Agent
│   │   └── compliance/          # Compliance Guardrail Agent
│   ├── shared/                  # Shared libraries
│   │   ├── models/              # Data models
│   │   ├── utils/               # Utility functions
│   │   └── config/              # Configuration management
│   └── orchestration/            # Orchestration layer
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                    # End-to-end tests
├── docs/                        # Project documentation
│   ├── architecture/            # Architecture decisions
│   ├── api/                    # API documentation
│   └── user/                    # User guides
├── infrastructure/
│   ├── docker/                  # Docker configurations
│   ├── kubernetes/               # K8s manifests (future)
│   └── terraform/               # IaC configurations (future)
└── scripts/
    ├── setup/                   # Setup scripts
    ├── migration/               # Database migrations
    └── utility/                 # Utility scripts
```

### 2.2 Directory Purposes

The source directory contains all application code organized by agent. Each agent directory follows a consistent internal structure with subdirectories for source code, tests, configuration, and documentation. This consistency enables agents to understand each other's code organization and simplifies navigation.

The tests directory follows the same agent-based organization as the source directory. Unit tests reside in the same directory as the code they test, following the convention of test files adjacent to implementation files. Integration tests and end-to-end tests are organized by workflow rather than by agent.

The docs directory contains all project documentation. The architecture subdirectory holds Architectural Decision Records (ADRs), technical specifications, and design documents. The api subdirectory contains API documentation, typically generated from OpenAPI specifications. The user subdirectory contains user guides and operational runbooks.

The infrastructure directory contains all infrastructure-as-code configurations. Docker configurations for local development are in the docker subdirectory. Kubernetes manifests for future production deployment are in the kubernetes subdirectory. Terraform configurations for cloud infrastructure are in the terraform subdirectory.

---

## 3. Branching Strategy

### 3.1 Branch Types

The branching strategy defines four primary branch types, each with a specific purpose and lifetime.

The main branch represents the production-ready state of the codebase. Only thoroughly tested and reviewed code enters main. The main branch is protected and can only be updated through pull requests that pass all quality gates. Every commit on main must be tagged with a semantic version number for release tracking.

Feature branches implement new functionality or make improvements to existing features. These branches branch off from main and merge back into main through pull requests. Feature branches should live for no more than two to three days to minimize integration friction. Branch naming follows the pattern: `feature/component-description` or `feat/agent-name-description`.

Bugfix branches address defects in the codebase. They follow the same lifecycle as feature branches but use the prefix `bugfix/`. The naming pattern is `bugfix/issue-description` or `fix/agent-name-issue-description`.

Hotfix branches address urgent production issues that cannot wait for the normal release cycle. These branches branch off from main and merge back into main with expedited review. Branch naming follows the pattern: `hotfix/issue-description`.

Milestone branches provide stable integration points for major phases or releases. These branches are created from main and serve as the basis for feature branches during a development period. Branch naming follows the pattern: `phase-N-description` or `release-X.Y`.

### 3.2 Agent-Specific Prefixes

To support Multiagent Antigravity IDE operations, each agent is assigned a specific branch prefix that enables automatic identification of which agent is responsible for which changes. This prefix appears in branch names after the type prefix.

| Agent | Branch Prefix | Example |
|-------|---------------|---------|
| Journey Coach | journeycoach/ | feat/journeycoach/conversation-state-management |
| Data Synthesizer | datasynth/ | feat/datasynth/scdg-markov-generator |
| Risk Engine | riskengine/ | feat/riskengine/feature-pipeline |
| Advisory | advisory/ | feat/advisory/rag-integration |
| Compliance | compliance/ | feat/compliance/fair-lending-rules |
| Shared/Config | shared/ | feat/shared/data-models-v2 |
| Infrastructure | infra/ | infra/docker-compose-optimization |

The agent prefix enables several capabilities. First, it creates an automatic audit trail of which agent made which changes. Second, it enables filtering branch lists by agent for focused reviews. Third, it supports automated workflows that apply agent-specific rules or notifications.

### 3.3 Branch Lifecycle

The lifecycle of a typical feature branch follows a structured process designed to maintain code quality while enabling rapid iteration.

The creation phase begins with the developer or agent identifying the work package from the WBS that needs implementation. The developer creates a branch from the current main branch using the appropriate naming convention. The branch is created with an initial commit that includes the work package reference in the commit message.

The development phase involves the developer implementing the required functionality while following the project's coding standards. Commits are made frequently with descriptive messages that reference the work package and explain the change. The developer runs local tests to validate changes before pushing.

The review phase begins when the developer pushes the branch and creates a pull request. The pull request description includes the work package ID, a summary of changes, and any testing performed. Code owners and relevant agents are notified for review.

The merge phase occurs after all reviews are complete and all CI checks pass. The branch is merged into main using a squash merge to maintain a linear history. The branch is deleted after merge to keep the repository clean.

---

## 4. Commit Conventions

### 4.1 Commit Message Format

All commit messages follow a structured format that enables automatic parsing and cross-referencing with the issue tracking system. The format consists of three parts: a type prefix, a scope identifier, and a description.

The type prefix indicates the category of change. Common types include `feat` for new features, `fix` for bug fixes, `docs` for documentation changes, `style` for code formatting changes that do not affect functionality, `refactor` for code changes that neither fix bugs nor add features, `test` for adding or updating tests, `chore` for maintenance tasks, and `ci` for CI/CD configuration changes.

The scope identifier indicates the agent, component, or module affected by the change. The scope uses the same identifiers defined in the agent-specific prefixes. Examples include `journeycoach`, `datasynth`, `riskengine`, `advisory`, `compliance`, and `shared`.

The description is a short, imperative statement of what the change does. The description should complete the sentence "This commit will..." and should be no more than 72 characters.

Examples of properly formatted commit messages include:

```
feat(datasynth): implement Markov chain payment history generator
fix(riskengine): correct feature normalization for zero-balance accounts
docs(api): document risk assessment response schema
refactor(shared): extract common validation logic to shared module
test(advisory): add integration tests for RAG retrieval
ci: add automated security scanning to pipeline
```

### 4.2 Work Package References

Every commit must reference the work package it implements using the format `[WP-XXX]` where XXX is the JIRA ticket number. This reference creates a bidirectional link between code changes and project management items.

The work package reference appears at the beginning of the commit message body, after a blank line from the short description. For commits that implement a single work package, the reference is mandatory. For commits that span multiple work packages, the primary reference appears first, followed by additional references.

Example commit with work package reference:

```
feat(journeycoach): implement session state persistence

[WP-147] Add Redis-based session storage for conversation context
- Store session data with 24-hour TTL
- Implement session recovery on agent restart
- Add session metrics for monitoring
```

### 4.3 Automated Validation

The CI pipeline includes automated validation of commit message format. Commits that do not follow the convention fail the pipeline with a clear error message explaining the required format. This validation ensures consistency across all contributors, whether human or agent.

---

## 5. Branch Protection Rules

### 5.1 Main Branch Protection

The main branch has strict protection rules that ensure only reviewed, tested code enters the production-ready state.

Require pull request reviews before merging is enabled with the following configuration. At least one code owner must approve the pull request. For changes affecting the Risk Engine or Compliance components, a second approval from a domain expert is required. For changes to infrastructure or security-related components, security team approval is required.

Require status checks to pass before merging is enabled with the following requirements. All CI pipeline stages must complete successfully. The build must not have any pending or failed checks. The branch must be up to date with main (no merge conflicts).

Require conversation resolution is enabled. All pull request comments must be resolved before merging is permitted.

Include administrators in these protection rules is disabled. Even repository administrators must follow the same review and check requirements as other contributors.

### 5.2 Milestone Branch Protection

Milestone branches have modified protection rules that reflect their role as integration points.

Require pull request reviews before merging is enabled with at least one approval required. For milestone branches in active development, automated merging is permitted when all checks pass and at least one owner approves.

Require status checks to pass is enabled with the same requirements as main.

Milestone branches may be protected differently depending on their state. Active development branches may allow force pushes for rebasing. Stable milestone branches (those representing released versions) may have full protection like main.

### 5.3 Branch Deletion Policy

The repository enforces automatic branch deletion after merge. When a pull request is merged (or closed), the source branch is automatically deleted. This policy keeps the branch list clean and prevents confusion from stale branches.

Administrators can restore deleted branches from the Git UI if needed, so accidental deletions are recoverable.

---

## 6. GitHub Actions CI/CD Integration

### 6.1 Pipeline Overview

The CI/CD pipeline automatically validates all changes that enter the repository through pull requests. The pipeline runs on every push to any branch and on every pull request. Successful pipeline execution is required for branch protection rules to pass.

The pipeline consists of five stages that execute sequentially. The first stage is Code Quality, which runs linting and static analysis. The second stage is Security Scanning, which checks for vulnerabilities and secrets. The third stage is Unit Tests, which executes the test suite with coverage reporting. The fourth stage is Integration Tests, which validates component interactions. The fifth stage is Build, which creates Docker images and other artifacts.

### 6.2 Workflow Configuration

The pipeline is defined in `.github/workflows/ci.yml` and includes the following key configurations.

The trigger configuration specifies that the workflow runs on push to any branch and on pull requests targeting main or milestone branches. The workflow also runs on a schedule (nightly builds) and can be triggered manually.

The job configuration defines parallel execution where possible. The code quality and security scanning jobs run in parallel since they analyze the same code but perform different checks. The test jobs depend on the quality jobs passing. The build job depends on all test jobs passing.

The matrix strategy enables testing against multiple Python versions and operating systems. The default configuration tests against Python 3.11 on Ubuntu, with optional testing on Python 3.10 and macOS.

### 6.3 Environment-Specific Workflows

Additional workflow files handle other GitHub Actions use cases.

The `pull-request.yml` workflow runs on every pull request and provides rapid feedback. This workflow is optimized for speed, running only essential checks.

The `nightly.yml` workflow runs on a schedule and includes extended testing. This workflow runs the full test suite, performs security scanning with extended rules, and builds all artifacts.

The `release.yml` workflow handles semantic versioning and release creation. This workflow runs only on tagged commits and includes additional validation steps required for releases.

---

## 7. Issue Tracking Integration

### 7.1 Work Package Linking

The version control system is integrated with the issue tracking system through structured references in commit messages and pull requests.

When a branch is created for a work package, the branch name includes the work package ID. This creates an initial link between the branch and the ticket.

When commits are made, the commit message includes the work package ID in the `[WP-XXX]` format. This links each commit to the relevant ticket.

When a pull request is created, the description includes the work package ID and the ticket is automatically updated to show the PR link.

When the PR is merged, the ticket is automatically transitioned to the "Done" or "Closed" state based on the automation rules.

### 7.2 Automation Rules

The following automation rules connect version control activities to issue tracking state.

On branch creation from a ticket, the ticket is moved to "In Progress" status.

On first commit to the branch, the ticket is assigned to the developer or agent who made the commit.

On pull request creation, the ticket is tagged with "In Review" label.

On pull request merge, the ticket is moved to "Done" status with a comment linking to the merge commit.

On pull request close without merge, the ticket is moved back to "To Do" status with a comment explaining the closure.

---

## 8. Repository Settings Configuration

### 8.1 Required Settings

The following repository settings must be configured for proper operation.

The default branch is set to "main". All new branches are created from main by default.

The allow squash merging is enabled. This ensures a linear commit history on main while allowing contributors to maintain clean feature branch histories.

The allow rebase merging is enabled for feature branches that need to be rebased rather than merged.

The allow auto-merge is enabled for automated merging when all requirements are met.

The automatically delete head branches is enabled to maintain a clean branch list.

### 8.2 Security Settings

The following security settings protect the repository and its contents.

The require 2FA for organization members setting should be enabled at the organization level.

The security and analysis settings should include dependency scanning, secret scanning, and code scanning enabled.

The push protection settings should block commits containing secrets from being pushed directly to main.

---

## 9. Setup Checklist

The following checklist summarizes all configuration steps required to establish the version control system.

- [ ] Create GitHub repository with appropriate visibility (private for production)
- [ ] Clone repository to local development environment
- [ ] Create initial directory structure as specified in Section 2
- [ ] Configure .gitignore for Python, Node, and IDE files
- [ ] Configure .editorconfig for consistent formatting
- [ ] Create GitHub Actions workflow files
- [ ] Create initial commit with project structure
- [ ] Configure main branch protection rules
- [ ] Configure milestone branch protection rules
- [ ] Set up branch auto-deletion policy
- [ ] Configure repository settings as specified in Section 8
- [ ] Test CI pipeline with initial commit
- [ ] Document repository URL and access instructions

---

## 10. Common Operations

### 10.1 Starting New Work

To start implementing a new work package, follow this procedure.

First, ensure your local main branch is current: `git checkout main && git pull origin main`.

Second, create a new branch with the appropriate prefix: `git checkout -b feat/datasynth/markov-generator`.

Third, make initial commit referencing the work package: `git commit -m "feat(datasynth): initial commit for Markov chain generator\n\n[WP-152]"`.

Fourth, push and create upstream branch: `git push -u origin feat/datasynth/markov-generator`.

### 10.2 Submitting Changes

To submit completed work for review, follow this procedure.

First, ensure all tests pass locally: `make test`.

Second, push all commits: `git push origin feat/datasynth/markov-generator`.

Third, Create pull request through GitHub UI or CLI with description including work package ID and summary of changes.

Fourth, Address review comments and push updates.

Fifth, Once approved and checks pass, merge the pull request.

### 10.3 Syncing Main Changes

To keep your branch synchronized with main, follow this procedure.

First, fetch latest changes: `git fetch origin`.

Second, Rebase onto main: `git rebase origin/main`.

Third, Resolve any conflicts and commit the resolution.

Fourth, Force push to update your branch: `git push --force-with-lease`.

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | February 2026 | Lead AI Architect | Initial version |

**Cross-References**

- Master Plan Checklist: Section 0.3
- Project Ontology Definition: ONT-001
- Work Breakdown Structure: WBS-001
- Issue Tracking Setup: ONT-004 (future)
