"""
tests/unit/test_holographic_hrr.py
Unit tests for Holographic Reduced Representations (HRR Memory Binding) per SPEC §4.10 / F-0022.
"""
from __future__ import annotations

import os
import tempfile
import numpy as np
import pytest

from sidecar.memory.hrr import (
    HolographicMemory,
    circular_convolution,
    circular_correlation,
    cleanup_memory,
    cosine_similarity,
    invert_axes,
    normalize,
    superposition_bundle,
)
from sidecar.memory.hrr_codebook import HRRCodebook, generate_unitary_vector
from sidecar.providers.holographic import HolographicConfig, HRRVector


def test_hrr_vector_initialization_and_normalization() -> None:
    """
    SPEC §4.10 line 1185: "HRRVector: dimension: int = 2048, values: float[2048] // Zero-mean, variance 1/D normal distribution"
    """
    dim = 2048
    vec = generate_unitary_vector("TEST:SYMBOL", dimension=dim)
    assert len(vec) == dim
    norm = np.linalg.norm(vec)
    assert pytest.approx(norm, rel=1e-5) == 1.0

    hrr = HRRVector.from_numpy(vec)
    assert hrr.dimension == dim
    assert len(hrr.values) == dim
    as_dict = hrr.to_dict()
    assert as_dict["dimension"] == dim
    restored = HRRVector.from_dict(as_dict)
    assert restored.dimension == dim
    assert np.allclose(restored.to_numpy(), vec)


