# Tracker status (computed, not written)

- commit `92816bf3e7` (dirty working tree) - 2026-10-20T11:50:07+0530 - with test runs
- guard: PASS {'FAIL': 0, 'WARN': 11, 'INFO': 0}
- features: 125 | verified average **31.6%** | old claimed average 71.4% over 86 rows
- integrated or better: 41 | proven: 0 | overclaims (claimed >= verified + 25): 51 | no evidence: 78
- by level: {'FILES_PRESENT': 2, 'INHERITED_OK': 12, 'INTEGRATED': 29, 'NO_EVIDENCE': 78, 'UNIT_VERIFIED': 4}

## Biggest gaps between old claim and evidence
| ID | Feature | Claimed | Verified | Level | Flags | Next step |
|---|---|---:|---:|---|---|---|
| F-0029 | Coding Context | 90% | 0% | NO_EVIDENCE | NO_FILES_NAMED,OVERCLAIM | Name the files this feature lives in (evidence.files). |
| F-0066 | Health Checks | 90% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/main.py. Create them or correct the path. |
| F-0078 | Master Conductor | 90% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/conductor.py. Create them or correct the path. |
| F-0031 | CLI / Doctor Diagnostics | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/main.py. Create them or correct the path. |
| F-0056 | Operating Modes / Scheduler | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/scheduler/. Create them or correct the path. |
| F-0059 | PageIndex Retrieval | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/search/pageindex.py. Create them or correct the path. |
| F-0064 | Dual Interface / Check-ins | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/gateway/. Create them or correct the path. |
| F-0021 | Neo4j Agent Memory (POLE+O) | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/neo4j_memory.py. Create them or correct the path. |
| F-0027 | Session Management | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/memory.py, sidecar/session_export.py. Create them or cor |
| F-0037 | Injection Filter | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/injection_filter.py. Create them or correct the |
| F-0041 | Data Redaction | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/redact.py. Create them or correct the path. |
| F-0042 | Think Token Scrubbing | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/think_scrubber.py. Create them or correct the p |
| F-0043 | Message Sanitization | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/sanitizer.py. Create them or correct the path. |
| F-0061 | Rough Note Parser | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/ingestion/rough_note_parser.py. Create them or correct t |
| F-0062 | Link Dump Logger | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/ingestion/link_logger.py. Create them or correct the pat |
| F-0040 | Shell Blocklist | 70% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/. Create them or correct the path. |
| F-0057 | Goal Tracker (3-Layer Stack) | 85% | 15% | FILES_PRESENT | OVERCLAIM | Declare evidence.symbols that prove the implementation exists. |
| F-0063 | Excalidraw MCP Skill | 70% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/display/excalidraw_builder.py. Create them or correct th |
| F-0054 | CI/CD / Docker | 65% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/deployment/. Create them or correct the path. |
| F-0067 | Notifications | 65% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/gateway/. Create them or correct the path. |

