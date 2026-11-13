
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider


class TriCypherDetector:
    """Detect sensitive information, including Indian PII."""

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

        # Aadhaar number
        aadhaar = Pattern(
            name="aadhaar_pattern",
            regex=r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)",
            score=0.90,
        )

        aadhaar_recognizer = PatternRecognizer(
            supported_entity="IN_AADHAAR",
            patterns=[aadhaar],
            name="Indian Aadhaar Recognizer",
            context=["aadhaar", "uidai", "unique identification"],
        )

        # Indian PAN
        pan = Pattern(
            name="pan_pattern",
            regex=r"(?i)(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])",
            score=0.95,
        )

        pan_recognizer = PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=[pan],
            name="Indian PAN Recognizer",
            context=["pan", "permanent account number", "tax identification"],
        )

        # Indian GSTIN
        gstin = Pattern(
            name="gstin_pattern",
            regex=r"(?i)(?<![A-Z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9](?![A-Z0-9])",
            score=0.95,
        )

        gstin_recognizer = PatternRecognizer(
            supported_entity="IN_GSTIN",
            patterns=[gstin],
            name="Indian GSTIN Recognizer",
            context=["gstin", "gst number", "goods and services tax"],
        )

        # Indian IFSC
        ifsc = Pattern(
            name="ifsc_pattern",
            regex=r"(?i)(?<![A-Z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Z0-9])",
            score=0.95,
        )

        ifsc_recognizer = PatternRecognizer(
            supported_entity="IN_IFSC",
            patterns=[ifsc],
            name="Indian IFSC Recognizer",
            context=["ifsc", "bank code", "branch code", "bank branch"],
        )

        # Indian mobile number
        phone = Pattern(
            name="indian_phone_pattern",
            regex=r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
            score=0.90,
        )

        phone_recognizer = PatternRecognizer(
            supported_entity="IN_PHONE_NUMBER",
            patterns=[phone],
            name="Indian Phone Recognizer",
            context=["phone", "mobile", "contact number", "telephone"],
        )

        # Indian bank account number
        bank_account = Pattern(
            name="indian_bank_account_pattern",
            regex=r"(?<!\d)(?:\d[ -]?){8,17}\d(?!\d)",
            score=0.90,
        )

        bank_recognizer = PatternRecognizer(
            supported_entity="IN_BANK_ACCOUNT",
            patterns=[bank_account],
            name="Indian Bank Account Recognizer",
            context=["bank account", "account number", "bank a/c"],
        )

        # Context-based person detection
        person_name_patterns = [
            Pattern(
                name="applicant_name",
                regex=r"(?i)(?<=Applicant )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="applicant_name_label",
                regex=r"(?i)(?<=Applicant Name: )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.95,
            ),
            Pattern(
                name="employee_name",
                regex=r"(?i)(?<=employee )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="employee_name_label",
                regex=r"(?i)(?<=Employee Name: )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.95,
            ),
            Pattern(
                name="ticket_raised_by",
                regex=r"(?i)(?<=raised by )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="signatory_name",
                regex=r"(?i)(?<=signatory )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="kyc_request_name",
                regex=r"(?i)(?<=request for )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="hindi_chat_name",
                regex=r"(?i)(?<=main )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
            Pattern(
                name="person_introduction",
                regex=r"(?i)(?<=I am )[A-Z][a-z]+\s+[A-Z][a-z]+\b",
                score=0.90,
            ),
        ]

        person_recognizer = PatternRecognizer(
            supported_entity="PERSON",
            patterns=person_name_patterns,
            name="Context-Based Indian Person Recognizer",
        )

        # Organization detection.
        # Supports comma, newline, or end of text after the organization.
        organization_recognizer = PatternRecognizer(
            supported_entity="ORGANIZATION",
            patterns=[
                Pattern(
                    name="corporate_kyc_organization",
                    regex=r"(?i)(?<=Corporate KYC for )[A-Z][A-Za-z&.-]*(?:\s+[A-Z][A-Za-z&.-]*){1,4}(?=[,\n]|\s*$)",
                    score=0.95,
                )
            ],
            name="Corporate KYC Organization Recognizer",
        )

        # Register custom recognizers.
        for recognizer in [
            aadhaar_recognizer,
            pan_recognizer,
            gstin_recognizer,
            ifsc_recognizer,
            phone_recognizer,
            bank_recognizer,
            person_recognizer,
            organization_recognizer,
        ]:
            self.analyzer.registry.add_recognizer(recognizer)

    def detect(self, text: str):
        """Detect PII and resolve incorrect overlapping detections."""

        results = self.analyzer.analyze(
            text=text,
            language="en",
        )

        valid_results = []

        for entity in results:
            value = text[entity.start:entity.end]
            value_lower = value.lower().strip()

            preceding_text = text[max(0, entity.start - 60):entity.start].lower()

            # Reject invalid PERSON detections.
            if entity.entity_type == "PERSON":
                if (
                    any(char.isdigit() for char in value)
                    or ":" in value
                    or value_lower in {"gstin", "pan", "pdf"}
                ):
                    continue

            # Reject obvious false ORGANIZATION detections.
            if entity.entity_type == "ORGANIZATION":
                if (
                    any(char.isdigit() for char in value)
                    or "\n" in value
                    or ":" in value
                    or len(value.strip()) <= 3
                ):
                    continue

            # Prefer Indian-specific recognizers over generic NLP results.
            priority = {
                "IN_GSTIN": 120,
                "IN_PAN": 120,
                "IN_IFSC": 120,
                "EMAIL_ADDRESS": 120,
                "IN_AADHAAR": 100,
                "IN_PHONE_NUMBER": 100,
                "IN_BANK_ACCOUNT": 100,
                "PERSON": 80,
                "ORGANIZATION": 70,
            }.get(entity.entity_type, 10)

            # Resolve numeric overlaps using nearby field labels.
            if entity.entity_type == "IN_BANK_ACCOUNT":
                if any(word in preceding_text for word in ["bank account", "account number", "bank a/c"]):
                    priority = 140

            elif entity.entity_type == "IN_AADHAAR":
                if "aadhaar" in preceding_text or "uidai" in preceding_text:
                    priority = 140

            elif entity.entity_type == "IN_PHONE_NUMBER":
                if any(word in preceding_text for word in ["mobile", "phone", "contact number", "telephone"]):
                    priority = 140

            # Generic date/time detections should not override labelled PII.
            if entity.entity_type == "DATE_TIME":
                if any(
                    word in preceding_text
                    for word in [
                        "mobile number",
                        "phone number",
                        "aadhaar number",
                        "bank account number",
                        "account number",
                    ]
                ):
                    continue

            valid_results.append((entity, priority))

        # Highest-priority detection wins when spans overlap.
        valid_results.sort(
            key=lambda item: (
                -item[1],
                item[0].start,
                -(item[0].end - item[0].start),
            )
        )

        filtered_results = []

        for entity, priority in valid_results:
            overlaps = any(
                entity.start < existing.end
                and entity.end > existing.start
                for existing in filtered_results
            )

            if not overlaps:
                filtered_results.append(entity)

        return sorted(filtered_results, key=lambda item: item.start)
