"""
MODELISE Geo-Compliance Policy Engine.

A standalone service, deliberately separate from Layer 2 (guardrail_layer2),
that manages multiple independent, named policy packs (typically one per
country or regulatory regime). Each pack gets its own FAISS index, built
once when the pack's CSV/PDF is uploaded and reused for every evaluation
after that - uploading a new pack never touches, rebuilds, or re-embeds any
other pack. Packs are individually toggleable, so any pipeline in the
orchestrator can attach or detach a specific country's rules without
affecting the others.
"""

__version__ = "1.0.0"