def test_codebook_symbol_deterministic_and_cache() -> None:
    """
    SPEC §4.10 line 1189: "Codebook: symbols: Dict[string -> HRRVector]"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = os.path.join(tmpdir, "codebook.npz")
        cb = HRRCodebook(dimension=512, cache_path=cache_path)

        v1 = cb.get_or_create("ROLE:TASK")
        v2 = cb.get_or_create("ROLE:TASK")
        assert np.array_equal(v1, v2)

        v3 = cb.get_or_create("ROLE:MODE")
        assert not np.allclose(v1, v3)
        # Quasi-orthogonal
        sim = cosine_similarity(v1, v3)
        assert abs(sim) < 0.15

        cb.save()
        assert os.path.exists(cache_path)

        cb2 = HRRCodebook(dimension=512, cache_path=cache_path)
        v1_loaded = cb2.get("ROLE:TASK")
        assert v1_loaded is not None
        assert np.allclose(v1_loaded, v1)


def test_circular_convolution_bind() -> None:
    """
    SPEC §4.10 line 1195: "FUNCTION bind(a: HRRVector, b: HRRVector) -> HRRVector: A_fft = FFT(a.values); B_fft = FFT(b.values); C_fft = A_fft * B_fft; c_vals = Real(IFFT(C_fft)); RETURN normalize(c_vals)"
    """
    cb = HRRCodebook(dimension=512)
    a = cb.get_or_create("ROLE:TASK")
    b = cb.get_or_create("TASK:123")

    c = circular_convolution(a, b)
    assert len(c) == 512
    assert pytest.approx(np.linalg.norm(c), rel=1e-5) == 1.0

    # Binding is commutative: a ⊛ b == b ⊛ a
    c_comm = circular_convolution(b, a)
    assert np.allclose(c, c_comm, atol=1e-6)

    # Bound vector is quasi-orthogonal to both inputs
    assert abs(cosine_similarity(c, a)) < 0.15
    assert abs(cosine_similarity(c, b)) < 0.15


def test_circular_correlation_unbind() -> None:
    """
    SPEC §4.10 line 1204: "FUNCTION unbind(c: HRRVector, b: HRRVector) -> HRRVector: b_inv = invert_axes(b.values); RETURN bind(c, b_inv)"
    """
    cb = HRRCodebook(dimension=1024)
    key = cb.get_or_create("ROLE:TASK")
    val = cb.get_or_create("TASK:IMPLEMENT_CODE")

    bound = circular_convolution(key, val)
    unbound_val = circular_correlation(bound, key)

    sim = cosine_similarity(unbound_val, val)
    # Unitary key gives near exact recovery (> 0.95)
    assert sim > 0.90

    # Unbinding with wrong key gives near zero similarity
    wrong_key = cb.get_or_create("ROLE:UNKNOWN")
    unbound_wrong = circular_correlation(bound, wrong_key)
    assert abs(cosine_similarity(unbound_wrong, val)) < 0.15


def test_vector_superposition_bundle() -> None:
    """
    SPEC §4.10 line 1210: "FUNCTION bundle(vectors: List[HRRVector]) -> HRRVector: s_vals = sum([v.values for v in vectors]); RETURN normalize(s_vals)"
    """
    cb = HRRCodebook(dimension=1024)
    v1 = cb.get_or_create("ITEM:1")
    v2 = cb.get_or_create("ITEM:2")
    v3 = cb.get_or_create("ITEM:3")

    bundled = superposition_bundle([v1, v2, v3])
    assert len(bundled) == 1024
    assert pytest.approx(np.linalg.norm(bundled), rel=1e-5) == 1.0

    # Each constituent vector has positive projection onto bundle (~ 1/sqrt(3) ≈ 0.577)
    for v in [v1, v2, v3]:
        sim = cosine_similarity(bundled, v)
        assert sim > 0.40


def test_cleanup_memory_associative_recall() -> None:
    """
    SPEC §4.10 line 1215: "FUNCTION cleanup(noisy_vector: HRRVector, codebook: Codebook, threshold=0.70) -> Optional[string]:"
    """
    cb = HRRCodebook(dimension=1024)
    role = cb.get_or_create("ROLE:TASK")
    task = cb.get_or_create("TASK:ANALYZE")
    cb.get_or_create("TASK:OTHER_1")
    cb.get_or_create("TASK:OTHER_2")

    bound = circular_convolution(role, task)
    unbound = circular_correlation(bound, role)

    # Cleanup with threshold=0.70 per spec
    recovered, sim = cleanup_memory(unbound, cb, threshold=0.70)
    assert recovered == "TASK:ANALYZE"
    assert sim >= 0.70

    # Noisy random vector below threshold
    rng = np.random.default_rng(999)
    noise = rng.normal(0, 1, 1024)
    noise = noise / np.linalg.norm(noise)
    recovered_noise, sim_noise = cleanup_memory(noise, cb, threshold=0.70)
    assert recovered_noise is None
    assert sim_noise < 0.70


def test_encode_ephemeral_state_pipeline() -> None:
    """
    SPEC §4.10 line 1226: "FUNCTION encode_ephemeral_state(current_task, active_mode, stress_level) -> HRRVector:"
    """
    mem = HolographicMemory(config=HolographicConfig(dimension=1024, similarity_threshold=0.70))

    current_task = {"id": "task_build_feature"}
    active_mode = {"name": "PEAK"}
    stress_level = {"category": "LOW"}

    state_vec = mem.encode_ephemeral_state(current_task, active_mode, stress_level)
    assert state_vec.dimension == 1024
    assert pytest.approx(np.linalg.norm(state_vec.to_numpy()), rel=1e-5) == 1.0

    # Unbind TASK role from composite state vector
    role_task = mem.get_or_create_symbol("ROLE:TASK")
    unbound_task = mem.unbind(state_vec, role_task)

    # In 3-constituent bundle, constituent similarity is ~ 1/sqrt(3) ≈ 0.577
    target_vec = mem.get_or_create_symbol("TASK:task_build_feature")
    sim = mem.similarity(unbound_task, target_vec)
    assert sim > 0.45

    # With bundle threshold 0.45, cleanup identifies task
    best_sym, score = mem.cleanup_with_score(unbound_task, threshold=0.45)
    assert best_sym == "TASK:task_build_feature"


def test_error_containment_and_dimensions() -> None:
    """
    SPEC §4.10 line 1186: "dimension: int = 2048"
    Assert dimension mismatch raises ValueError.
    """
    mem = HolographicMemory(config=HolographicConfig(dimension=512))
    v1 = HRRVector(dimension=512, values=[0.1] * 512)
    v2 = HRRVector(dimension=256, values=[0.1] * 256)

    with pytest.raises(ValueError, match="dimensions do not match"):
        mem.bind(v1, v2)

    with pytest.raises(ValueError, match="dimensions do not match"):
        mem.unbind(v1, v2)

    with pytest.raises(ValueError, match="Cannot bundle empty"):
        mem.bundle([])
