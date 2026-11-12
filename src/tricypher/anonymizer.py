
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class TriCypherAnonymizer:
    """Replace detected sensitive information with placeholders."""

    def __init__(self):
        self.anonymizer = AnonymizerEngine()

    def anonymize(self, text, detected_entities):
        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
            "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
            "IN_AADHAAR": OperatorConfig("replace", {"new_value": "<AADHAAR>"}),
            "URL": OperatorConfig("replace", {"new_value": "<URL>"}),
        }

        result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=detected_entities,
            operators=operators,
        )

        return result.text