## All features
| ID | Feature | Claimed | Verified | Level | Flags | Next step |
|---|---|---:|---:|---|---|---|
| F-0001 | Pi Agent Loop | 100% | 100% | INHERITED_OK |  |  |
| F-0002 | System Prompt Construction | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0003 | Tool System (13 Canonical Tools) | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0004 | Model Management & Escalation | 85% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0005 | Extension Lifecycle | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0006 | Context Window Management | 70% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0007 | Post-Turn Review | 80% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0008 | Stream Diagnostics | 100% | 100% | INHERITED_OK |  |  |
| F-0009 | Rate Limit Tracking | 80% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0010 | Usage/Cost Tracking | 75% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0011 | Title Generation | 75% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0012 | Onboarding Flow | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0013 | Agent Initialization | 100% | 100% | INHERITED_OK |  |  |
| F-0014 | 30+ LLM Providers | 100% | 100% | INHERITED_OK |  |  |
| F-0015 | OAuth Flows | 100% | 100% | INHERITED_OK |  |  |
| F-0016 | Custom/Local Models | 100% | 100% | INHERITED_OK |  |  |
| F-0017 | Provider Registry | 100% | 100% | INHERITED_OK |  |  |
| F-0018 | Model Selection | 100% | 100% | INHERITED_OK |  |  |
| F-0019 | File/Shell/Search Tools | 100% | 100% | INHERITED_OK |  |  |
| F-0020 | Harness Delegation | 65% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0021 | Neo4j Agent Memory (POLE+O) | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/neo4j_memory.py. Create them or correct the path. |
| F-0022 | Holographic HRR | 30% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/holographic/. Create them or correct the path. |
| F-0023 | STDP Reinforcement | 40% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/patterns/hebbian.py. Create them or correct the path. |
| F-0024 | Spaced Repetition | 60% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/spaced_rep.py. Create them or correct the path. |
| F-0025 | Project Memory Decay | 25% | 0% | NO_EVIDENCE | NO_FILES_NAMED,OVERCLAIM | Name the files this feature lives in (evidence.files). |
| F-0026 | Headroom CCR | 50% | 15% | FILES_PRESENT | OVERCLAIM | Declare evidence.symbols that prove the implementation exists. |
| F-0027 | Session Management | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/memory.py, sidecar/session_export.py. Create them or cor |
| F-0028 | Context References | 40% | 0% | NO_EVIDENCE | NO_FILES_NAMED,OVERCLAIM | Name the files this feature lives in (evidence.files). |
| F-0029 | Coding Context | 90% | 0% | NO_EVIDENCE | NO_FILES_NAMED,OVERCLAIM | Name the files this feature lives in (evidence.files). |
| F-0030 | TUI / Dashboard | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/curses_ui.py, sidecar/display/dashboard.py. Create the |
| F-0031 | CLI / Doctor Diagnostics | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/main.py. Create them or correct the path. |
| F-0032 | Extension System | 100% | 100% | INHERITED_OK |  |  |
| F-0033 | ACP Protocol | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/acp_server.py. Create them or correct the path. |
| F-0034 | Plugin LLM | 10% | 0% | NO_EVIDENCE | NO_FILES_NAMED | Name the files this feature lives in (evidence.files). |
| F-0035 | Learning / Profiling / Reward Model | 70% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0036 | Subagents / AutoResearch | 60% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0037 | Injection Filter | 80% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/injection_filter.py. Create them or correct the |
| F-0038 | Shell Sandbox | 100% | 100% | INHERITED_OK |  |  |
| F-0039 | Project Trust | 100% | 100% | INHERITED_OK |  |  |
| F-0040 | Shell Blocklist | 70% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/. Create them or correct the path. |
| F-0041 | Data Redaction | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/redact.py. Create them or correct the path. |
| F-0042 | Think Token Scrubbing | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/think_scrubber.py. Create them or correct the p |
| F-0043 | Message Sanitization | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/security/sanitizer.py. Create them or correct the path. |
| F-0044 | STT / TTS Providers | 60% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/voice/. Create them or correct the path. |
| F-0045 | Browser Automation | 45% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/browser/. Create them or correct the path. |
| F-0046 | Telegram Gateway | 90% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0047 | Graceful Restart | 50% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/gateway/. Create them or correct the path. |
| F-0048 | MCP Server/Client | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/mcp_client.py. Create them or correct the path. |
| F-0049 | Trajectory Recording | 40% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0050 | AI Chat Archiver | 55% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0051 | Computer Use / Screen | 40% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/screen/. Create them or correct the path. |
| F-0052 | VNC Remote | 20% | 0% | NO_EVIDENCE | NO_FILES_NAMED | Name the files this feature lives in (evidence.files). |
| F-0053 | Google Calendar | 35% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/integrations/calendar_sync.py. Create them or correct th |
| F-0054 | CI/CD / Docker | 65% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/deployment/. Create them or correct the path. |
| F-0055 | DCS / TWS / Factions | 90% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0056 | Operating Modes / Scheduler | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/scheduler/. Create them or correct the path. |
| F-0057 | Goal Tracker (3-Layer Stack) | 85% | 15% | FILES_PRESENT | OVERCLAIM | Declare evidence.symbols that prove the implementation exists. |
| F-0058 | Proactive Inner Loop | 70% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0059 | PageIndex Retrieval | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/search/pageindex.py. Create them or correct the path. |
| F-0060 | Obsidian Self-Hosted LiveSync & CouchDB Real | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0061 | Rough Note Parser | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/ingestion/rough_note_parser.py. Create them or correct t |
| F-0062 | Link Dump Logger | 75% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/ingestion/link_logger.py. Create them or correct the pat |
| F-0063 | Excalidraw MCP Skill | 70% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/display/excalidraw_builder.py. Create them or correct th |
| F-0064 | Dual Interface / Check-ins | 85% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/gateway/. Create them or correct the path. |
| F-0065 | Error Classifier | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/diagnostics/error_classifier.py. Create them or correct  |
| F-0066 | Health Checks | 90% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/main.py. Create them or correct the path. |
| F-0067 | Notifications | 65% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/gateway/. Create them or correct the path. |
| F-0068 | Connectivity Check | 60% | 0% | NO_EVIDENCE | NO_FILES_NAMED,OVERCLAIM | Name the files this feature lives in (evidence.files). |
| F-0069 | Code Graph | 50% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: .graphifyignore. Create them or correct the path. |
| F-0070 | Subconscious | 40% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/heartbeat/. Create them or correct the path. |
| F-0071 | Workflows | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/scheduler/workflow.py. Create them or correct the path. |
| F-0072 | Collector + Chunker | 60% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/ingestion/collector.py. Create them or correct the path. |
| F-0073 | Cause Chain Engine | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/cause_chain.py. Create them or correct the path. |
| F-0074 | SOUL.md / Wants Engine | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/soul.py. Create them or correct the path. |
| F-0075 | Content Engine | 60% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/content/engine.py. Create them or correct the path. |
| F-0076 | Spaced Repetition | 60% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/spaced_rep.py. Create them or correct the path. |
| F-0077 | QLoRA Pipeline | 25% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/evolution/dataset_curator.py. Create them or correct the |
| F-0078 | Master Conductor | 90% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/conductor.py. Create them or correct the path. |
| F-0079 | Dashboard/TUI Spec | 45% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: locus_cli/curses_ui.py. Create them or correct the path. |
| F-0080 | Redis Integration | 55% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/redis_state.py. Create them or correct the path. |
| F-0081 | Obsidian/LightRAG Bridge | 45% | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING,OVERCLAIM | Files claimed but absent: sidecar/vault/lightrag_bridge.py. Create them or correct the pat |
| F-0082 | Install Script (ALL platforms) | 100% | 65% | UNIT_VERIFIED | OVERCLAIM | Add evidence.integration: a DIFFERENT test that crosses a boundary (sidecar<->Pi, extensio |
| F-0083 | Telegram Setup via /setup command | 100% | 65% | UNIT_VERIFIED | OVERCLAIM | Add evidence.integration: a DIFFERENT test that crosses a boundary (sidecar<->Pi, extensio |
| F-0084 | core/ vs sidecar/ Deduplication | 100% | 65% | UNIT_VERIFIED | OVERCLAIM | Add evidence.integration: a DIFFERENT test that crosses a boundary (sidecar<->Pi, extensio |
| F-0085 | VM Backend Setup | 100% | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0086 | Deployment (systemd/Docker) | 65% | 65% | UNIT_VERIFIED |  | Add evidence.integration: a DIFFERENT test that crosses a boundary (sidecar<->Pi, extensio |
| F-0087 | ARCH-6 Pi bridge (sidecar -> Pi CLI, used by | - | 0% | NO_EVIDENCE | CLAIMED_FILES_MISSING | Files claimed but absent: sidecar/cron_runner.py. Create them or correct the path. |
| F-0088 | Memory Tree (Hierarchical Summarization Casc | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0089 | Memory Sync (Multi-Source Ingestion Pipeline | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0090 | Memory Queue (Async Job Pipeline) | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0091 | Memory Diff (Snapshot-Based Change Tracking) | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0092 | Query Router / Intent Classifier (Stage 2) | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0093 | State Engine (Stage 3) | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0094 | Context Forge (Stage 6) — The 6-Layer Assemb | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0095 | Anti-Hallucination Guard (Stage 10) | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0096 | Intelligent Model Routing + Quality-Based Fa | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0097 | Streaming (SSE) | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0098 | Image Generation | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0099 | Git Tools | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
| F-0100 | Tool Call Validation | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0101 | Tool Result Classification | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0102 | Tool Output Accumulator | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0103 | Tool Timeout / Budget | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0104 | Custom Locus Tools | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0105 | Web Search (8 Providers) | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0106 | Pi Utilities (Clipboard, Syntax Highlighting | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0107 | File Safety | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0108 | Autonomy Tiers | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0109 | Approval Gate | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0110 | Context Compression | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0111 | Emergency Task Injection | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0112 | Exhaustion Predictor | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0113 | Weekly Faction Rebalance | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0114 | Review Cadence System | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0115 | Goal Stack Enforcement | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0116 | Cross-Faction Efficiency | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0117 | Four-Level Emergency Protocol | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0118 | Memory Provider Interface | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0119 | Skill System & Multi-Source Marketplace | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0120 | Self-Evolving Architect Bot | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0121 | Agent Experience Tracking (Procedural Memory | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0122 | LOCUS_SHORTHAND 4× Text Compressor | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0123 | 3-Level Tag Hierarchy & Semantic Indexing | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0124 | Auxiliary LLM Client | - | 0% | NO_EVIDENCE |  | Name the files this feature lives in (evidence.files). |
| F-0125 | Modularity foundation: provider registry + c | - | 85% | INTEGRATED |  | Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff |
