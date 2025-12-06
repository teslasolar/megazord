"""
Megazord Hash Functions
Deterministic 8-character identifiers for entities
"""

import hashlib
import time
import uuid


def H(gpu_id: int | str) -> str:
    """
    Generate GPU hash.

    Args:
        gpu_id: GPU device index or unique identifier

    Returns:
        8-character hash string
    """
    return hashlib.md5(f"gpu:{gpu_id}".encode()).hexdigest()[:8]


def M(model_name: str) -> str:
    """
    Generate Model hash.

    Args:
        model_name: Model name/path

    Returns:
        8-character hash string
    """
    return hashlib.md5(f"mdl:{model_name}".encode()).hexdigest()[:8]


def R(request_data: str = "") -> str:
    """
    Generate Request hash.
    Includes timestamp for uniqueness.

    Args:
        request_data: Optional request identifier/data

    Returns:
        8-character hash string
    """
    return hashlib.md5(f"req:{time.time()}:{request_data}:{uuid.uuid4().hex[:8]}".encode()).hexdigest()[:8]


def B(batch_id: str = "") -> str:
    """
    Generate Batch hash.

    Args:
        batch_id: Optional batch identifier

    Returns:
        8-character hash string
    """
    return hashlib.md5(f"bat:{time.time()}:{batch_id}".encode()).hexdigest()[:8]


def A(alarm_tag: str, timestamp: float | None = None) -> str:
    """
    Generate Alarm instance hash.

    Args:
        alarm_tag: Alarm tag name
        timestamp: Optional timestamp (uses current if not provided)

    Returns:
        8-character hash string
    """
    ts = timestamp or time.time()
    return hashlib.md5(f"alm:{alarm_tag}:{ts}".encode()).hexdigest()[:8]
