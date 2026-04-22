from typing_extensions import TypedDict


class HealthResponse(TypedDict):
    healthy: bool
    externals: dict[str, bool]
