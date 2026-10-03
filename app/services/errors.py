class ExternalServiceError(RuntimeError):
    """A configured upstream service failed or returned an invalid response."""

    def __init__(self, service: str, operation: str = "request") -> None:
        self.service = service
        self.operation = operation
        super().__init__(f"{service} {operation} failed")


class CampaignNotFound(LookupError):
    """Raised when a requested campaign does not exist."""
