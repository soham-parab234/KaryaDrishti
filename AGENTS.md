# Project Instructions — LMIS Forecasting Engine

## 1. Project Goal
Build a working prototype for the SIH 2026 problem:
AI-Enabled Labour Market Intelligence and Skill Demand-Supply Forecasting Engine.

## 2. Source of Truth
- The Master R&D PDF is the primary source for requirements and research.
- The AI Handoff PDF is the implementation reference.
- Do not invent requirements, datasets, statistics, or research findings.
- Clearly label assumptions and synthetic/demo data.
- Never claim a government integration works unless it has been implemented and verified.

## 3. Technology Stack
- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Data processing: Pandas + NumPy
- Initial database: SQLite
- Target database: PostgreSQL
- Charts: Recharts
- Version control: Git + GitHub
- Testing: automated tests, ESLint, and Playwright where appropriate

## 4. Development Rules
- Inspect existing files before changing anything.
- Prefer simple, maintainable solutions over unnecessary complexity.
- Do not overwrite working code without understanding it.
- Do not install unnecessary dependencies.
- Never expose API keys, passwords, tokens, or personal data.
- Keep frontend and backend responsibilities separate.
- Validate inputs and handle errors.
- Add tests for important calculations and business logic.
- Explain important architectural decisions in documentation.

## 5. Collaboration Rules
- GitHub is the source of truth for project code.
- Read this file before starting a task.
- Make focused changes and explain which files changed.
- Do not let multiple AI agents edit the same files simultaneously.
- Never commit or push changes without the user's approval.
- Never delete project data or perform destructive operations without approval.

## 6. Product Integrity
The prototype should support the requirements established by the source documents.
Potential capabilities include data imports, occupation mapping, demand-supply gap analysis, forecasting, alerts, training scenarios, and report exports. Confirm each against the source documents before implementation.

## 7. Working Style
- Work in small, verifiable steps.
- Explain commands before asking the user to run them.
- Do not assume the user has advanced programming knowledge.
- Report limitations honestly.
- Do not mark a feature complete until it has been tested.