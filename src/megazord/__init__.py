"""
Megazord - Generic Local LLM Cluster
ISA-88/95/101 Compliant

"industry 4.0 calls it ERP, I call it Megazord"
"""

__version__ = "0.1.0"
__author__ = "Phoenix"

from megazord.core.params import Params, SysParams, ThermParams, RouterParams, ModelParams, RecipeParams
from megazord.core.udts import UDT_GPU, UDT_Model, UDT_Request
from megazord.core.states import ST, RS, RM
from megazord.core.hash import H, M, R
from megazord.core.router import Router
from megazord.megazord import Megazord

__all__ = [
    "Megazord",
    "Params",
    "SysParams",
    "ThermParams",
    "RouterParams",
    "ModelParams",
    "RecipeParams",
    "UDT_GPU",
    "UDT_Model",
    "UDT_Request",
    "ST",
    "RS",
    "RM",
    "H",
    "M",
    "R",
    "Router",
]
