from __future__ import annotations

from typing import Any

from control_plane.runtime import normalize_capabilities


def _policy_root(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("job_policy", {})


def default_job_type(config: dict[str, Any]) -> str:
    return _policy_root(config).get("default_job_type", "diagnostic")


def job_type_policy(config: dict[str, Any], job_type: str) -> dict[str, Any]:
    policies = _policy_root(config).get("job_types", {})
    if job_type not in policies:
        available = ", ".join(sorted(policies)) or "<none>"
        raise ValueError(f"Unknown job_type '{job_type}'. Available: {available}")
    return policies[job_type]


def available_job_types(config: dict[str, Any]) -> list[str]:
    return sorted(_policy_root(config).get("job_types", {}).keys())


def validate_job_command(config: dict[str, Any], job_type: str, command: str) -> None:
    policy = job_type_policy(config, job_type)
    command = command.strip()
    for prefix in policy.get("allowed_prefixes", []):
        if command == prefix or command.startswith(prefix + " "):
            return
    allowed = ", ".join(policy.get("allowed_prefixes", []))
    raise ValueError(
        f"Command '{command}' is not allowed for job_type '{job_type}'. "
        f"Allowed prefixes: {allowed}"
    )


def job_defaults(
    config: dict[str, Any],
    job_type: str,
    *,
    required_capabilities: list[str],
    approval_required: bool,
    preferred_node: str | None,
) -> tuple[list[str], bool, str | None]:
    policy = job_type_policy(config, job_type)
    merged_caps = normalize_capabilities(required_capabilities + policy.get("default_required_capabilities", []))
    final_approval = approval_required or bool(policy.get("force_approval"))
    final_preferred_node = preferred_node or policy.get("preferred_node")
    return merged_caps, final_approval, final_preferred_node


def retryable_default(config: dict[str, Any], job_type: str) -> bool:
    policy = job_type_policy(config, job_type)
    return bool(policy.get("default_retryable_on_failure", False))
