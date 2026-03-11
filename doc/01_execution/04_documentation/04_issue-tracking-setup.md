# Issue Tracking Setup

**Document ID:** JIRA-001
**Version:** 1.0
**Phase:** 0.4
**Status:** Draft
**Last Updated:** February 2026

---

## 1. Purpose and Scope

This document establishes the complete issue tracking infrastructure for the AI-Driven Agentic System for Loan Prequalification and Financial Advisory. The issue tracking system serves as the single source of truth for all work items, enabling precise tracking of progress, clear assignment of responsibilities, and comprehensive traceability from requirements through implementation to validation. In a multiagent development environment where multiple specialized agents operate concurrently, the issue tracking system provides the coordination mechanism that prevents conflicts, identifies dependencies, and maintains coherent project context.

The issue tracking setup described herein is designed around JIRA, the industry-standard project management platform. However, the principles and configurations described can be adapted to other platforms such as Linear, Azure DevOps, or GitHub Projects. The configuration emphasizes the unique requirements of multiagent development, where work items must be precisely defined to enable parallel execution without conflicts, and where the relationship between work items and code artifacts must be explicitly maintained.

This document covers project configuration, issue types and workflows, custom fields and templates, automation rules, priority and escalation frameworks, and integration with the version control system. The goal is a complete issue tracking infrastructure that supports professional project management while enabling the full capabilities of Multiagent Antigravity IDE.

---

## 2. Project Configuration

### 2.1 Project Setup

The JIRA project represents the complete loan prequalification system development effort. The project is configured with the following basic settings.

The project key is LOANPA, standing for Loan Prequalification Advisory. This key appears in all issue identifiers, creating a unique namespace for the project. The project name is Loan Prequalification System, providing a clear display name in all JIRA interfaces. The project type is Software, enabling the full range of agile boards and sprint planning tools. The lead is set to the project manager or technical lead responsible for overall delivery.

The project URL points to the GitHub repository where all code is stored. This link connects the project management view to the version control system, enabling direct navigation from issues to code and vice versa.

### 2.2 Project Structure

The project is organized into a hierarchical structure that mirrors the Work Breakdown Structure defined in the project documentation. This hierarchy enables both high-level portfolio views and detailed work management.

The top level contains the project itself, representing the complete development effort. Below the project level are Program Increments, which group work by major delivery phases. Each Program Increment corresponds to one of the six project phases: Phase 0 Foundation, Phase 1 Open Core, Phase 2 Predictive Enhancement, Phase 3 External Data, Phase 4 Cloud LLM, and Phase 5 Full Ecosystem.

Within each Program Increment are Features, which represent the major capabilities delivered at that level. For example, Phase 1 Open Core contains features for each agent: Journey Coach, Data Synthesizer, Risk Engine, Advisory, and Compliance. Each Feature contains the Stories and Tasks that implement specific capabilities.

### 2.3 Access Control

The project access control is configured to support both human team members and automated agents.

Project administrators have full access to all project settings, including configuration changes, permission modifications, and data management. This role is limited to the core project leadership team.

Developers have access to create, edit, and assign issues within their agent domain. They can update issues they are assigned to and comment on all issues. This role supports both human developers and the Multiagent Antigravity IDE agents.

Stakeholders have read-only access to the project, enabling them to view progress, review documentation, and comment on issues. This role supports business sponsors, compliance officers, and other non-development team members who need visibility into project status.

---

## 3. Issue Types

### 3.1 Core Issue Types

The project uses five core issue types, each with a specific purpose in the project management workflow.

Epic represents a large body of work that can be broken down into smaller stories. Epics correspond to major capabilities or phases in the project. An Epic has a longer lifespan than other issue types, typically spanning multiple sprints. The Epic issue type is used for Program Increments and major Features.

Story represents a user-facing capability or feature that delivers value to an end user. Stories follow the INVEST criteria: Independent, Negotiable, Valuable, Estimable, Small, and Testable. The Story issue type is used for most development work items.

