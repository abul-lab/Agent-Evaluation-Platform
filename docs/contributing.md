# Contributing to Agent Evaluation Platform (AEP)

Thank you for your interest in contributing to the Agent Evaluation Platform! We welcome contributions that maintain our high standards of architectural rigor, deterministic evaluation, and test discipline.

---

## 1. Code of Conduct

We expect all contributors to adhere to standard professional conduct:
- Maintain constructive, respectful communication.
- Focus on evidence-based software engineering and deterministic logic.
- Avoid introducing unvalidated claims or hype into documentation or code comments.

---

## 2. Pull Request & Quality Gates

Every pull request must pass the automated CI pipeline before review:

| Check | Tool | Command | Requirement |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Integration Tests** | `pytest` | `$env:PYTHONPATH="backend"; pytest backend/tests` | 100% pass rate, **≥ 85%** code coverage (enforced by `--cov-fail-under=85`). |
| **Backend Linting & Formatting** | `ruff` | `ruff check backend/app backend/tests` | 0 warnings or errors. |
| **Backend Type Safety** | `mypy` | `mypy backend/app` | Strict typing, 0 type errors. |
| **Frontend Tests** | `vitest` | `npm --prefix frontend test` | 100% pass rate. |
| **Frontend Linting** | `eslint` | `npm --prefix frontend run lint` | 0 warnings or errors. |
| **Frontend Type Safety** | `tsc` | `npm --prefix frontend run typecheck` | Strict compilation, 0 errors. |
| **Production Build** | `next build` | `npm --prefix frontend run build` | All static and dynamic pages compile cleanly. |

---

## 3. Development Workflow

1. **Fork & Branch**:
   ```bash
   git checkout -b feature/my-evaluation-rule
   ```
2. **Local Setup**:
   - Backend: Create virtual environment in `backend/`, install `requirements-dev.txt` (pinned test and lint tooling).
   - Frontend: Run `npm ci` in `frontend/`.
3. **Commit Messages**:
   Follow the [Conventional Commits](https://www.conventionalcommits.org/) standard:
   - `feat(evaluator): add token rate budget auditor`
   - `fix(graph): correct edge routing for cycle detection`
   - `docs(quickstart): clarify Docker deployment steps`
   - `test(contracts): add contract test for multi-agent traces`

---

## 4. Authoring New Deterministic Evaluators

All evaluators must:
1. Extend `app.evaluators.base.BaseEvaluator`.
2. Implement the `evaluate(trace: CanonicalTrace) -> list[EvaluationFinding]` method.
3. Be purely deterministic: calculate findings mathematically without invoking non-deterministic LLMs.
4. Provide structured `EvaluationFinding` objects with explicit `severity` (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `rule_name`, `message`, and `remediation`.
5. Include exhaustive unit tests in `backend/tests/evaluators/`.

---

## 5. Adding Golden Fixtures

Golden fixtures live in `fixtures/`:
1. Use valid JSON conforming strictly to `CanonicalTrace` Pydantic v2 schema.
2. Add a corresponding test contract in `backend/tests/fixtures/` verifying expected findings, scores, and risk classifications.
