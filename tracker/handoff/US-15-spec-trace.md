# US-15 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| Errata D-13 Option a | "Sidecar on the VM binds strictly to loopback 127.0.0.1:8420. The local computer reaches it over an SSH tunnel (ssh -N -L 8420:127.0.0.1:8420 user@vm). No mTLS, no tokens, no open HTTP/HTTPS port on 0.0.0.0." | LOCUS-NEW | locus_cli/tunnel.py:27-142, locus_cli/install.py:231-250, 405-420 | tests/unit/test_tunnel.py::test_build_ssh_command_flags, tests/integration/test_hybrid_tunnel.py::test_hybrid_tunnel_cross_boundary_communication |
| 10-security.md | "sidecar/service.py binds only to loopback 127.0.0.1:8420 on VM, never exposing plain HTTP on 0.0.0.0 (10-security.md)." | LOCUS-NEW | sidecar/service.py:104-110, 158-164 | tests/integration/test_hybrid_tunnel.py::test_service_refuses_binding_to_public_0000 |
| User requirement demo | "Run hybrid tunnel test: asserts sidecar binds to loopback, tunnel helper establishes port forwarding, and local client communicates with remote sidecar endpoint." | LOCUS-NEW | tests/integration/test_hybrid_tunnel.py | tests/integration/test_hybrid_tunnel.py::test_hybrid_tunnel_cross_boundary_communication |