Task represents a technical activity that does not directly deliver user value in itself but is necessary to complete a Story. Tasks are typically used for research, infrastructure setup, or non-functional work. A Story may contain multiple Tasks.

Bug represents a defect in the system that requires correction. Bugs are categorized by severity and priority, with critical bugs receiving expedited handling.

Subtask represents a component of work that is part of a larger Story or Task. Subtasks enable breaking down complex work into smaller, trackable units.

### 3.2 Issue Type Schemes

A custom issue type scheme maps issue types to the project. The scheme assigns each issue type to the appropriate category and enables or disables creation of each type based on project needs.

The default scheme includes Epic, Story, Task, Bug, and Subtask. Epics can be created at the project level and within Program Increments. Stories can be created within Features. Tasks can be created within Stories. Bugs can be created at any level. Subtasks can be created within any parent issue.

### 3.3 Issue Type Workflows

Each issue type has an associated workflow that defines the valid statuses and transitions. The workflows are designed to support agile development while maintaining appropriate controls.

The Story workflow includes the statuses To Do, In Progress, In Review, Done, and Removed. The transitions follow standard agile practice: To Do moves to In Progress when work begins, In Progress moves to In Review when implementation is complete, In Review moves to Done when accepted, and any status can move to Removed if the story is cancelled.

The Task workflow mirrors the Story workflow but includes an additional status, Blocked, that indicates the task cannot proceed due to a dependency or external constraint.

The Bug workflow includes the statuses Open, In Progress, In Review, Verified, and Closed. An additional transition path goes from Verified back to In Progress if regression testing reveals the fix was incomplete.

---

## 4. Custom Fields

### 4.1 Required Fields

Custom fields capture information specific to the project's needs beyond the standard JIRA fields. The following custom fields are required for all issues.

The Agent Assignment field identifies which of the five agents is responsible for implementing this work item. The field uses a dropdown with options: Journey Coach, Data Synthesizer, Risk Engine, Advisory, Compliance, Shared, Infrastructure, or Unassigned. This field enables filtering and reporting by agent, essential for multiagent coordination.

The Work Package ID field links each issue to the Work Breakdown Structure. The field uses a text field with format WP-XXX, where XXX is the WBS item number. This field enables traceability from project management to code artifacts.

The Story Points field captures the effort estimate for the issue. The field uses a number field with values from the Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21, 34. This field enables velocity tracking and capacity planning.

The Priority Matrix field classifies the issue's priority based on both urgency and impact. The field uses a dropdown with options: Critical, High, Medium, and Low. This field is distinct from JIRA's native Priority field and provides business-level prioritization.

### 4.2 Conditional Fields

Certain fields appear only for specific issue types or statuses.

The Blocked By field appears for issues with status Blocked. This field links to the issue causing the blockage, creating a dependency chain that can be analyzed to identify critical path impacts.

The Sprint field appears for issues assigned to Sprints. This field enables sprint planning and burndown tracking.

The Risk Score field appears for Epic and Feature issues. This field captures a numerical assessment of delivery risk using a scale of 1-100.

### 4.3 Field Configuration

The field configuration defines which fields are required, optional, or hidden for each issue type and workflow state.

For Story issues, the Agent Assignment, Work Package ID, and Story Points fields are required. The Description field supports Jira Markdown formatting. The Acceptance Criteria field uses a table format with Given-When-Then scenarios.

For Task issues, the Agent Assignment and Work Package ID fields are required. Story Points are optional for Tasks.

For Bug issues, the Severity field (Critical, Major, Minor, Cosmetic) is required. Steps to Reproduce uses a repeatable fieldset that includes Step Number, Action, Expected Result, and Actual Result.

---

## 5. Ticket Templates

### 5.1 Story Template

Stories follow a structured template that ensures consistent information capture. The template is automatically applied when creating new Story issues.

