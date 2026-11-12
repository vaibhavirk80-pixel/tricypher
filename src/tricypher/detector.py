
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider


class TriCypherDetector:
    """Detect sensitive information in text."""

    def __init__(self):
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [
                {
                    "lang_code": "en",
                    "model_name": "en_core_web_sm",
                }
            ],
        }

        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            supported_languages=["en"],
        )

        # Indian Aadhaar: 12 digits, optionally separated by spaces
        aadhaar = Pattern(
            name="aadhaar_pattern",
            regex=r"\b\d{4}\s?\d{4}\s?\d{4}\b",
            score=0.65,
        )

        aadhaar_recognizer = PatternRecognizer(
            supported_entity="IN_AADHAAR",
            patterns=[aadhaar],
            name="Indian Aadhaar Recognizer",
        )

        self.analyzer.registry.add_recognizer(aadhaar_recognizer)

    def detect(self, text: str):
        """Return detected sensitive entities."""
        return self.analyzer.analyze(
            text=text,
            language="en",
        )
