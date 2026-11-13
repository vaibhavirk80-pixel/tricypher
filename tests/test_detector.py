from src.tricypher.detector import TriCypherDetector


def test_detect_person_name():
    detector = TriCypherDetector()

    text = "Applicant Shweta Desai has applied for a loan."
    entities = detector.detect(text)

    detected_values = [
        text[entity.start:entity.end]
        for entity in entities
    ]

    assert "Shweta Desai" in detected_values


def test_detect_indian_pii():
    detector = TriCypherDetector()

    text = (
        "PAN: ABCDE1234F\n"
        "Aadhaar Number: 1234 5678 9012\n"
        "Mobile Number: 9123456789\n"
        "IFSC: SBIN0001234\n"
        "GSTIN: 24ABCDE1234F1Z5"
    )

    entities = detector.detect(text)

    detected_values = {
        text[entity.start:entity.end]
        for entity in entities
    }

    expected_values = {
        "ABCDE1234F",
        "1234 5678 9012",
        "9123456789",
        "SBIN0001234",
        "24ABCDE1234F1Z5",
    }

    assert expected_values.issubset(detected_values)


def test_detect_bank_account():
    detector = TriCypherDetector()

    text = "Bank Account Number: 123456789012"
    entities = detector.detect(text)

    detected_values = [
        text[entity.start:entity.end]
        for entity in entities
    ]

    assert "123456789012" in detected_values


def test_detect_organization():
    detector = TriCypherDetector()

    text = "Corporate KYC for Sri Lakshmi Traders"
    entities = detector.detect(text)

    detected_values = [
        text[entity.start:entity.end]
        for entity in entities
    ]

    assert "Sri Lakshmi Traders" in detected_values