```
h3. Summary
[Agent]: [Short description of the capability]

h3. User Story
As a [user type], I want [goal] so that [benefit].

h3. Acceptance Criteria
* [ ] Criterion 1
* [ ] Criterion 2
* [ ] Criterion 3

h3. Technical Notes
* Implementation approach
* Dependencies
* Architecture considerations

h3. Links
* Related Epics: [Epic links]
* Related Stories: [Story links]
* Documentation: [Doc links]

h3. Estimation
Story Points: [number]
Original Estimate: [hours]
Remaining Estimate: [hours]
```

### 5.2 Task Template

Tasks follow a simplified template focused on technical implementation details.

```
h3. Summary
[Agent]: [Short description of the task]

h3. Description
[Detailed description of what needs to be done]

h3. Technical Details
* Component: [Which component]
* Approach: [How to implement]
* Testing: [How to verify]

h3. Dependencies
* Blocked by: [Links]
* Blocks: [Links]

h3. Time Tracking
Original Estimate: [hours]
Time Spent: [hours]
Remaining: [hours]
```

### 5.3 Bug Template

Bugs follow a template focused on reproduction and verification.

```
h3. Summary
[Brief description of the bug]

h3. Environment
* Browser/Platform: [Details]
* Version: [System version]
* Date Observed: [Date]

h3. Steps to Reproduce
# Step 1
# Step 2
# Step 3

h3. Expected Behavior
[What should happen]

h3. Actual Behavior
[What actually happens]

h3. Root Cause
[Analysis of the bug cause]

h3. Fix Details
* File: [Path]
* Line: [Number]
* Solution: [Description]

h3. Testing
* [ ] Verified fix in development
* [ ] Added regression test
* [ ] Verified in staging
```

### 5.4 Epic Template

Epics follow a template focused on scope and roadmap planning.

```
h3. Summary
[High-level description of the epic]

h3. Goal
[What this epic aims to achieve]

h3. Scope
h4. In Scope
* [Item 1]
* [Item 2]

h4. Out of Scope
* [Item 1]
* [Item 2]

h3. Milestones
* Milestone 1: [Description] - [Target Date]
* Milestone 2: [Description] - [Target Date]

h3. Dependencies
* [Dependency 1]
* [Dependency 2]

h3. Risks
* [Risk 1] - Mitigation: [Description]
* [Risk 2] - Mitigation: [Description]

h3. Success Criteria
* [ ] Criterion 1
* [ ] Criterion 2
```

---

## 6. Workflow Automation

### 6.1 Status Transition Rules

Automation rules manage issue state transitions based on events in the version control system and other integrated tools. The following rules are configured.

On branch creation from an issue, the automation transitions the issue from To Do to In Progress and assigns the issue to the creator. The rule triggers on webhook events from GitHub indicating a new branch with the issue key in the branch name.

On pull request creation, the automation adds the In Review label to the issue. The rule triggers on webhook events from GitHub indicating a new pull request with the issue key in the title or description.

On pull request merge, the automation transitions the issue to Done and adds the Completed label. The rule triggers on webhook events from GitHub indicating a merge to main with the issue key. The automation also logs the commit hash and pull request number for traceability.

On pull request close without merge, the automation transitions the issue back to To Do and adds the Abandoned label with a comment explaining the closure. This handles cases where work is abandoned or deferred.

### 6.2 Notification Rules

Automation rules manage notifications to keep stakeholders informed and to drive action.

On issue assignment, the automation sends an email notification to the assignee. For issues assigned to an agent (Multiagent Antigravity IDE), the notification is posted to a dedicated Slack channel or webhook endpoint that the agent monitors.

On issue escalation, the automation escalates issues that have been in the same status for more than three days. The rule sends a reminder to the assignee and notifies the project lead.

