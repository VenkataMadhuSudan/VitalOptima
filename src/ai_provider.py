"""
VitalOptima Provider-Independent AI Architecture
Decouples application services from specific language-model providers.
Calculations (forecasting, optimization, emergency simulation) remain strictly
outside the model; providers only explain structured calculated evidence.
"""
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional


class BaseAIProvider(ABC):
    """Abstract Base Class for AI insight generators and conversational agents."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the name identifier of the provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the provider is currently available and configured."""
        pass

    @abstractmethod
    def generate_insights(
        self,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Generates structured executive insights from verified analytical evidence.
        Returns: (insights_dict, error_or_none)
        """
        pass

    @abstractmethod
    def answer_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Answers operational questions using grounded evidence tools.
        Returns: (response_text, tool_calls_executed)
        """
        pass


class DeterministicProvider(BaseAIProvider):
    """
    100% offline, reproducible, deterministic operational intelligence engine.
    Computes exact hospital telemetry metrics without external network or LLM dependencies.
    """

    def get_provider_name(self) -> str:
        return "Deterministic Analytics Engine"

    def is_available(self) -> bool:
        return True

    def generate_insights(
        self,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        from src.grok_client import generate_deterministic_insights
        from src.ai_analytics import build_evidence_package
        if evidence is None:
            evidence = build_evidence_package()
        return generate_deterministic_insights(evidence), None

    def answer_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        from src.grok_client import answer_agent_question
        # Forces fallback deterministic execution by passing non-matching key or direct tool routing
        return answer_agent_question(question, chat_history=chat_history)


class GrokProvider(BaseAIProvider):
    """
    xAI Grok Provider via OpenAI-compatible REST API.
    Synthesizes rich clinical and operational narrative grounded in structured metrics.
    Gracefully falls back to DeterministicProvider when offline or unconfigured.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.override_key = api_key
        self.model_name = model_name

    def get_provider_name(self) -> str:
        return f"xAI Grok ({self.model_name or os.getenv('XAI_MODEL', 'grok-2-latest')})"

    def is_available(self) -> bool:
        from src.grok_client import is_grok_available
        return is_grok_available(self.override_key)

    def generate_insights(
        self,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        from src.grok_client import generate_grok_insights
        return generate_grok_insights(
            evidence=evidence,
            api_key=self.override_key,
            model_name=self.model_name
        )

    def answer_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        from src.grok_client import answer_agent_question
        return answer_agent_question(
            question=question,
            chat_history=chat_history,
            api_key=self.override_key,
            model_name=self.model_name
        )


class KompactAdapter(BaseAIProvider):
    """
    Adapter boundary for future Kompact engine integration.
    Maintains clean architectural decoupling so Kompact local edge runtime
    can be integrated without modifying forecaster, optimizer, or simulator models.
    """

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("KOMPACT_ENDPOINT_URL")

    def get_provider_name(self) -> str:
        return "Kompact Edge Inference Engine (Adapter)"

    def is_available(self) -> bool:
        # Honest capability reporting: currently only active if endpoint is configured
        return bool(self.endpoint_url and self.endpoint_url.strip())

    def generate_insights(
        self,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        if not self.is_available():
            raise NotImplementedError(
                "Kompact inference endpoint is not configured in this environment. "
                "Set KOMPACT_ENDPOINT_URL or select Grok/Deterministic provider."
            )
        # Future Kompact client invocation will hook here
        raise NotImplementedError("Kompact model runtime integration pending final API specs.")

    def answer_question(
        self,
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        if not self.is_available():
            raise NotImplementedError(
                "Kompact inference endpoint is not configured in this environment."
            )
        raise NotImplementedError("Kompact conversational agent pending final API specs.")


def get_ai_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> BaseAIProvider:
    """
    Factory function returning the active AI provider instance based on
    configuration, environment, and availability.
    """
    selected = (provider_name or os.getenv("AI_PROVIDER", "auto")).strip().lower()

    if selected == "deterministic":
        return DeterministicProvider()
    elif selected == "kompact":
        return KompactAdapter()
    elif selected == "grok":
        return GrokProvider(api_key=api_key)
    else:  # "auto"
        grok = GrokProvider(api_key=api_key)
        if grok.is_available():
            return grok
        return DeterministicProvider()
