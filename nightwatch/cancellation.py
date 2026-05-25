"""Cooperative cancellation primitives (ARCH-003).

Risk #2 from the Phase 1 audit: if SafetyMonitor flips unsafe
(rain detected, wind over limit, etc.) the safety subsystem closes the
roof — but there's no documented way to abort the in-flight camera
exposure or mount slew BEFORE the enclosure starts moving. ARCH-003
introduces ``CancelToken`` and ``CommandContext`` so long-running ops
(``_capture_loop``, slew, autofocus, plate-solve) can opt into a
cheap, cooperative cancellation check at safe iteration boundaries.

Why cooperative rather than ``asyncio.Task.cancel``:

  * ``Task.cancel`` injects ``CancelledError`` at an arbitrary ``await``
    point. Camera FITS-write code and mount serial transactions need to
    finish atomically; surprise cancellation mid-write produces corrupt
    files and confused hardware state.
  * ``CancelledError`` carries no human-readable reason. Safety
    cancellation needs a *why* ("rain detected", "wind over 35 mph") to
    surface to the user via the voice response formatter.
  * ``Task.cancel`` cannot be inspected pre-fact ("was I cancelled?")
    without trapping the exception — awkward for loop bodies that want
    to check at the iteration boundary.

The primitive is deliberately tiny: a one-shot boolean + an
``asyncio.Event`` + a reason string. ``CommandContext`` adds a
correlation id (which intentionally overlaps with the ARCH-004
correlation-id work) and an optional ``timeout_s``.

SAFE-001 closes the loop: ``SafetyMonitor.run()`` was reordered so
``_notify_callbacks`` (which fires the orchestrator's cancel-on-unsafe
hook) runs BEFORE ``execute_action`` (which drives the roof on
EMERGENCY_CLOSE). The cancel signal therefore reaches in-flight
captures/slews before the irreversible enclosure-close, plus a
bounded ``_wait_for_cancellations_to_drain`` settle window gives
cooperative loops a chance to honor their token. See
``services/safety_monitor/monitor.py:run`` for the production caller
and ``tests/integration/test_safety_cancellation.py``
(``TestSafe001OrderingThroughRunLoop``) for the verify-line tests.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

__all__ = [
    "CancelToken",
    "CancellationError",
    "CommandContext",
]


class CancellationError(Exception):
    """Raised when ``CancelToken.raise_if_cancelled`` fires.

    The ``reason`` attribute carries the human-readable explanation that
    was passed to ``CancelToken.cancel``. Handlers should catch this
    near the top of their try/except and map it to a
    ``ToolStatus.CANCELLED`` result so downstream voice/log layers can
    distinguish "user/safety stopped this" from "this errored out".
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CancelToken:
    """A one-shot cooperative cancellation signal.

    Cheap to construct; safe to share across asyncio tasks (the
    ``asyncio.Event`` it wraps is the standard cross-task signalling
    primitive).

    Lifecycle:
      * Created in the *not cancelled* state.
      * ``cancel(reason)`` flips it to the cancelled state and stores
        the reason. Subsequent calls are no-ops (first reason wins).
      * Long-running callers either poll ``is_cancelled()`` /
        ``raise_if_cancelled()`` at iteration boundaries, or
        ``await wait_cancelled()`` in a select-style race.

    The token is NOT reusable — once cancelled, it stays cancelled.
    Each new command should create a fresh token (via
    ``CommandContext.new()`` or by passing one explicitly).
    """

    def __init__(self) -> None:
        self._cancelled: bool = False
        self._reason: str | None = None
        # Lazily constructed on first ``wait_cancelled`` access so
        # callers that only poll synchronously never pay the
        # event-loop-bound construction cost.
        self._event: asyncio.Event | None = None

    def cancel(self, reason: str) -> None:
        """Signal cancellation. First-call wins — later calls are ignored.

        Why first-call wins: safety transitions can fire repeatedly while
        the unsafe condition persists. The first reason is what the
        caller will surface to the user; later reasons would just churn
        log lines without adding information.
        """
        if self._cancelled:
            return
        self._cancelled = True
        self._reason = reason
        if self._event is not None:
            self._event.set()

    def is_cancelled(self) -> bool:
        """Return ``True`` once ``cancel`` has been called."""
        return self._cancelled

    @property
    def reason(self) -> str | None:
        """The reason passed to ``cancel``, or ``None`` if not cancelled."""
        return self._reason

    def raise_if_cancelled(self) -> None:
        """Raise ``CancellationError`` if the token is cancelled.

        The idiomatic check inside a long-running loop body. Place it
        immediately AFTER any side-effect that must complete atomically
        (e.g. after a FITS write returns) so partial work is not silently
        discarded.
        """
        if self._cancelled:
            assert self._reason is not None  # invariant: set together
            raise CancellationError(self._reason)

    async def wait_cancelled(self) -> str:
        """Block until ``cancel`` has been called; return the reason.

        Typical use:

            done, pending = await asyncio.wait(
                {asyncio.create_task(long_op()),
                 asyncio.create_task(token.wait_cancelled())},
                return_when=asyncio.FIRST_COMPLETED,
            )

        The event is constructed lazily on first call so the token
        remains usable from sync code that never needs the awaitable.
        """
        if self._event is None:
            self._event = asyncio.Event()
            if self._cancelled:
                # We were cancelled BEFORE anyone awaited — make sure the
                # event reflects that so ``wait`` returns immediately.
                self._event.set()
        await self._event.wait()
        # Invariant: ``_event.set()`` is only ever called inside
        # ``cancel`` (or the just-cancelled-pre-await branch above),
        # both of which set ``_reason``.
        assert self._reason is not None
        return self._reason


@dataclass
class CommandContext:
    """Per-command execution context.

    Carries the cancellation token plus the correlation id that
    ToolExecutor / Orchestrator use to tie log lines together across
    the voice → LLM → tool → service hop. The id space deliberately
    overlaps with ARCH-004 (correlation-id propagation) — ARCH-003
    establishes the shape; ARCH-004 will widen its consumers.

    ``timeout_s`` is informational — the wall-clock timeout currently
    lives on ``ToolExecutor.execute(timeout=...)``. Future work
    (ARCH-004 / OBS-*) may move it onto the context so deadline
    arithmetic survives service hops.
    """

    command_id: str
    token: CancelToken = field(default_factory=CancelToken)
    timeout_s: float | None = None

    @classmethod
    def new(cls, timeout_s: float | None = None) -> CommandContext:
        """Create a fresh context with a uuid4 hex correlation id.

        The standard constructor — direct ``CommandContext(command_id=...)``
        is for callers that want to thread an externally-supplied id
        (e.g. a request id from an upstream pipeline).
        """
        return cls(command_id=uuid.uuid4().hex, timeout_s=timeout_s)

    def cancel(self, reason: str) -> None:
        """Cancel the underlying token. Delegates so call sites stay terse."""
        self.token.cancel(reason)

    def is_cancelled(self) -> bool:
        """Return ``True`` if the underlying token is cancelled."""
        return self.token.is_cancelled()
