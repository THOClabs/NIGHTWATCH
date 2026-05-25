"""Unit tests for nightwatch.cancellation primitives (ARCH-003).

ARCH-003 introduces cooperative cancellation: a ``CancelToken`` carried by
a per-command ``CommandContext`` so safety transitions can abort in-flight
camera exposures / mount slews / autofocus runs WITHOUT relying on
``asyncio.Task.cancel`` (which lacks a ``reason`` field and crosses the
``await`` boundary in ways that mid-loop cleanup code finds surprising).

These tests pin the primitive's surface: cancel-once semantics, reason
preservation, ``raise_if_cancelled``, the ``wait_cancelled`` async event,
and the ``CommandContext`` wrapper that long-running handlers actually
receive.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from nightwatch.cancellation import (
    CancellationError,
    CancelToken,
    CommandContext,
)

# =============================================================================
# CancelToken
# =============================================================================


def test_cancel_token_is_not_cancelled_initially() -> None:
    token = CancelToken()
    assert token.is_cancelled() is False
    assert token.reason is None


def test_cancel_token_is_cancelled_after_cancel() -> None:
    token = CancelToken()
    token.cancel("rain detected")
    assert token.is_cancelled() is True
    assert token.reason == "rain detected"


def test_cancel_token_cancel_is_idempotent_first_reason_wins() -> None:
    """Cancel-once semantics: a second cancel() does NOT overwrite the reason.

    Safety transitions can fire repeatedly while the unsafe condition
    persists; we want the FIRST reason (the one a caller will surface to
    the user) to stick.
    """
    token = CancelToken()
    token.cancel("rain detected")
    token.cancel("wind")  # later transition — should be ignored
    assert token.reason == "rain detected"


def test_cancel_token_raise_if_cancelled_noop_when_not_cancelled() -> None:
    token = CancelToken()
    token.raise_if_cancelled()  # should not raise


def test_cancel_token_raise_if_cancelled_raises_with_reason() -> None:
    token = CancelToken()
    token.cancel("emergency_close")
    with pytest.raises(CancellationError) as excinfo:
        token.raise_if_cancelled()
    assert excinfo.value.reason == "emergency_close"
    assert "emergency_close" in str(excinfo.value)


async def test_cancel_token_wait_cancelled_fires() -> None:
    """``await token.wait_cancelled()`` resolves when cancel() is called.

    The classic pattern for select-style cancellation: race
    ``wait_cancelled`` against the long-running op.
    """
    token = CancelToken()

    async def fire_after(delay: float) -> None:
        await asyncio.sleep(delay)
        token.cancel("from fire_after")

    task = asyncio.create_task(fire_after(0.05))
    try:
        reason = await asyncio.wait_for(token.wait_cancelled(), timeout=1.0)
    finally:
        # Keep ruff happy (RUF006) AND make sure the test never leaks
        # a stray task if the assertion below ever changes shape.
        if not task.done():
            task.cancel()
    assert reason == "from fire_after"


async def test_cancel_token_wait_cancelled_resolves_immediately_if_already_cancelled() -> None:
    """No await-then-never if the token is already in the cancelled state."""
    token = CancelToken()
    token.cancel("pre-cancelled")
    reason = await asyncio.wait_for(token.wait_cancelled(), timeout=0.5)
    assert reason == "pre-cancelled"


# =============================================================================
# CommandContext
# =============================================================================


def test_command_context_defaults_to_active_token() -> None:
    ctx = CommandContext(command_id="cmd_001")
    assert ctx.command_id == "cmd_001"
    assert ctx.is_cancelled() is False
    assert ctx.token.is_cancelled() is False


def test_command_context_cancel_delegates_to_token() -> None:
    ctx = CommandContext(command_id="cmd_002")
    ctx.cancel("safety:EMERGENCY_CLOSE")
    assert ctx.is_cancelled() is True
    assert ctx.token.is_cancelled() is True
    assert ctx.token.reason == "safety:EMERGENCY_CLOSE"


def test_command_context_new_factory_generates_unique_ids() -> None:
    """``CommandContext.new()`` is the standard constructor — uuid-based id."""
    a = CommandContext.new()
    b = CommandContext.new()
    assert a.command_id != b.command_id
    # ids should be parseable as UUID hex prefix (we don't pin the format
    # tightly — just that they look like correlation tokens).
    assert len(a.command_id) >= 8
    # Smoke: confirm the implementation actually uses uuid (defensive,
    # so future contributors don't switch to a global counter that
    # collides under concurrent commands).
    uuid.UUID(a.command_id)


def test_command_context_carries_optional_timeout() -> None:
    ctx = CommandContext(command_id="cmd_003", timeout_s=120.0)
    assert ctx.timeout_s == 120.0
