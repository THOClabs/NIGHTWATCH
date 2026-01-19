"""
Encoder service for high-resolution position feedback.

This module provides interface to EncoderBridge hardware for absolute
encoder readings used to correct harmonic drive periodic error and backlash.
"""

from .encoder_bridge import EncoderBridge, EncoderPosition

__all__ = ["EncoderBridge", "EncoderPosition"]
