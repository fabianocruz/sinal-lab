# CLAUDE.md — Code Review & Plan Mode

> **Keep this file concise.** Every line competes for attention in Claude's context window.
> Prune regularly. If removing a line wouldn't cause Claude to make mistakes, cut it.

---

## Project Status (Updated: 2026-02-21)

**Repository:** https://github.com/fabianocruz/sinal-lab
**Branch:** main (PR #14 merged)
**Test Coverage:** 88 Python tests + 63 frontend tests (Vitest)

### Completed:
- ✅ Initial project structure + GitHub repo
- ✅ API routers tested (7/7 = 100%, includes auth + waitlist)
- ✅ Editorial package tested (3/3 = 100%)
- ✅ Agent system documented and tested
- ✅ Newsletter SSR dinâmica (API → frontend com paginação)
- ✅ Seed expandido (20 newsletters, 5 agents, 5 meses)
- ✅ Logout + área do usuário (UserMenu dropdown + /conta)
- ✅ Waitlist-auth unificado (form auth-aware + upgrade waitlist→active)
- ✅ 63 testes frontend (UserMenu, AccountDetails, Navbar auth, WaitlistForm auth, ContaPage)

### Next Steps:
- Run tests before every commit: `pytest apps/ packages/ -v && pnpm test`
- Keep main branch stable (no direct commits except hotfixes)

---

## Engineering Preferences

IMPORTANT — Use these to guide every recommendation, review, and code change:

- **DRY is important** — flag repetition aggressively.
- **Well-tested code is non-negotiable.** I'd rather have too many tests than too few.
- **"Engineered enough"** — not under-engineered (fragile, hacky) and not over-engineered (premature abstraction, unnecessary complexity).
- **Handle more edge cases, not fewer.** Thoughtfulness > speed.
- **Explicit over clever.** Bias toward readability.
- **Readability over cleverness.** If it's hard to follow, simplify it.

---

## Plan Mode — Code Review Protocol

Review this plan thoroughly before making any code changes. For every issue or recommendation, explain the concrete tradeoffs, give me an opinionated recommendation, and ask for my input before assuming a direction.

### BEFORE YOU START

Ask if I want one of two options:

1. **BIG CHANGE:** Work through this interactively, one section at a time (Architecture → Code Quality → Tests → Performance) with at most 4 top issues in each section.
2. **SMALL CHANGE:** Work through interactively ONE question per review section.

### 1. Architecture Review

Evaluate:

- Overall system design and component boundaries
- Dependency graph and coupling concerns
- Data flow patterns and potential bottlenecks
- Scaling characteristics and single points of failure
- Security architecture (auth, data access, API boundaries)

### 2. Code Quality Review

Evaluate:

- Code organization and module structure
- DRY violations — be aggressive here
- Error handling patterns and missing edge cases (call these out explicitly)
- Technical debt hotspots
- Areas that are over-engineered or under-engineered relative to my preferences

### 3. Test Review

Evaluate:

- Test coverage gaps (unit, integration, e2e)
- Test quality and assertion strength
- Missing edge case coverage — be thorough
- Untested failure modes and error paths

### 4. Performance Review

Evaluate:

- N+1 queries and database access patterns
- Memory-usage concerns
- Caching opportunities
- Slow or high-complexity code paths

### For Each Issue Found

For every specific issue (bug, smell, design concern, or risk):

1. **Describe the problem concretely**, with file and line references.
2. **Present 2–3 options**, including "do nothing" where reasonable.
3. **For each option specify:** implementation effort, risk, impact on other code, and maintenance burden.
4. **Give your recommended option and why**, mapped to my preferences above.
5. **Then explicitly ask** whether I agree or want to choose a different direction before proceeding.

### Interaction Rules

- NUMBER all issues (e.g., Issue #1, Issue #2).
- Give LETTERS for options (e.g., A, B, C).
- When using AskUserQuestion, clearly label each option with the issue NUMBER and option LETTER so the user doesn't get confused.
- IMPORTANT: Make the recommended option always the 1st option.
- Do not assume my priorities on timeline or scale.
- After each section, pause and ask for my feedback before moving on.

---

## Workflow Standards

### Plan Before You Code

For anything beyond trivial changes:

1. **Explore** — read relevant files, understand context. Do NOT write code yet.
2. **Plan** — think hard about the approach. Propose a plan with tradeoffs. Use a scratchpad file (`PLAN.md`) for complex tasks.
3. **Implement** — only after I approve the plan. Verify correctness as you go.
4. **Test** — run tests. If tests fail, iterate until they pass.
5. **Commit** — write a descriptive commit message. Update docs if needed.

### Test-Driven Development (Preferred)

1. Write tests based on expected behavior — avoid mocks where possible.
2. Confirm tests fail (do NOT write implementation yet).
3. Commit the tests.
4. Write code that makes the tests pass — do NOT modify the tests.
5. Keep iterating until all tests pass.
6. Commit the implementation.

### Git Workflow

**Branch Strategy:**
- `main` — stable, deployable code only
- `feature/<name>` — new features (e.g., `feature/auth-system`)
- `fix/<name>` — bug fixes (e.g., `fix/api-validation`)
- `agent/<name>` — new AI agents (e.g., `agent/funding`)

**Rules:**
- ✅ Always create a new branch for each task
- ✅ Keep diffs small and focused (< 200 lines when possible)
- ✅ Write commit messages that explain *why*, not just *what*
- ✅ YOU MUST run tests before committing
- ❌ NEVER commit directly to main (except initial setup/hotfixes)

**Exception:** Direct commits to main were allowed during initial project setup (commits 1-5). From now on, all work MUST be done in feature branches with PR review.

**Workflow Example:**
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes, test, commit
pytest apps/ packages/ -v
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push -u origin feature/new-feature
gh pr create --title "Add new feature" --body "Description..."
```

---

## Quick Commands

### QPLAN
When I type "qplan", this means:
```
Analyze similar parts of the codebase and determine whether your plan:
- Is consistent with rest of codebase
- Introduces minimal changes
- Reuses existing code
Then present the plan for my review. Do NOT code yet.
```

### QCODE
When I type "qcode", this means:
```
Implement your plan. Run tests to make sure nothing is broken.
Run linter/formatter on newly created files.
Run type checking to ensure type safety.
```

### QCHECK
When I type "qcheck", this means:
```
You are a SKEPTICAL senior software engineer. For every MAJOR code change:
1. Check against the Engineering Preferences above.
2. Verify edge cases are handled.
3. Verify tests are sufficient.
4. Flag any DRY violations.
5. Flag any over/under-engineering.
```

### QTEST
When I type "qtest", this means:
```
Imagine you are a human tester of the feature you implemented.
Output a comprehensive list of scenarios to test, sorted by priority.
Include happy paths, edge cases, error states, and boundary conditions.
```

### QSTATUS
When I type "qstatus", this means:
```
Show current project status:
- Test coverage summary
- Uncommitted/unstaged changes
- Current branch and commits ahead/behind
- Pending TODOs or technical debt
```

---

## Project-Specific Commands

### Running Tests
```bash
# All tests
pytest apps/ packages/ -v

# Specific module
pytest apps/api/tests/ -v
pytest apps/agents/editorial/tests/ -v

# With coverage
pytest --cov=apps --cov=packages --cov-report=html
```

### Running Agents
```bash
# Dry run (preview only)
python scripts/run_agents.py sintese --dry-run --verbose

# Run and persist
python scripts/run_agents.py sintese --persist

# Run all agents
python scripts/run_agents.py all --persist
```

### Database Migrations
```bash
# Run migrations
alembic -c packages/database/alembic.ini upgrade head

# Create new migration
alembic -c packages/database/alembic.ini revision --autogenerate -m "description"
```

### Local Development
```bash
# Start PostgreSQL (Homebrew)
brew services start postgresql@16

# Start API server
uvicorn apps.api.main:app --reload --port 8000

# Start frontend
cd apps/web && pnpm dev
```

**Environment files:**
- `.env` (repo root) — database, API keys, backend config
- `apps/web/.env.local` — frontend-specific (AUTH_SECRET, NEXTAUTH_URL, NEXT_PUBLIC_*)
- Next.js only loads `.env` from its own directory (`apps/web/`), not from repo root

---

## Context Management

- Use `/clear` between distinct tasks to reset context.
- For complex multi-step work, use a scratchpad file (`PLAN.md` or `SCRATCHPAD.md`) as a checklist.
- For large tasks, break work into small, independently testable chunks.
- When context gets long, use subagents for distinct phases (e.g., one to implement, another to review).

---

## What NOT to Do

- NEVER modify test files to make tests pass — fix the implementation instead.
- NEVER commit directly to main/master (except initial setup or critical hotfixes).
- NEVER skip tests to save time.
- NEVER assume my priorities on timeline or scale — ask.
- NEVER proceed past a review section without my explicit approval.

---

## Test Coverage Standards

**Minimum Requirements:**
- Overall coverage: ≥ 80%
- API routers: 100% (all endpoints tested)
- Critical agents: 100% (collector, processor, scorer, synthesizer)
- Editorial pipeline: 100% (all layers tested)

**Current Status:**
- ✅ API routers: 7/7 = 100% (includes auth + waitlist)
- ✅ Editorial package: 3/3 = 100%
- ✅ Agent base framework: 100%
- ✅ Frontend components: 63 tests (Vitest + Testing Library)
- ✅ Overall: 88 Python + 63 frontend tests

**Before Committing:**
1. Run full test suite: `pytest apps/ packages/ -v`
2. Check coverage report if needed
3. Fix any failing tests before proceeding