On blocked issue detection, the automation monitors issues with Blocked status. If an issue remains blocked for more than two days, the rule escalates to the project lead and creates a dependency analysis task.

### 6.3 SLA Rules

Service Level Agreement rules ensure timely handling of issues based on priority.

Critical priority issues have a response time of four hours and a resolution target of one business day. High priority issues have a response time of one business day and a resolution target of three business days. Medium priority issues have a response time of one week and a resolution target of two weeks. Low priority issues have no specific SLA but are addressed as capacity allows.

The SLA tracking is implemented using JIRA's built-in SLA management, with dashboards showing compliance metrics.

---

## 7. Boards and Views

### 7.1 Kanban Board

The primary project board is a Kanban board that provides visual workflow management. The board has columns matching the workflow statuses: To Do, In Progress, In Review, and Done.

The board includes swimlanes by Agent, enabling a view of each agent's current workload. This is essential for multiagent coordination, allowing the orchestration layer to understand capacity and balance work distribution.

The board includes quick filters for Priority, Sprint, and Epic. Users can save filtered views for common queries, such as viewing all Critical issues across all agents.

WIP limits are configured for each column to prevent overloading. The In Progress column has a limit of 10 issues per agent. The In Review column has a limit of 5 issues per agent.

### 7.2 Sprint Board

A Sprint board supports the two-week sprint cycle used for iteration planning. The board includes all issues committed to the current sprint, organized by assignee within status columns.

The sprint board includes burndown chart gadget showing progress toward sprint completion. The board also includes a velocity chart gadget showing historical velocity for capacity planning.

The sprint backlog view shows all issues in the current sprint with their story point totals. This enables the product owner to make informed decisions about scope tradeoffs.

### 7.3 Portfolio Views

Portfolio-level views provide visibility across all phases and agents. The Epic Roadmap view shows all epics with their planned timelines, enabling dependency identification and risk assessment. The Release Burnup view shows progress toward major releases, providing stakeholders with delivery confidence metrics.

---

## 8. Reporting and Dashboards

### 8.1 Project Dashboard

The project dashboard provides at-a-glance visibility into project health. The dashboard includes the following gadgets.

The Sprint Burndown gadget shows the current sprint progress with ideal versus actual burndown lines. The gadget includes forecasting of sprint completion based on current velocity.

The Team Velocity gadget shows story points completed per sprint over the last six sprints. The gadget includes a trend line showing velocity trajectory.

The Issue Status Distribution gadget shows a pie chart of issues by status, enabling quick assessment of work in progress versus completed.

The Blocked Issues gadget lists all issues currently in Blocked status, enabling immediate visibility into impediments.

The Agent Workload gadget shows a bar chart of issues per agent, enabling balanced workload distribution.

### 8.2 Agent-Specific Reports

Each agent has dedicated reports showing workload, progress, and blockers specific to that agent's domain.

The Agent Delivery Report shows story points completed, average cycle time, and defect rate per agent. This report enables assessment of agent performance and identification of improvement opportunities.

The Agent Backlog Health shows the age distribution of backlog items per agent. Items aging beyond thresholds are flagged for attention.

### 8.3 Executive Summary

An executive summary report provides high-level metrics for stakeholders who do not need detailed project visibility. The report includes overall progress percentage, milestone status, key risks and issues, and upcoming milestones.

---

## 9. Integration Configuration

### 9.1 GitHub Integration

The JIRA integration with GitHub is configured to enable bidirectional linking between issues and code artifacts.

The integration maps JIRA issue keys to GitHub branches, commits, and pull requests. When a branch is created with a JIRA key in the name, JIRA automatically links the branch to the issue. When a commit includes a JIRA key in the message, JIRA automatically links the commit to the issue. When a pull request references a JIRA key, JIRA automatically links the pull request and shows the PR status on the issue.

The integration includes webhook configuration for real-time synchronization. Webhooks are configured for push events, pull request events, and branch events.

### 9.2 Slack Integration

