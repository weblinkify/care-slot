"""Mock identity provider - LOCAL / TEST / DEMO ONLY.

Stands in for a real OIDC provider (e.g. Suomi.fi or an enterprise IdP) so the system can be
run and demonstrated without external dependencies. It is not a bounded context and is never
mounted when CARESLOT_ENVIRONMENT=production (tested). The API itself only verifies tokens;
swapping this for a real IdP means changing configuration, not code (ADR-0006).
"""
