"""Research Console vNext framework-neutral application boundary.

LOCAL READ-ONLY APPLICATION ONLY. This namespace grants no active market,
selector, Validation, publication, probability, risk, exposure, trading,
execution authority or agent-write authority. It may project only authority
already owned by upstream OVC programmes and must fail closed when a lawful
current-generation read model is unavailable.
"""

from .application.models import Availability, Blocker, ConsoleResource, SourceIdentity

__all__ = ["Availability", "Blocker", "ConsoleResource", "SourceIdentity"]