The Slack integration enables notifications and alerts to reach team members through their preferred communication channel.

Channel mapping directs notifications to appropriate channels based on agent assignment. Journey Coach-related issues post to #loans-journeycoach. Data Synthesizer issues post to #loans-datasynth. Risk Engine issues post to #loans-riskengine. Advisory issues post to #loans-advisory. Compliance issues post to #loans-compliance.

Notification rules trigger messages for issue assignment, status changes, and escalations. Critical and high-priority issues trigger immediate notifications. Medium and low-priority issues are batched into daily digests.

### 9.3 Documentation Integration

The integration with the project documentation system enables traceability from issues to design documents and technical specifications.

When an Epic is created, the automation creates a corresponding folder in the project documentation repository. When a Story is completed, the automation prompts for documentation updates. When a Bug is fixed, the automation links to the regression test that verified the fix.

---

## 10. Setup Checklist

The following checklist summarizes all configuration steps required to establish the issue tracking system.

- [ ] Create JIRA project with key LOANPA
- [ ] Configure project structure with Program Increments
- [ ] Set up user roles and permissions
- [ ] Configure issue type scheme with five core types
- [ ] Create custom workflows for each issue type
- [ ] Add custom fields: Agent Assignment, Work Package ID, Priority Matrix
- [ ] Configure field configuration schemes
- [ ] Create issue templates for Story, Task, Bug, Epic
- [ ] Set up automation rules for status transitions
- [ ] Configure notification rules
- [ ] Configure SLA rules and metrics
- [ ] Create Kanban board with agent swimlanes
- [ ] Create Sprint board with burndown
- [ ] Set up portfolio views
- [ ] Configure project dashboard
- [ ] Create agent-specific reports
- [ ] Integrate with GitHub
- [ ] Integrate with Slack
- [ ] Test end-to-end workflow
- [ ] Train team on usage

---

## 11. Usage Guidelines

### 11.1 Creating Issues

When creating a new issue, follow these guidelines.

First, identify the correct issue type. Use Story for deliverable features. Use Task for technical work that does not directly deliver user value. Use Bug for defects. Use Epic for large bodies of work.

Second, complete all required fields. The Agent Assignment field must be set to identify the responsible agent. The Work Package ID field must be set for traceability. Story Points must be estimated for Stories.

Third, write clear, concise summaries. The summary should complete the sentence "As a user, I want..." for Stories. For Tasks and Bugs, the summary should clearly describe what needs to be done or what is broken.

Fourth, provide sufficient detail in the description. Use the template appropriate for the issue type. Include acceptance criteria that define when the work is complete.

### 11.2 Updating Issues

When updating an issue, follow these guidelines.

First, keep the status current. Update the status as work progresses through the workflow. Stale statuses mislead the team about true progress.

Second, log time spent. Accurate time tracking enables better estimation for future work. Use the Time Tracking field to record hours worked.

Third, add comments for context. Explain decisions, record discussions, and note any information that would help future maintainers.

Fourth, link related issues. Use the Linked Issues field to connect dependent items. This creates the dependency graph that enables critical path analysis.

### 11.3 Sprint Planning

During sprint planning, follow these guidelines.

First, review the backlog. Identify Stories that are ready for commitment based on clear acceptance criteria and accurate estimates.

Second, consider capacity. Review each assignee's current workload before committing new work. Account for meetings, holidays, and other commitments.

Third, set sprint goals. Define what the team intends to accomplish in the sprint. Goals provide focus and enable measuring sprint success.

Fourth, break down complex Stories. If a Story is too large to complete in a sprint, break it into smaller Stories that can be delivered incrementally.

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | February 2026 | Lead AI Architect | Initial version |

**Cross-References**

- Master Plan Checklist: Section 0.4
- Project Ontology Definition: ONT-001
- Work Breakdown Structure: WBS-001
- Version Control Setup: VCS-001
