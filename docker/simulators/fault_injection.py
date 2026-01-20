#!/usr/bin/env python3
"""
Configurable Fault Injection for NIGHTWATCH Simulators (Step 523)

Provides a framework for injecting faults into simulator behavior for testing
error handling and recovery mechanisms.

Fault Types:
- Communication faults (timeout, disconnect, corrupt data)
- Device faults (stuck, error response, out of range)
- Timing faults (delay, intermittent)
- Environmental faults (weather events, power issues)

Usage:
    from fault_injection import FaultInjector, FaultType

    injector = FaultInjector()
    injector.enable_fault(FaultType.TIMEOUT, probability=0.1)

    # In simulator code:
    if injector.should_inject(FaultType.TIMEOUT):
        raise TimeoutError("Simulated timeout")
"""

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of faults that can be injected."""
    # Communication faults
    TIMEOUT = "timeout"                     # Response timeout
    DISCONNECT = "disconnect"               # Connection dropped
    CORRUPT_DATA = "corrupt_data"           # Garbled response
    PARTIAL_RESPONSE = "partial_response"   # Incomplete response

    # Device faults
    DEVICE_ERROR = "device_error"           # Device returns error
    DEVICE_BUSY = "device_busy"             # Device reports busy
    STUCK = "stuck"                         # Device doesn't respond to commands
    OUT_OF_RANGE = "out_of_range"           # Values outside normal range

    # Timing faults
    DELAY = "delay"                         # Slow response
    INTERMITTENT = "intermittent"           # Random failures

    # Environmental faults
    WEATHER_EVENT = "weather_event"         # Rain/wind event
    POWER_GLITCH = "power_glitch"           # Brief power interruption
    SENSOR_NOISE = "sensor_noise"           # Noisy sensor readings


@dataclass
class FaultConfig:
    """Configuration for a specific fault type."""
    enabled: bool = False
    probability: float = 0.0                # 0.0 to 1.0
    duration_sec: float = 0.0               # How long fault lasts
    delay_sec: float = 0.0                  # Delay before response
    error_code: Optional[str] = None        # Error code to return
    custom_data: Dict[str, Any] = field(default_factory=dict)

    # Timing constraints
    start_time: Optional[datetime] = None   # When fault becomes active
    end_time: Optional[datetime] = None     # When fault expires
    cooldown_sec: float = 0.0               # Min time between fault triggers
    max_occurrences: int = -1               # Max times to trigger (-1 = unlimited)

    # State tracking
    occurrence_count: int = 0
    last_triggered: Optional[datetime] = None


class FaultInjector:
    """
    Configurable fault injection system for testing (Step 523).

    Allows simulators to inject various faults for testing error handling,
    recovery mechanisms, and safety systems.

    Example:
        injector = FaultInjector()

        # Enable random timeouts with 10% probability
        injector.enable_fault(FaultType.TIMEOUT, probability=0.1)

        # Enable delayed responses
        injector.enable_fault(FaultType.DELAY, delay_sec=2.0, probability=0.2)

        # In simulator code:
        if injector.should_inject(FaultType.TIMEOUT):
            raise TimeoutError("Simulated timeout")
    """

    def __init__(self):
        """Initialize fault injector."""
        self._faults: Dict[FaultType, FaultConfig] = {
            fault_type: FaultConfig() for fault_type in FaultType
        }
        self._enabled = True
        self._callbacks: List[Callable] = []

        # Load configuration from environment
        self._load_env_config()

    def _load_env_config(self):
        """Load fault configuration from environment variables."""
        # Format: FAULT_<TYPE>_ENABLED=true
        #         FAULT_<TYPE>_PROBABILITY=0.1
        #         FAULT_<TYPE>_DELAY=2.0

        for fault_type in FaultType:
            prefix = f"FAULT_{fault_type.name}"

            enabled = os.environ.get(f"{prefix}_ENABLED", "").lower() == "true"
            probability = float(os.environ.get(f"{prefix}_PROBABILITY", "0"))
            delay = float(os.environ.get(f"{prefix}_DELAY", "0"))

            if enabled or probability > 0:
                self.enable_fault(
                    fault_type,
                    probability=probability,
                    delay_sec=delay
                )
                logger.info(f"Loaded fault config from env: {fault_type.name} "
                           f"(prob={probability}, delay={delay})")

    @property
    def enabled(self) -> bool:
        """Check if fault injection is enabled globally."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable all fault injection."""
        self._enabled = enabled
        logger.info(f"Fault injection {'enabled' if enabled else 'disabled'}")

    def enable_fault(
        self,
        fault_type: FaultType,
        probability: float = 1.0,
        duration_sec: float = 0.0,
        delay_sec: float = 0.0,
        error_code: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        cooldown_sec: float = 0.0,
        max_occurrences: int = -1,
        **custom_data
    ):
        """
        Enable a fault type with configuration.

        Args:
            fault_type: Type of fault to enable
            probability: Probability of fault occurring (0.0-1.0)
            duration_sec: How long the fault condition lasts
            delay_sec: Delay before fault effect
            error_code: Error code to return when fault triggers
            start_time: When fault becomes active
            end_time: When fault expires
            cooldown_sec: Minimum time between triggers
            max_occurrences: Maximum number of times to trigger
            **custom_data: Additional fault-specific data
        """
        self._faults[fault_type] = FaultConfig(
            enabled=True,
            probability=max(0.0, min(1.0, probability)),
            duration_sec=duration_sec,
            delay_sec=delay_sec,
            error_code=error_code,
            start_time=start_time,
            end_time=end_time,
            cooldown_sec=cooldown_sec,
            max_occurrences=max_occurrences,
            custom_data=custom_data
        )
        logger.info(f"Enabled fault: {fault_type.name} (prob={probability})")

    def disable_fault(self, fault_type: FaultType):
        """Disable a specific fault type."""
        self._faults[fault_type].enabled = False
        logger.info(f"Disabled fault: {fault_type.name}")

    def disable_all(self):
        """Disable all faults."""
        for fault_type in FaultType:
            self._faults[fault_type].enabled = False
        logger.info("All faults disabled")

    def reset(self):
        """Reset all fault configurations and counters."""
        self._faults = {
            fault_type: FaultConfig() for fault_type in FaultType
        }
        logger.info("Fault injector reset")

    def should_inject(self, fault_type: FaultType) -> bool:
        """
        Check if a fault should be injected.

        Args:
            fault_type: Type of fault to check

        Returns:
            True if fault should be injected
        """
        if not self._enabled:
            return False

        config = self._faults[fault_type]
        if not config.enabled:
            return False

        now = datetime.now()

        # Check time constraints
        if config.start_time and now < config.start_time:
            return False
        if config.end_time and now > config.end_time:
            return False

        # Check cooldown
        if config.last_triggered and config.cooldown_sec > 0:
            elapsed = (now - config.last_triggered).total_seconds()
            if elapsed < config.cooldown_sec:
                return False

        # Check max occurrences
        if config.max_occurrences >= 0 and config.occurrence_count >= config.max_occurrences:
            return False

        # Random probability check
        if random.random() > config.probability:
            return False

        # Fault triggered
        config.occurrence_count += 1
        config.last_triggered = now

        logger.warning(f"FAULT INJECTED: {fault_type.name} (count={config.occurrence_count})")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(fault_type, config)
            except Exception as e:
                logger.error(f"Fault callback error: {e}")

        return True

    def get_fault_config(self, fault_type: FaultType) -> FaultConfig:
        """Get configuration for a fault type."""
        return self._faults[fault_type]

    def get_delay(self, fault_type: FaultType) -> float:
        """Get delay value for a fault type."""
        return self._faults[fault_type].delay_sec

    def get_error_code(self, fault_type: FaultType) -> Optional[str]:
        """Get error code for a fault type."""
        return self._faults[fault_type].error_code

    async def apply_delay(self, fault_type: FaultType):
        """Apply delay if fault is triggered."""
        if self.should_inject(FaultType.DELAY):
            delay = self._faults[fault_type].delay_sec
            if delay > 0:
                logger.debug(f"Applying {delay}s delay for {fault_type.name}")
                await asyncio.sleep(delay)

    def corrupt_string(self, data: str, corruption_rate: float = 0.1) -> str:
        """
        Corrupt a string by randomly modifying characters.

        Args:
            data: String to corrupt
            corruption_rate: Fraction of characters to corrupt

        Returns:
            Corrupted string
        """
        if not self.should_inject(FaultType.CORRUPT_DATA):
            return data

        chars = list(data)
        num_corrupt = max(1, int(len(chars) * corruption_rate))

        for _ in range(num_corrupt):
            if chars:
                idx = random.randint(0, len(chars) - 1)
                chars[idx] = chr(random.randint(32, 126))

        return ''.join(chars)

    def add_noise(self, value: float, noise_level: float = 0.1) -> float:
        """
        Add noise to a numeric value.

        Args:
            value: Original value
            noise_level: Standard deviation as fraction of value

        Returns:
            Value with noise added
        """
        if not self.should_inject(FaultType.SENSOR_NOISE):
            return value

        noise = random.gauss(0, abs(value * noise_level))
        return value + noise

    def register_callback(self, callback: Callable):
        """Register callback for fault events."""
        self._callbacks.append(callback)

    def get_status(self) -> Dict[str, Any]:
        """Get current fault injection status."""
        active_faults = []
        for fault_type, config in self._faults.items():
            if config.enabled:
                active_faults.append({
                    "type": fault_type.name,
                    "probability": config.probability,
                    "occurrences": config.occurrence_count,
                    "delay_sec": config.delay_sec
                })

        return {
            "enabled": self._enabled,
            "active_faults": active_faults,
            "total_injections": sum(c.occurrence_count for c in self._faults.values())
        }


