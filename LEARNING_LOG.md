# Learning Log

Interview-prep notes: one entry per chunk, with concepts, my answers to the check questions, and what I struggled with.

---

## M1 · Chunk 1.1: Repo + tooling

**Concepts**
- **Lockfile (`uv.lock`)**: pins the exact version of every dependency, including transitive ones, so eval numbers are reproducible later.
- **src/ layout**: tests import the *installed* package, which catches packaging mistakes a flat layout hides.
- **Typed config (pydantic-settings)**: one source of truth for knobs; bad values fail at startup, not deep inside a run. Precedence: kwargs > env > .env > YAML > defaults.
- **Secrets**: `.env` (gitignored) + `.env.example` (committed template); `SecretStr` keeps keys out of logs.
- **Git branches**: a branch is a movable pointer to a commit; `git switch -c <name>` creates one and moves you onto it. Work lands on `main` only via reviewed PRs.

**Check questions & my answers**
_(to fill in)_

**What I struggled with**
_(to fill in)_
