class RingWatchError(Exception):
    """Base RingWatch exception."""


class ResourceNotFoundError(RingWatchError):
    """Requested resource does not exist."""


class DataValidationError(RingWatchError):
    """Processed data failed validation."""


class LLMServiceError(RingWatchError):
    """LLM service failed."""


class AddressResolutionError(RingWatchError):
    """Address could not be resolved."""