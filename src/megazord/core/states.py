"""
Megazord State Machines
PackML Compliant State Definitions
"""

from enum import IntEnum


class ST(IntEnum):
    """
    GPU/Equipment Status States (PackML-inspired)

    State Transitions:
        OFFLINE -> STARTING (on scan)
        STARTING -> READY (on init complete)
        READY -> BUSY (on request)
        BUSY -> READY (on complete)
        READY/BUSY -> THROTTLE (on thermal)
        THROTTLE -> READY (on thermal clear + hysteresis)
        ANY -> ERROR (on fault)
        ERROR -> OFFLINE (on reset)
    """

    OFF = 0       # Offline / Not available
    STARTING = 1  # Initializing
    READY = 2     # Available for work
    BUSY = 3      # Processing request
    THROTTLE = 4  # Thermal throttling
    ERROR = 5     # Fault state

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            ST.OFF: "Offline",
            ST.STARTING: "Starting",
            ST.READY: "Ready",
            ST.BUSY: "Busy",
            ST.THROTTLE: "Throttle",
            ST.ERROR: "Error",
        }[self]

    @property
    def color(self) -> str:
        """ISA-101 color code."""
        return {
            ST.OFF: "#6B7280",      # Gray
            ST.STARTING: "#F59E0B", # Yellow
            ST.READY: "#22C55E",    # Green
            ST.BUSY: "#06B6D4",     # Cyan
            ST.THROTTLE: "#F59E0B", # Yellow
            ST.ERROR: "#EF4444",    # Red
        }[self]


class RS(IntEnum):
    """
    Request Status States

    State Transitions:
        QUEUED -> RUNNING (on dispatch)
        RUNNING -> DONE (on complete)
        RUNNING -> ERROR (on fault)
        QUEUED -> ERROR (on timeout)
    """

    QUEUED = 0   # Waiting in queue
    RUNNING = 1  # Currently executing
    DONE = 2     # Successfully completed
    ERROR = 3    # Failed

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            RS.QUEUED: "Queued",
            RS.RUNNING: "Running",
            RS.DONE: "Done",
            RS.ERROR: "Error",
        }[self]


class RM(IntEnum):
    """
    Router Balance Mode

    SPEED: Prefer fastest available GPU
    VRAM: Prefer GPU with most available VRAM
    ROUND_ROBIN: Distribute evenly
    """

    SPEED = 0
    VRAM = 1
    ROUND_ROBIN = 2

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            RM.SPEED: "Speed",
            RM.VRAM: "VRAM",
            RM.ROUND_ROBIN: "Round Robin",
        }[self]


class RTR_ST(IntEnum):
    """
    Router State Machine (PackML)

    State Transitions:
        IDLE -> STARTING (on start cmd)
        STARTING -> EXECUTE (on ready)
        EXECUTE -> HELD (on hold cmd)
        HELD -> EXECUTE (on resume)
        EXECUTE -> STOPPING (on stop cmd)
        STOPPING -> IDLE (on stopped)
    """

    IDLE = 0
    STARTING = 1
    EXECUTE = 2
    HELD = 3
    STOPPING = 4

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            RTR_ST.IDLE: "Idle",
            RTR_ST.STARTING: "Starting",
            RTR_ST.EXECUTE: "Execute",
            RTR_ST.HELD: "Held",
            RTR_ST.STOPPING: "Stopping",
        }[self]


class AlarmClass(IntEnum):
    """
    Alarm Priority Classes (ISA-18.2)
    """

    CRIT = 1   # Critical - Auto-shutdown
    HIGH = 2   # High - Alert + pause
    MED = 3    # Medium - Warning
    LOW = 4    # Low - Info

    @property
    def label(self) -> str:
        """Human-readable label."""
        return {
            AlarmClass.CRIT: "Critical",
            AlarmClass.HIGH: "High",
            AlarmClass.MED: "Medium",
            AlarmClass.LOW: "Low",
        }[self]

    @property
    def color(self) -> str:
        """ISA-101 color code."""
        return {
            AlarmClass.CRIT: "#EF4444",  # Red
            AlarmClass.HIGH: "#F97316",  # Orange
            AlarmClass.MED: "#F59E0B",   # Yellow
            AlarmClass.LOW: "#06B6D4",   # Cyan
        }[self]
