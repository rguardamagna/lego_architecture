"""Route table and resolution for the API Gateway."""

# Module-level route map: {prefix: target_base_url}
# e.g. {"/api/v1/auth/": "http://auth:8000"}
ROUTE_PREFIX_MAP: dict[str, str] = {}


def init_routes(route_map: dict[str, str]) -> None:
    """Build ROUTE_PREFIX_MAP from a dict of {NAME: target_url}.

    Each NAME becomes prefix /api/v1/<lowercase_name>/.
    """
    ROUTE_PREFIX_MAP.clear()
    for name, target in route_map.items():
        prefix = f"/api/v1/{name.lower()}/"
        ROUTE_PREFIX_MAP[prefix] = target.rstrip("/")


def find_route(path: str) -> tuple[str, str] | None:
    """Find the best matching route for a path.

    Uses longest prefix match. Returns (target_base_url, remaining_path)
    or None if no route matches.
    """
    if not path:
        return None

    # Normalize: ensure trailing slash for prefix matching
    normalized = path if path.endswith("/") else path + "/"

    best_prefix = ""
    best_target = ""
    for prefix, target in ROUTE_PREFIX_MAP.items():
        if normalized.startswith(prefix) and len(prefix) > len(best_prefix):
            best_prefix = prefix
            best_target = target

    if not best_prefix:
        return None

    # Calculate remaining path (preserve query string)
    remaining = path[len(best_prefix.rstrip("/")):]
    if not remaining:
        remaining = ""
    return best_target, remaining
