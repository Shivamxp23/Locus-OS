# Spec Trace for US-51: Holographic HRR (Memory Binding)

| Spec Ref | Spec Sentence | Code Implementation | Test File:Line |
|---|---|---|---|
| §4.10 line 1166 | "## Feature §4.10: Holographic Reduced Representations (HRR Memory Binding)" | `sidecar/memory/hrr.py:1` | `tests/unit/test_holographic_hrr.py:22` |
| §4.10 line 1185 | "HRRVector: dimension: int = 2048, values: float[2048] // Zero-mean, variance 1/D normal distribution" | `sidecar/providers/holographic.py:15`, `locus-extension/src/memory/hrr-adapter.ts:10` | `tests/unit/test_holographic_hrr.py:22` |
| §4.10 line 1189 | "Codebook: symbols: Dict[string -> HRRVector]" | `sidecar/memory/hrr_codebook.py:38`, `sidecar/providers/holographic.py:100` | `tests/unit/test_holographic_hrr.py:40`, `tests/integration/test_holographic_hrr_service.py:53` |
| §4.10 line 1195 | "FUNCTION bind(a: HRRVector, b: HRRVector) -> HRRVector: A_fft = FFT(a.values); B_fft = FFT(b.values); C_fft = A_fft * B_fft; c_vals = Real(IFFT(C_fft)); RETURN normalize(c_vals)" | `sidecar/memory/hrr.py:48`, `sidecar/service.py:3399` | `tests/unit/test_holographic_hrr.py:68`, `tests/integration/test_holographic_hrr_service.py:77` |
| §4.10 line 1204 | "FUNCTION unbind(c: HRRVector, b: HRRVector) -> HRRVector: b_inv = invert_axes(b.values); RETURN bind(c, b_inv)" | `sidecar/memory/hrr.py:66`, `sidecar/service.py:3415` | `tests/unit/test_holographic_hrr.py:91`, `tests/integration/test_holographic_hrr_service.py:77` |
| §4.10 line 1210 | "FUNCTION bundle(vectors: List[HRRVector]) -> HRRVector: s_vals = sum([v.values for v in vectors]); RETURN normalize(s_vals)" | `sidecar/memory/hrr.py:77`, `sidecar/service.py:3431` | `tests/unit/test_holographic_hrr.py:116`, `tests/integration/test_holographic_hrr_service.py:107` |
| §4.10 line 1215 | "FUNCTION cleanup(noisy_vector: HRRVector, codebook: Codebook, threshold=0.70) -> Optional[string]:" | `sidecar/memory/hrr.py:104`, `sidecar/service.py:3449` | `tests/unit/test_holographic_hrr.py:136`, `tests/integration/test_holographic_hrr_service.py:97` |
| §4.10 line 1226 | "FUNCTION encode_ephemeral_state(current_task, active_mode, stress_level) -> HRRVector:" | `sidecar/memory/hrr.py:186`, `sidecar/service.py:3466` | `tests/unit/test_holographic_hrr.py:162`, `tests/integration/test_holographic_hrr_service.py:118` |
| §4.10 line 1239 | "Provider Interface: AssociativeMemoryProvider" | `sidecar/providers/holographic.py:66`, `sidecar/service.py:3355` | `tests/unit/test_holographic_hrr.py:162` |
| §4.10 line 1240 | "codebook cache persisted at .locus/memory/hrr_codebook.bin." | `sidecar/memory/hrr_codebook.py:46`, `sidecar/service.py:3371` | `tests/unit/test_holographic_hrr.py:40`, `tests/integration/test_holographic_hrr_service.py:41` |
| §4.10 line 1241 | "Swappable / off state: locus.memory.hrr.enabled. Off -> Locus skips holographic state bundling; uses standard JSON key-value store in Redis." | `sidecar/service.py:3380` | `tests/integration/test_holographic_hrr_service.py:132` |
