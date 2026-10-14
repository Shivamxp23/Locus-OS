# Codebase Report for locus-os

## Overview
This codebase is a hybrid application consisting of a backend (Python/Flask), a PWA frontend (React/JavaScript), and various scripts for data processing and synchronization. The backend handles core logic including state engine, pattern detection, inference, and vault management. The frontend is a progressive web app for capturing and viewing tasks/goals. Scripts handle database setup, vault synchronization, and chat synchronization.

## File-by-File Details

### Top-level
| File/Folder | Purpose | Duplicate? |
|-------------|---------|------------|
| .github/workflows/deploy-pwa.yml | CI/CD workflow to deploy the PWA | No |
| .gitignore | Specifies files to ignore in version control | No |
| .locus/distiller_state.json | Stores state for the distiller process (likely JSON state file) | No |
| docker-compose.yml | Defines Docker Compose services for the application | No |
| 5.md | This report file | No |

### backend/
| File | Purpose | Duplicate? |
|------|---------|------------|
| Dockerfile | Docker image definition for the backend | No |
| main.py | Entry point for the Flask/FastAPI server | No |
| requirements.txt | Python dependencies | No |
| core/__init__.py | Package initializer for core modules | No |
| core/context_synthesizer.py | Synthesizes context from various sources | No |
| core/db.py | Database connection and initialization (likely SQLite or similar) | No |
| core/hebbian.py | Implements Hebbian learning algorithm for pattern recognition | No |
| core/inner_loop.py | Inner loop logic for the core engine | No |
| core/pattern_detector.py | Detects patterns in data | No |
| core/query_classifier.py | Classifies queries into categories | No |
| core/shorthand.py | Handles shorthand notation for commands or data | No |
| core/source_retriever.py | Retrieves source data for processing | No |
| core/state_engine.py | Core state engine managing application state | No |
| routers/__init__.py | Package initializer for routers | No |
| routers/analytics_data.py | API endpoint for analytics data | Yes (router) |
| routers/auth.py | Authentication routes | Yes (router) |
| routers/brain.py | Brain-related API endpoints | Yes (router) |
| routers/captures.py | Capture-related API endpoints | Yes (router) |
| routers/checkins.py | Check-in API endpoints | Yes (router) |
| routers/context.py | Context API endpoints | Yes (router) |
| routers/factions.py | Faction-related API endpoints | Yes (router) |
| routers/goals.py | Goals API endpoints | Yes (router) |
| routers/inference.py | Inference API endpoints | Yes (router) |
| routers/logs.py | Logging API endpoints | Yes (router) |
| routers/push.py | Push notification API endpoints | Yes (router) |
| routers/schedule.py | Schedule API endpoints | Yes (router) |
| routers/tasks.py | Tasks API endpoints | Yes (router) |
| routers/vault.py | Vault API endpoints | Yes (router) |
| routers/vector.py | Vector operations API endpoints | Yes (router) |
| services/__init__.py | Package initializer for services | No |
| services/brain/__init__.py | Package initializer for brain services | No |
| services/brain/chunker.py | Brain chunking logic | No |
| services/brain/collector.py | Brain data collector | No |
| services/brain/goal_tracker.py | Tracks goals across the system | No |
| services/brain/pattern_engine.py | Pattern engine for brain data | No |
| services/goal_distiller.py | Distills goals from various sources | No |
| services/google_calendar.py | Integrates with Google Calendar API | No |
| services/lightrag_service.py | Service for Lightrag (lightweight RAG) integration | No |
| services/llm.py | Large Language Model service abstraction | No |
| services/neo4j_service.py | Neo4j graph database service | No |
| services/proposition_chunker.py | Chunks propositions for storage/retrieval | No |
| services/push_service.py | Push notification service | No |
| services/qdrant_service.py | Qdrant vector database service | No |
| services/scheduler_engine.py | Scheduler engine for tasks | No |
| services/sync_layer.py | Synchronization layer for data consistency | No |
| services/vault_change_tracker.py | Tracks changes in vault data | No |
| services/vault_chat_logger.py | Logs chat interactions to vault | No |
| services/vault_enricher.py | Enriches vault data with additional context | No |
| services/vault_indexer_v2.py | Indexes vault data (version 2) | No |
| services/vault_jobs.py | Background jobs for vault operations | No |
| telegram_bot.py | Telegram bot integration | No |