# Global fault injector instance for shared use
_global_injector: Optional[FaultInjector] = None


def get_fault_injector() -> FaultInjector:
    """Get the global fault injector instance."""
    global _global_injector
    if _global_injector is None:
        _global_injector = FaultInjector()
    return _global_injector


def reset_fault_injector():
    """Reset the global fault injector."""
    global _global_injector
    if _global_injector:
        _global_injector.reset()
    _global_injector = None


# Convenience functions for common fault scenarios
def simulate_network_issues(probability: float = 0.1, delay_sec: float = 2.0):
    """Configure network-related faults."""
    injector = get_fault_injector()
    injector.enable_fault(FaultType.TIMEOUT, probability=probability)
    injector.enable_fault(FaultType.DELAY, probability=probability, delay_sec=delay_sec)
    injector.enable_fault(FaultType.DISCONNECT, probability=probability * 0.5)


def simulate_device_errors(probability: float = 0.1):
    """Configure device error faults."""
    injector = get_fault_injector()
    injector.enable_fault(FaultType.DEVICE_ERROR, probability=probability, error_code="ERR")
    injector.enable_fault(FaultType.DEVICE_BUSY, probability=probability)


def simulate_weather_event(duration_sec: float = 60.0):
    """Trigger a simulated weather event."""
    injector = get_fault_injector()
    injector.enable_fault(
        FaultType.WEATHER_EVENT,
        probability=1.0,
        duration_sec=duration_sec,
        end_time=datetime.now() + timedelta(seconds=duration_sec)
    )


# Main for testing
if __name__ == "__main__":
    print("Fault Injection Test\n")

    injector = FaultInjector()

    # Enable some faults
    injector.enable_fault(FaultType.TIMEOUT, probability=0.3)
    injector.enable_fault(FaultType.DELAY, probability=0.5, delay_sec=1.0)
    injector.enable_fault(FaultType.SENSOR_NOISE, probability=0.8)

    print("Testing fault injection:")

    # Test timeout
    for i in range(10):
        if injector.should_inject(FaultType.TIMEOUT):
            print(f"  [{i}] TIMEOUT triggered")
        else:
            print(f"  [{i}] Normal operation")

    # Test noise
    print("\nTesting noise injection:")
    value = 100.0
    for i in range(5):
        noisy = injector.add_noise(value, noise_level=0.05)
        print(f"  Original: {value}, Noisy: {noisy:.2f}")

    # Status
    print("\nFault injector status:")
    status = injector.get_status()
    print(f"  Total injections: {status['total_injections']}")
    for fault in status['active_faults']:
        print(f"  - {fault['type']}: prob={fault['probability']}, count={fault['occurrences']}")
