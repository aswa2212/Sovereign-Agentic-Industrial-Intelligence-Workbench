"""Sovereignty and air-gap enforcement checks."""

from datetime import datetime, timezone
import ipaddress
from typing import List, Optional
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.audit.models import (
    NetworkObservationReport,
    ProviderSovereigntyCheck,
    SovereigntyStatus,
)
from app.services.audit.network_monitor import RuntimeNetworkMonitor


def is_strictly_local_host(host: Optional[str]) -> bool:
    """
    Verify if a hostname or IP string is strictly a local host.
    Permitted: 'localhost', '127.0.0.1', '::1', '0.0.0.0', '::'.
    Rejects public/remote hostnames, cloud domains, external IPs.
    """
    if not host:
        return False
    host_clean = host.strip().lower()

    if host_clean in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "::"):
        return True

    # Check if it resolves to loopback IP
    try:
        ip = ipaddress.ip_address(host_clean)
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        pass

    # Reject any general or external hostname
    return False


class SovereigntyChecker:
    """
    Validates that model provider endpoints and network configurations
    comply with local-only sovereign constraints when AIR_GAPPED_MODE is enabled.
    """

    def __init__(self, network_monitor: Optional[RuntimeNetworkMonitor] = None):
        self.network_monitor = network_monitor or RuntimeNetworkMonitor()

    def check_provider_url(self, provider_name: str, url: Optional[str]) -> ProviderSovereigntyCheck:
        """Evaluate a single provider's endpoint URL for strict locality."""
        if not url:
            return ProviderSovereigntyCheck(
                provider_name=provider_name,
                configured_url=None,
                is_local=True,
                host=None,
                port=None,
                error=None
            )

        try:
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port

            if not host:
                return ProviderSovereigntyCheck(
                    provider_name=provider_name,
                    configured_url=url,
                    is_local=False,
                    host=None,
                    port=port,
                    error="Unable to parse hostname from provider URL."
                )

            is_local = is_strictly_local_host(host)
            err = None if is_local else f"Host '{host}' is not a permitted local loopback address."

            return ProviderSovereigntyCheck(
                provider_name=provider_name,
                configured_url=url,
                is_local=is_local,
                host=host,
                port=port,
                error=err
            )
        except Exception as e:
            return ProviderSovereigntyCheck(
                provider_name=provider_name,
                configured_url=url,
                is_local=False,
                host=None,
                port=None,
                error=f"Error parsing provider URL: {e}"
            )

    def evaluate_sovereignty(
        self,
        air_gapped_mode: Optional[bool] = None,
        custom_providers: Optional[dict] = None
    ) -> SovereigntyStatus:
        """
        Evaluate full sovereignty compliance across configured model providers
        and observable runtime network activity.
        """
        settings = get_settings()
        is_air_gapped = (
            air_gapped_mode if air_gapped_mode is not None else getattr(settings, "air_gapped_mode", True)
        )

        # Collect configured providers
        providers_to_check = {
            "Ollama": getattr(settings, "ollama_base_url", "http://127.0.0.1:11434"),
            "LlamaCPP": getattr(settings, "llamacpp_base_url", "http://127.0.0.1:8080"),
            "vLLM": getattr(settings, "vllm_base_url", "http://127.0.0.1:8000")
        }

        if custom_providers:
            providers_to_check.update(custom_providers)

        provider_results: List[ProviderSovereigntyCheck] = []
        violations: List[str] = []

        for name, url in providers_to_check.items():
            check = self.check_provider_url(name, url)
            provider_results.append(check)
            if not check.is_local and is_air_gapped:
                violations.append(
                    f"Provider '{name}' configured with non-local endpoint: '{url}'. "
                    f"Violation detail: {check.error}"
                )

        # Perform runtime network observation
        net_report: NetworkObservationReport = self.network_monitor.observe_connections()
        external_observed = net_report.non_loopback_connections > 0

        if external_observed and is_air_gapped:
            violations.append(
                f"Observed {net_report.non_loopback_connections} non-loopback active socket connections."
            )

        status_str = "FAIL" if violations else "PASS"

        return SovereigntyStatus(
            status=status_str,
            local_mode_enabled=is_air_gapped,
            provider_checks=provider_results,
            network_observation=net_report,
            external_connections_observed=external_observed,
            violations=violations,
            checked_at=datetime.now(timezone.utc).isoformat()
        )