### pwa/
| File | Purpose | Duplicate? |
|------|---------|------------|
| package.json | Node.js package configuration | No |
| public/_redirects | Redirects for the PWA | No |
| public/favicon.ico | Favicon for the PWA | No |
| public/index.html | Main HTML entry point | No |
| public/logo192.png | 192px logo for PWA | No |
| public/logo512.png | 512px logo for PWA | No |
| public/manifest.json | PWA manifest configuration | No |
| public/robots.txt | Robots.txt for SEO/crawlers | No |
| src/App.css | Main application styles | No |
| src/App.js | Main application component | No |
| src/App.test.js | Unit tests for App component | No |
| src/components/BottomNav.css | Bottom navigation styles | No |
| src/components/BottomNav.js | Bottom navigation component | No |
| src/components/QuickCapture.css | Quick capture styles | No |
| src/components/QuickCapture.js | Quick capture component | No |
| src/components/Sidebar.css | Sidebar styles | No |
| src/components/Sidebar.js | Sidebar component | No |
| src/components/ToastContainer.js | Toast notification container | No |
| src/components/TreeOrganism.css | Tree organism styles | No |
| src/components/TreeOrganism.js | Tree organism component | No |
| src/context/AppContext.js | Application context provider | No |
| src/index.css | Global CSS styles | No |
| src/index.js | Entry point for the React app | No |
| src/logo.svg | SVG logo component | No |
| src/reportWebVitals.js | Web vitals reporting utility | No |
| src/screens/Analytics.css | Analytics screen styles | No |
| src/screens/Analytics.js | Analytics screen component | No |
| src/screens/CheckIn.css | Check-in screen styles | No |
| src/screens/CheckIn.js | Check-in screen component | No |
| src/screens/Dashboard.css | Dashboard screen styles | No |
| src/screens/Dashboard.js | Dashboard screen component | No |
| src/screens/Onboarding.css | Onboarding screen styles | No |
| src/screens/Onboarding.js | Onboarding screen component | No |
| src/screens/Organism.css | Organism screen styles | No |
| src/screens/Organism.js | Organism screen component | No |
| src/screens/Projects.css | Projects screen styles | No |
| src/screens/Projects.js | Projects screen component | No |
| src/screens/Settings.css | Settings screen styles | No |
| src/screens/Settings.js | Settings screen component | No |
| src/screens/Today.css | Today screen styles | No |
| src/screens/Today.js | Today screen component | No |
| src/screens/Vault.css | Vault screen styles | No |
| src/screens/Vault.js | Vault screen component | No |
| src/service-worker.js | Service worker for PWA offline support | No |
| src/serviceWorkerRegistration.js | Registers service worker | No |
| src/setupTests.js | Test setup for Jest | No |
| src/utils/api.js | API utility functions | No |
| src/utils/helpers.js | Helper functions | No |
| src/utils/helpers.test.js | Tests for helpers | No |
| src/utils/pushUtils.js | Push notification utilities | No |

### scripts/
| File | Purpose | Duplicate? |
|------|---------|------------|
| build_personality_graph.py | Builds personality graph from data | No |
| check_syntax.py | Checks syntax of Python files | No |
| create_tables.sql | SQL script to create database tables | No |
| diagnose_databases.py | Diagnoses database issues | No |
| index_vault.py | Indexes vault data | No |
| init.sql | Initial SQL setup | No |
| locus_chats/README.md | Documentation for locus_chats scripts | No |
| locus_chats/config.json | Configuration for locus_chats (platforms, accounts, etc.) | No |
| locus_chats/requirements.txt | Python dependencies for locus_chats | No |
| locus_chats/setup_auth.py | One-time auth setup for platforms | No |
| locus_chats/sync_chats.py | Syncs chat histories from platforms to vault | No |
| migrate_v2.sql | Database migration for version 2 | No |
| migrate_v3_inference.sql | Database migration for version 3 inference | No |
| smoke_tests.sh | Smoke tests script | No |
| start_lightrag.sh | Script to start Lightrag service | No |

### Additional Notes
- Many router files serve a similar purpose (exposing API endpoints). They are marked as duplicates in the "Duplicate?" column.
- Service files each provide distinct integrations or functionalities, so they are not considered duplicates.
- The backend core modules each have unique responsibilities.
- The frontend components are largely unique in purpose.
- No exact code duplication detected across the repository.
