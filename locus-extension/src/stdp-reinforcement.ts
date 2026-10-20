/**
 * locus-extension/src/stdp-reinforcement.ts
 *
 * SPEC §4.12: STDP Reinforcement (Spike-Timing-Dependent Plasticity) client module.
 */

export {
  STDPClient,
  STDPConfig,
  RetrievalEvent,
  OutcomeEvent,
  TraversedEdgeRecord,
  TurnAuditLog,
  EdgeUpdateResult,
  TurnSTDPResult,
  PruneCandidate,
} from "./memory/stdp-updater";
