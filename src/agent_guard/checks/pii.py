"""Offline English PII detection using an explicitly curated Presidio registry."""

import re
from importlib import metadata
from typing import Any

from agent_guard.core.errors import ConfigurationError

_EMAIL = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@(?:[A-Z0-9-]+\.)+[A-Z]{2,}(?![\w.-])", re.IGNORECASE)
_ENTITIES = ("PERSON", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN")


class LocalPIIDetector:
    """The `english-v1` preset; model provisioning is an installation-time step."""

    def __init__(self, *, preset: str = "english-v1", language: str = "en") -> None:
        if preset != "english-v1" or language != "en":
            raise ConfigurationError("unsupported_pii_preset")
        self._analyzer: Any = None
        self._extractor: Any = None

    def prepare(self) -> None:
        try:
            import spacy
            from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
            from presidio_analyzer.nlp_engine import SpacyNlpEngine
            from presidio_analyzer.predefined_recognizers import (
                CreditCardRecognizer,
                PhoneRecognizer,
                SpacyRecognizer,
                UsSsnRecognizer,
            )
            from tldextract import TLDExtract
        except ImportError:
            raise ConfigurationError("pii_dependency_unavailable") from None
        try:
            if not spacy.util.is_package("en_core_web_lg") or metadata.version("en_core_web_lg") != "3.8.0":
                raise ConfigurationError("pii_model_unavailable")
        except metadata.PackageNotFoundError:
            raise ConfigurationError("pii_model_unavailable") from None
        try:
            engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_lg"}])
            engine.load()
            registry = RecognizerRegistry(supported_languages=["en"])
            registry.add_recognizer(SpacyRecognizer(supported_entities=["PERSON"]))
            registry.add_recognizer(PhoneRecognizer(supported_regions=("US", "CA", "GB")))
            registry.add_recognizer(CreditCardRecognizer())
            registry.add_recognizer(UsSsnRecognizer())
            analyzer = AnalyzerEngine(
                registry=registry, nlp_engine=engine, supported_languages=["en"],
                default_score_threshold=0.35,
            )
            extractor = TLDExtract(
                suffix_list_urls=(), cache_dir=None, fallback_to_snapshot=True,
            )
        except Exception:  # noqa: BLE001 - optional package internals are not public errors
            raise ConfigurationError("pii_model_unavailable") from None
        self._analyzer = analyzer
        self._extractor = extractor

    def detect(self, text: str) -> bool:
        if self._analyzer is None or self._extractor is None:
            raise ConfigurationError("pii_detector_not_prepared")
        for match in _EMAIL.finditer(text):
            host = match.group().rsplit("@", 1)[1]
            if self._extractor(host).suffix:
                return True
        return bool(self._analyzer.analyze(text=text, language="en", entities=list(_ENTITIES)))

    def close(self) -> None:
        self._analyzer = None
        self._extractor = None
