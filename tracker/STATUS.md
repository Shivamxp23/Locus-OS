# Tracker status (computed, not written)

- commit `a0364f456e` (dirty working tree) - 2026-10-16T02:13:14+0530 - static
- guard: PASS {'FAIL': 0, 'WARN': 10, 'INFO': 0}
- features: 125 | verified average **48.2%** | old claimed average 71.4% over 86 rows
- integrated or better: 17 | proven: 0 | overclaims (claimed >= verified + 25): 41 | no evidence: 0
- by level: {'IMPLEMENTED': 108, 'INHERITED_OK': 17}

## Biggest gaps between old claim and evidence
| ID | Feature | Claimed | Verified | Level | Flags | Next step |
|---|---|---:|---:|---|---|---|
| F-0002 | System Prompt Construction | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0003 | Tool System (13 Canonical Tools) | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0005 | Extension Lifecycle | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0012 | Onboarding Flow | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0060 | Obsidian Self-Hosted LiveSync & CouchDB Real | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0082 | Install Script (ALL platforms) | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0083 | Telegram Setup via /setup command | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0084 | core/ vs sidecar/ Deduplication | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0085 | VM Backend Setup | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0029 | Coding Context | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0046 | Telegram Gateway | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0055 | DCS / TWS / Factions | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0066 | Health Checks | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0078 | Master Conductor | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0004 | Model Management & Escalation | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0031 | CLI / Doctor Diagnostics | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0056 | Operating Modes / Scheduler | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0057 | Goal Tracker (3-Layer Stack) | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0059 | PageIndex Retrieval | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0064 | Dual Interface / Check-ins | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |

## All features
| ID | Feature | Claimed | Verified | Level | Flags | Next step |
|---|---|---:|---:|---|---|---|
| F-0001 | Pi Agent Loop | 100% | 100% | INHERITED_OK |  |  |
| F-0002 | System Prompt Construction | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0003 | Tool System (13 Canonical Tools) | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0004 | Model Management & Escalation | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0005 | Extension Lifecycle | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0006 | Context Window Management | 70% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0007 | Post-Turn Review | 80% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0008 | Stream Diagnostics | 100% | 100% | INHERITED_OK |  |  |
| F-0009 | Rate Limit Tracking | 80% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0010 | Usage/Cost Tracking | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0011 | Title Generation | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0012 | Onboarding Flow | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0013 | Agent Initialization | 100% | 100% | INHERITED_OK |  |  |
| F-0014 | 30+ LLM Providers | 100% | 100% | INHERITED_OK |  |  |
| F-0015 | OAuth Flows | 100% | 100% | INHERITED_OK |  |  |
| F-0016 | Custom/Local Models | 100% | 100% | INHERITED_OK |  |  |
| F-0017 | Provider Registry | 100% | 100% | INHERITED_OK |  |  |
| F-0018 | Model Selection | 100% | 100% | INHERITED_OK |  |  |
| F-0019 | File/Shell/Search Tools | 100% | 100% | INHERITED_OK |  |  |
| F-0020 | Harness Delegation | 65% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0021 | Neo4j Agent Memory (POLE+O) | 80% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0022 | Holographic HRR | 30% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0023 | STDP Reinforcement | 40% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0024 | Spaced Repetition | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0025 | Project Memory Decay | 25% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0026 | Headroom CCR | 50% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0027 | Session Management | 80% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0028 | Context References | 40% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0029 | Coding Context | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0030 | TUI / Dashboard | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0031 | CLI / Doctor Diagnostics | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0032 | Extension System | 100% | 100% | INHERITED_OK |  |  |
| F-0033 | ACP Protocol | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0034 | Plugin LLM | 10% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0035 | Learning / Profiling / Reward Model | 70% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0036 | Subagents / AutoResearch | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0037 | Injection Filter | 80% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0038 | Shell Sandbox | 100% | 100% | INHERITED_OK |  |  |
| F-0039 | Project Trust | 100% | 100% | INHERITED_OK |  |  |
| F-0040 | Shell Blocklist | 70% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0041 | Data Redaction | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0042 | Think Token Scrubbing | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0043 | Message Sanitization | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0044 | STT / TTS Providers | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0045 | Browser Automation | 45% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0046 | Telegram Gateway | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0047 | Graceful Restart | 50% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0048 | MCP Server/Client | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0049 | Trajectory Recording | 40% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0050 | AI Chat Archiver | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0051 | Computer Use / Screen | 40% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0052 | VNC Remote | 20% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0053 | Google Calendar | 35% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0054 | CI/CD / Docker | 65% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0055 | DCS / TWS / Factions | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0056 | Operating Modes / Scheduler | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0057 | Goal Tracker (3-Layer Stack) | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0058 | Proactive Inner Loop | 70% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0059 | PageIndex Retrieval | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0060 | Obsidian Self-Hosted LiveSync & CouchDB Real | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0061 | Rough Note Parser | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0062 | Link Dump Logger | 75% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0063 | Excalidraw MCP Skill | 70% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0064 | Dual Interface / Check-ins | 85% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0065 | Error Classifier | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0066 | Health Checks | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0067 | Notifications | 65% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0068 | Connectivity Check | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0069 | Code Graph | 50% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0070 | Subconscious | 40% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0071 | Workflows | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0072 | Collector + Chunker | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0073 | Cause Chain Engine | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0074 | SOUL.md / Wants Engine | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0075 | Content Engine | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0076 | Spaced Repetition | 60% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0077 | QLoRA Pipeline | 25% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0078 | Master Conductor | 90% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0079 | Dashboard/TUI Spec | 45% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0080 | Redis Integration | 55% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0081 | Obsidian/LightRAG Bridge | 45% | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0082 | Install Script (ALL platforms) | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0083 | Telegram Setup via /setup command | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0084 | core/ vs sidecar/ Deduplication | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0085 | VM Backend Setup | 100% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0086 | Deployment (systemd/Docker) | 65% | 40% | IMPLEMENTED | OVERCLAIM | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0087 | ARCH-6 Pi bridge (sidecar -> Pi CLI, used by | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0088 | Memory Tree (Hierarchical Summarization Casc | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0089 | Memory Sync (Multi-Source Ingestion Pipeline | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0090 | Memory Queue (Async Job Pipeline) | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0091 | Memory Diff (Snapshot-Based Change Tracking) | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0092 | Query Router / Intent Classifier (Stage 2) | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0093 | State Engine (Stage 3) | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0094 | Context Forge (Stage 6) — The 6-Layer Assemb | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0095 | Anti-Hallucination Guard (Stage 10) | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0096 | Intelligent Model Routing + Quality-Based Fa | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0097 | Streaming (SSE) | - | 100% | INHERITED_OK |  |  |
| F-0098 | Image Generation | - | 100% | INHERITED_OK |  |  |
| F-0099 | Git Tools | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0100 | Tool Call Validation | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0101 | Tool Result Classification | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0102 | Tool Output Accumulator | - | 100% | INHERITED_OK |  |  |
| F-0103 | Tool Timeout / Budget | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0104 | Custom Locus Tools | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0105 | Web Search (8 Providers) | - | 100% | INHERITED_OK |  |  |
| F-0106 | Pi Utilities (Clipboard, Syntax Highlighting | - | 100% | INHERITED_OK |  |  |
| F-0107 | File Safety | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0108 | Autonomy Tiers | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0109 | Approval Gate | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0110 | Context Compression | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0111 | Emergency Task Injection | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0112 | Exhaustion Predictor | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0113 | Weekly Faction Rebalance | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0114 | Review Cadence System | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0115 | Goal Stack Enforcement | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0116 | Cross-Faction Efficiency | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0117 | Four-Level Emergency Protocol | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0118 | Memory Provider Interface | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0119 | Skill System & Multi-Source Marketplace | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0120 | Self-Evolving Architect Bot | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0121 | Agent Experience Tracking (Procedural Memory | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0122 | LOCUS_SHORTHAND 4× Text Compressor | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0123 | 3-Level Tag Hierarchy & Semantic Indexing | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0124 | Auxiliary LLM Client | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
| F-0125 | Modularity foundation: provider registry + c | - | 40% | IMPLEMENTED |  | Add evidence.unit (a pytest/vitest command over a test that mentions the feature, with rea |
