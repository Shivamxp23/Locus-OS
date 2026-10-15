import pytest
import numpy as np
from sidecar.memory.hrr import (
    HRRVector,
    Codebook,
    bind,
    unbind,
    bundle,
    cleanup,
    cosine_similarity,
    encode_ephemeral_state,
    decode_ephemeral_state,
    HolographicMemory,
)


def test_codebook_and_normalization():
    cb = Codebook(dim=1024, seed=42)
    v1 = cb.get_or_create("SYM_A")
    assert v1.dim == 1024
    assert pytest.approx(v1.norm(), rel=1e-4) == 1.0


def test_circular_convolution_bind_unbind_exact():
    cb = Codebook(dim=2048, seed=123)
    role = cb.get_or_create("AGENT_ROLE")
    filler = cb.get_or_create("CODER")

    bound = bind(role, filler)
    assert pytest.approx(bound.norm(), rel=1e-4) == 1.0

    # Unbind with role should recover filler with high cosine similarity
    recovered = unbind(bound, role)
    sim = cosine_similarity(recovered.values, filler.values)
    assert sim > 0.40  # In HRR D=2048, correlation unbind typically yields sim > 0.5

    # Cleanup against codebook matches filler
    matched = cleanup(recovered, cb, threshold=0.30)
    assert matched == "CODER"


def test_ephemeral_state_encoding_and_decoding():
    mem = HolographicMemory(dim=2048, seed=999)
    mem.store_state(
        state_id="state_turn_1",
        current_task="implement_hrr",
        active_mode="FLOW",
        stress_level="LOW",
    )

    task_res = mem.query_state_attribute("state_turn_1", "TASK")
    mode_res = mem.query_state_attribute("state_turn_1", "MODE")
    stress_res = mem.query_state_attribute("state_turn_1", "STRESS")

    assert task_res == "implement_hrr"
    assert mode_res == "FLOW"
    assert stress_res == "LOW"


def test_cosine_similarity_edge_cases():
    zero = np.zeros(10)
    v = np.ones(10)
    assert cosine_similarity(zero, v) == 0.0
