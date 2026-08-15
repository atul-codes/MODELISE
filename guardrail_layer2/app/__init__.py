"""
MODELISE Layer 2 - Custom Organizational Policy Enforcement, Semantic
Token-Burn Exploit Defense, and Local LLM Orchestration Engine.

This package sits behind Layer 1 (baseline security / prompt-injection
screening / edge validation) and in front of a locally-hosted generation
model (Ollama / any OpenAI-compatible endpoint). It never talks to the
public internet for inference - everything runs on local hardware.
"""

__version__ = "1.0.0"
