"""
Megazord Alarm Manager
ISA-18.2 Compliant Alarm System
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Awaitable, Any

from megazord.core.hash import A
from megazord.core.states import AlarmClass
from megazord.core.udts import UDT_Alarm

if TYPE_CHECKING:
    from megazord.core.schema import Database

logger = logging.getLogger(__name__)


@dataclass
class AlarmDefinition:
    """
    Alarm definition template.

    Defines the conditions under which an alarm should be raised.
    """

    tag: str                    # Unique tag name
    priority: AlarmClass        # Alarm priority
    message: str                # Message template (supports {value} placeholder)
    threshold: float            # Value threshold
    comparison: str = ">"       # Comparison operator: >, <, >=, <=, ==, !=
    deadband: float = 0.0       # Deadband for hysteresis
    enabled: bool = True        # Whether alarm is enabled

    def check(self, value: float) -> bool:
        """Check if value triggers this alarm."""
        if not self.enabled:
            return False

        ops = {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: v == t,
            "!=": lambda v, t: v != t,
        }

        op = ops.get(self.comparison, ops[">"])
        return op(value, self.threshold)

    def format_message(self, value: float) -> str:
        """Format message with value."""
        return self.message.format(value=value)


# Default alarm definitions
DEFAULT_ALARMS: list[AlarmDefinition] = [
    # Temperature alarms (per-GPU, templated)
    AlarmDefinition(
        tag="GPU_Temp_Crit",
        priority=AlarmClass.CRIT,
        message="GPU critical temperature: {value}°C",
        threshold=90,
    ),
    AlarmDefinition(
        tag="GPU_Temp_Throt",
        priority=AlarmClass.HIGH,
        message="GPU throttling: {value}°C",
        threshold=83,
    ),
    AlarmDefinition(
        tag="GPU_Temp_Warn",
        priority=AlarmClass.MED,
        message="GPU temperature warning: {value}°C",
        threshold=75,
    ),
    # VRAM alarms
    AlarmDefinition(
        tag="GPU_VRAM_Low",
        priority=AlarmClass.MED,
        message="GPU VRAM low: {value}% used",
        threshold=90,
    ),
    # Router alarms
    AlarmDefinition(
        tag="RTR_Queue_Full",
        priority=AlarmClass.HIGH,
        message="Queue full: {value} requests",
        threshold=100,
    ),
    AlarmDefinition(
        tag="RTR_Queue_Warn",
        priority=AlarmClass.MED,
        message="Queue warning: {value} requests",
        threshold=80,
    ),
    AlarmDefinition(
        tag="RTR_Timeout",
        priority=AlarmClass.HIGH,
        message="Request timeout: {value}ms",
        threshold=300000,
    ),
    # Model alarms
    AlarmDefinition(
        tag="MDL_Load_Fail",
        priority=AlarmClass.HIGH,
        message="Model load failed",
        threshold=1,
    ),
    AlarmDefinition(
        tag="MDL_VRAM_Insuff",
        priority=AlarmClass.MED,
        message="Insufficient VRAM for model: {value}MB needed",
        threshold=0,
        comparison="<",
    ),
]


class AlarmManager:
    """
    Alarm manager with shelving, acknowledgement, and persistence.
    """

    def __init__(self, db: "Database | None" = None):
        self.db = db
        self._definitions: dict[str, AlarmDefinition] = {}
        self._active: dict[str, UDT_Alarm] = {}
        self._shelved: set[str] = set()  # Shelved alarm tags
        self._callbacks: list[Callable[[UDT_Alarm], Awaitable[None]]] = []

        # Load default definitions
        for defn in DEFAULT_ALARMS:
            self.register(defn)

    def register(self, defn: AlarmDefinition) -> None:
        """Register an alarm definition."""
        self._definitions[defn.tag] = defn

    def unregister(self, tag: str) -> None:
        """Unregister an alarm definition."""
        if tag in self._definitions:
            del self._definitions[tag]

    def get_definition(self, tag: str) -> AlarmDefinition | None:
        """Get alarm definition by tag."""
        return self._definitions.get(tag)

    def add_callback(self, callback: Callable[[UDT_Alarm], Awaitable[None]]) -> None:
        """Add alarm callback."""
        self._callbacks.append(callback)

    async def check(self, tag: str, value: float) -> UDT_Alarm | None:
        """
        Check if a value triggers an alarm.

        Returns the alarm instance if triggered, None otherwise.
        """
        defn = self._definitions.get(tag)
        if not defn:
            return None

        if tag in self._shelved:
            return None

        if not defn.check(value):
            # Value is OK - check if we should clear an existing alarm
            if tag in self._active:
                # Apply deadband before clearing
                active = self._active[tag]
                if abs(value - defn.threshold) > defn.deadband:
                    await self.clear(tag)
            return None

        # Check if alarm already active
        if tag in self._active:
            return self._active[tag]

        # Raise new alarm
        alarm = UDT_Alarm(
            h=A(tag),
            tag=tag,
            priority=defn.priority,
            message=defn.format_message(value),
            t_raised=int(time.time()),
            value=value,
        )

        self._active[tag] = alarm

        # Persist
        if self.db:
            await self.db.insert_alarm(alarm)

        # Trigger callbacks
        for callback in self._callbacks:
            try:
                await callback(alarm)
            except Exception as e:
                logger.error(f"Alarm callback error: {e}")

        logger.warning(f"ALARM [{alarm.priority}] {alarm.tag}: {alarm.message}")

        return alarm

    async def raise_alarm(
        self,
        tag: str,
        message: str,
        priority: AlarmClass = AlarmClass.MED,
        value: float = 0.0,
    ) -> UDT_Alarm:
        """Raise an alarm directly (without definition check)."""
        if tag in self._shelved:
            return None

        alarm = UDT_Alarm(
            h=A(tag),
            tag=tag,
            priority=priority,
            message=message,
            t_raised=int(time.time()),
            value=value,
        )

        self._active[tag] = alarm

        if self.db:
            await self.db.insert_alarm(alarm)

        for callback in self._callbacks:
            try:
                await callback(alarm)
            except Exception as e:
                logger.error(f"Alarm callback error: {e}")

        logger.warning(f"ALARM [{priority.label}] {tag}: {message}")

        return alarm

    async def acknowledge(self, tag: str, ack_by: str = "") -> bool:
        """Acknowledge an active alarm."""
        if tag not in self._active:
            return False

        alarm = self._active[tag]
        alarm.t_ack = int(time.time())
        alarm.ack_by = ack_by

        if self.db:
            await self.db.ack_alarm(alarm.h, ack_by)

        logger.info(f"ALARM ACK: {tag} by {ack_by or 'system'}")
        return True

    async def clear(self, tag: str) -> bool:
        """Clear an alarm."""
        if tag not in self._active:
            return False

        alarm = self._active[tag]
        alarm.t_cleared = int(time.time())

        if self.db:
            await self.db.clear_alarm(alarm.h)

        del self._active[tag]

        logger.info(f"ALARM CLEAR: {tag}")
        return True

    def shelve(self, tag: str) -> None:
        """Shelve an alarm (suppress temporarily)."""
        self._shelved.add(tag)
        logger.info(f"ALARM SHELVED: {tag}")

    def unshelve(self, tag: str) -> None:
        """Unshelve an alarm."""
        self._shelved.discard(tag)
        logger.info(f"ALARM UNSHELVED: {tag}")

    @property
    def active_alarms(self) -> list[UDT_Alarm]:
        """Get all active alarms."""
        return list(self._active.values())

    @property
    def active_count(self) -> int:
        """Get count of active alarms."""
        return len(self._active)

    def get_active_by_priority(self, priority: AlarmClass) -> list[UDT_Alarm]:
        """Get active alarms by priority."""
        return [a for a in self._active.values() if a.priority == priority]

    async def clear_all(self) -> int:
        """Clear all active alarms. Returns count cleared."""
        count = len(self._active)
        for tag in list(self._active.keys()):
            await self.clear(tag)
        return count
