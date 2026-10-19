# Phase 2 Execution — Task Tracker

## Phase 2A: Quick Wins (Unblock Everything)

- `[/]` **Component 4: Holographic Embedding Upgrade**
  - `[ ]` Add TF-IDF vectorizer to `holographic/retrieval.py`
  - `[ ]` Add cosine similarity search to replace keyword fallback
  - `[ ]` Add auto-embed on `store_memory()` in `holographic/store.py`

- `[ ]` **Component 3: Cron Runner Fixes**
  - `[ ]` Fix async agent init pattern
  - `[ ]` Add per-job error isolation + timeout
  - `[ ]` Log execution results to MemoryStore

- `[ ]` **Component 2: Heartbeat Activation**
  - `[ ]` Implement `_gather_reminders()` and `_gather_events()`
  - `[ ]` Implement subconscious scan stubs
  - `[ ]` Implement `deliver_notification()`
  - `[ ]` Wire heartbeat start into gateway/bot.py

## Phase 2B: Core Intelligence (after 2A)

- `[ ]` **Component 1: Master Conductor**
  - `[ ]` Create `core/conductor.py` with 11-step pipeline
  - `[ ]` Add RateLimiter + intent classifier
  - `[ ]` Add parallel retrieval dispatch
  - `[ ]` Add post-turn sync (entity extraction)
  - `[ ]` Wire into gateway

- `[ ]` **Component 5: Pattern Engine**
  - `[ ]` Create `core/patterns/__init__.py` with 5-horizon detection
  - `[ ]` Create `core/patterns/hebbian.py` with edge weight logic
  - `[ ]` Create `core/patterns/store.py` with SQLite backend

## Phase 2C: Higher-Order Systems (after 2B)

- `[ ]` **Component 7: SOUL.md / Wants Engine**
  - `[ ]` Create `core/soul.py`
  - `[ ]` Wire into Context Forge Layer 1

- `[ ]` **Component 6: Cause Chain Engine**
  - `[ ]` Create `core/cause_chain.py` (9-step pipeline)

- `[ ]` **Component 8: Spaced Repetition**
  - `[ ]` Create `core/spaced_rep.py`
