
from .detector import TriCypherDetector
from .anonymizer import TriCypherAnonymizer
from .vault import TokenVault
from dotenv import load_dotenv
import re
import secrets

load_dotenv()


class TriCypher:
    def __init__(self):
        self.detector = TriCypherDetector()
        self.anonymizer = TriCypherAnonymizer()
        self.vault = TokenVault()

    def protect(self, text: str) -> dict:
        if not isinstance(text, str):
            raise TypeError("Input must be a string")

        if not text.strip():
            raise ValueError("Input text cannot be empty")

        detected_entities = self.detector.detect(text)

      
        # Remove overlapping detections.
        # Prefer the longer detected entity.
        filtered_entities = []

        for entity in sorted(
            detected_entities,
            key=lambda item: (item.start, -(item.end - item.start)),
        ):
            overlaps = any(
                entity.start < existing.end
                and entity.end > existing.start
                for existing in filtered_entities
            )

            if not overlaps:
                filtered_entities.append(entity)

        detected_entities = filtered_entities

        # Replace sensitive values with typed reversible tokens.
        protected_text = text
        token_map = {}

        for entity in sorted(
            detected_entities,
            key=lambda item: item.start,
            reverse=True,
        ):
            original_value = text[entity.start:entity.end]

            entity_type = entity.entity_type
            token = f"<TC_{entity_type}_{secrets.token_hex(6)}>"

            self.vault.store(original_value, token=token)

            protected_text = (
                protected_text[:entity.start]
                + token
                + protected_text[entity.end:]
            )

            token_map[token] = entity_type

        return {
            "protected_text": protected_text,
            "detected_count": len(detected_entities),
            "detected_types": list(
                dict.fromkeys(e.entity_type for e in detected_entities)
            ),
            "token_map": token_map,
        }

    def restore(self, protected_text: str) -> str:
        pattern = r"<TC_[A-Z0-9_]+_[a-f0-9]{12}>"

        def replace_token(match):
            token = match.group(0)
            original = self.vault.restore(token)
            return original if original is not None else token

        return re.sub(pattern, replace_token, protected_text)
