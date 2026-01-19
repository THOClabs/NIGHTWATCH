"""
NIGHTWATCH Custom Exceptions

Provides domain-specific exception hierarchy for the NIGHTWATCH observatory
control system. These exceptions enable targeted error handling and provide
clearer error messages than generic Python exceptions.

Exception Hierarchy:
    NightwatchError (base)
    ├── ConfigurationError
    ├── ConnectionError
    │   ├── DeviceConnectionError
    │   └── ServiceConnectionError
    ├── DeviceError
    │   ├── DeviceNotReadyError
    │   ├── DeviceBusyError
    │   └── DeviceTimeoutError
    ├── SafetyError
    │   ├── SafetyVetoError
    │   └── SafetyInterlockError
    ├── CommandError
    │   ├── InvalidCommandError
    │   └── CommandTimeoutError
    └── CatalogError
        └── ObjectNotFoundError
"""

from typing import Any, Optional, Sequence


class NightwatchError(Exception):
    """Base exception for all NIGHTWATCH errors.

    All NIGHTWATCH-specific exceptions inherit from this class, allowing
    callers to catch all NIGHTWATCH errors with a single except clause.

    Attributes:
        message: Human-readable error description
        details: Optional dict with additional error context
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(NightwatchError):
    """Error in configuration file or settings.

    Raised when configuration validation fails, required settings are missing,
    or configuration values are invalid.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
    ) -> None:
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details)
        self.config_key = config_key
        self.config_file = config_file


# =============================================================================
# Connection Errors
# =============================================================================

class NightwatchConnectionError(NightwatchError):
    """Base class for connection-related errors.

    Note: Named NightwatchConnectionError to avoid shadowing builtin
    ConnectionError.
    """
    pass


class DeviceConnectionError(NightwatchConnectionError):
    """Failed to connect to a hardware device.

    Raised when connection to telescope mount, camera, focuser, or other
    hardware device fails or is lost.
    """

    def __init__(
        self,
        message: str,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        details = {}
        if device_type:
            details["device_type"] = device_type
        if device_id:
            details["device_id"] = device_id
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        super().__init__(message, details)
        self.device_type = device_type
        self.device_id = device_id
        self.host = host
        self.port = port


class ServiceConnectionError(NightwatchConnectionError):
    """Failed to connect to a service (PHD2, INDI server, etc.).

    Raised when connection to external services fails.
    """

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        details = {}
        if service_name:
            details["service"] = service_name
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        super().__init__(message, details)
        self.service_name = service_name
        self.host = host
        self.port = port


# =============================================================================
# Device Errors
# =============================================================================

class DeviceError(NightwatchError):
    """Base class for device operation errors."""

    def __init__(
        self,
        message: str,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs
        if device_type:
            details["device_type"] = device_type
        if device_id:
            details["device_id"] = device_id
        super().__init__(message, details)
        self.device_type = device_type
        self.device_id = device_id


class DeviceNotReadyError(DeviceError):
    """Device is not ready for the requested operation.

    Raised when attempting an operation on a device that hasn't been
    initialized or connected.
    """
    pass


class DeviceBusyError(DeviceError):
    """Device is busy with another operation.

    Raised when attempting an operation while the device is already
    performing another task (e.g., focuser moving, camera capturing).
    """

    def __init__(
        self,
        message: str,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        current_operation: Optional[str] = None,
    ) -> None:
        super().__init__(message, device_type, device_id)
        if current_operation:
            self.details["current_operation"] = current_operation
        self.current_operation = current_operation


class DeviceTimeoutError(DeviceError):
    """Device operation timed out.

    Raised when a device operation exceeds its allowed time limit.
    """

    def __init__(
        self,
        message: str,
        device_type: Optional[str] = None,
        device_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
    ) -> None:
        super().__init__(message, device_type, device_id)
        if timeout_seconds is not None:
            self.details["timeout_seconds"] = timeout_seconds
        if operation:
            self.details["operation"] = operation
        self.timeout_seconds = timeout_seconds
        self.operation = operation


# =============================================================================
# Safety Errors
# =============================================================================

class SafetyError(NightwatchError):
    """Base class for safety-related errors.

    Safety errors indicate conditions that could potentially damage equipment
    or compromise observation safety.
    """
    pass


class SafetyVetoError(SafetyError):
    """Safety system vetoed an operation.

    Raised when the safety monitor blocks an operation due to environmental
    conditions (wind, humidity, etc.) or system state.
    """

    def __init__(
        self,
        message: str,
        vetoed_operation: Optional[str] = None,
        failed_conditions: Optional[Sequence[str]] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if vetoed_operation:
            details["vetoed_operation"] = vetoed_operation
        if failed_conditions:
            details["failed_conditions"] = list(failed_conditions)
        super().__init__(message, details)
        self.vetoed_operation = vetoed_operation
        self.failed_conditions = list(failed_conditions) if failed_conditions else []


class SafetyInterlockError(SafetyError):
    """Hardware safety interlock triggered.

    Raised when a physical safety interlock prevents operation
    (e.g., roof not open, telescope not parked for roof operation).
    """

    def __init__(
        self,
        message: str,
        interlock_name: Optional[str] = None,
        required_state: Optional[str] = None,
        current_state: Optional[str] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if interlock_name:
            details["interlock"] = interlock_name
        if required_state:
            details["required_state"] = required_state
        if current_state:
            details["current_state"] = current_state
        super().__init__(message, details)
        self.interlock_name = interlock_name
        self.required_state = required_state
        self.current_state = current_state


# =============================================================================
# Command Errors
# =============================================================================

class CommandError(NightwatchError):
    """Base class for command execution errors."""
    pass


class InvalidCommandError(CommandError):
    """Invalid or malformed command.

    Raised when a command cannot be parsed or has invalid parameters.
    """

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        parameter: Optional[str] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if command:
            details["command"] = command
        if parameter:
            details["parameter"] = parameter
        super().__init__(message, details)
        self.command = command
        self.parameter = parameter


class CommandTimeoutError(CommandError):
    """Command execution timed out.

    Raised when a command does not complete within the expected time.
    """

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if command:
            details["command"] = command
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, details)
        self.command = command
        self.timeout_seconds = timeout_seconds


# =============================================================================
# Catalog Errors
# =============================================================================

class CatalogError(NightwatchError):
    """Base class for catalog-related errors."""
    pass


class ObjectNotFoundError(CatalogError):
    """Celestial object not found in catalog.

    Raised when a requested object cannot be found by name or identifier.
    """

    def __init__(
        self,
        message: str,
        object_name: Optional[str] = None,
        catalog: Optional[str] = None,
    ) -> None:
        details: dict[str, Any] = {}
        if object_name:
            details["object_name"] = object_name
        if catalog:
            details["catalog"] = catalog
        super().__init__(message, details)
        self.object_name = object_name
        self.catalog = catalog


# =============================================================================
# Convenience aliases
# =============================================================================

# Allow importing without prefix for common cases
Error = NightwatchError
ConnectionErr = NightwatchConnectionError
