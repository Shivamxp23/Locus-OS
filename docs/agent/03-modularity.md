# 03 - Modularity (the owner's rule: EVERYTHING can be turned off or swapped)

One line: every feature is a provider behind an interface, switched by config, with a defined "off" behaviour and a proven swap.
The spec writes this for every feature as "Provider Interface" and "Swappable / off state". Print them with
`python tools/tracker/show.py F-xxxx --spec` and build exactly that.

## The universal provider pattern (spec section "UNIVERSAL PROVIDER PATTERN")
1. register: `registry.register("name", ProviderClass)`
2. configure under `locus.<area>`: `provider` (which one), `enabled` (on/off), `options` (provider-specific)
3. initialize at start: `if not enabled: SKIP`, else `registry.get(provider).initialize(options)`
4. run: `provider.method(args)`   5. stop: `provider.shutdown()`   6. health: `provider.health_check() -> {status, latency, error?}`

The 25 interfaces the spec names (default in brackets): MemoryProvider [Neo4j Agent Memory], RetrievalProvider [PageIndex],
CompressionProvider [Headroom CCR], CompactionProvider [Pi compaction], BrainProvider, PatternEngine, ContextAssembler [Context Forge],
IntentClassifier, RewardModel, LifeOSProvider, SchedulerProvider [node-cron + APScheduler], ChannelProvider [Telegram],
STTProvider [Groq Whisper], TTSProvider [Edge TTS], SearchProvider, EmbeddingProvider [pgvector], EntityExtractor,
SandboxProvider [Pi trust model], BrowserProvider [Playwright], VaultProvider [Obsidian], LearningProvider, PostTurnProvider,
UserModelProvider, SubagentArchetype, HarnessProvider [Pi].

## Names fixed here so two models cannot invent two (errata D-12)
| Thing | Python | TypeScript |
|---|---|---|
| registry | `sidecar/registry.py`: `ProviderRegistry`, `get_registry()` | `locus-extension/src/registry.ts` |
| config accessor | `sidecar/config.py`: `get(path, default=None)`, `is_enabled(path)` | `locus-extension/src/config.ts`: `getConfig(path)`, `isEnabled(path)` |
| interface (abstract) | `sidecar/providers/<interface>.py` | `locus-extension/src/providers/<interface>.ts` |
| concrete provider | `sidecar/providers/<area>/<name>.py` | `locus-extension/src/providers/<area>/<name>.ts` |
Where the config tree is stored is OPEN (errata D-10): hide it behind the accessor. If `registry` or `config` does not exist yet,
a feature task is blocked: STOP and report "blocked: registry". Those two are built once, as their own task, never inside a feature task.

## Adding or changing a feature
1. `show.py F-xxxx --spec`: copy the interface, default provider, and "Off ->" lines into your handoff.
2. Define the interface once; feature code talks to the interface only.
3. Write the default provider as a class registered by name. No business code imports a concrete provider.
4. Use the config keys exactly as the spec writes them (`locus.memory.enabled`, `locus.compaction.provider`, ...). Never rename.
5. Off behaviour = the spec's "Off ->" text. Defaults chosen here: a disabled feature's HTTP routes answer 503 with
   `{"disabled": "<config key>"}`; its Pi tools are not registered; its scheduled jobs are not scheduled; start-up still succeeds.
6. Implement `health_check()`; `locus doctor` (05-installer-onboarding.md) lists every registered provider.

## Tests that count as modularity evidence (put them in `evidence.unit`)
- `test_<feature>_off`: enabled=false -> routes/tools/jobs absent, the rest of the system starts, the spec's "Off ->" effect is visible.
- `test_<feature>_swap`: register a second fake provider under another name, set `provider`, assert the fake is called and the default is not.
- `test_<feature>_health`: `health_check()` returns status and latency, and reports a stopped dependency as not OK.
Without these three the owner counts the feature as NOT modular, whatever its level says.

## Forbidden (each has happened or is one prompt away)
- `if provider == "neo4j"` outside the provider class; model names, hosts, ports, paths, or timezones typed into business code.
- Reading `os.environ`, `process.env`, or a config file anywhere except the accessor (it also loads `~/.locus/.env` for secrets).
- A second flag system (`feature_flags.py`, env-only toggles, one setting stored in two places).
- Rebuilding what Pi already provides (KEEP-PI features): toggle Pi's own setting through the accessor instead.
- An "off" that deletes data. Off stops the feature; it never drops user data.
- Hard-coding the owner's machine (`C:\Users\soni8\...`): the home is `LOCUS_HOME`, default `~/.locus` (errata D-14).
