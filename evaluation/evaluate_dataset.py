
import argparse
import csv
import json
import sys
from pathlib import Path

# Make the project root importable when this script is run directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.tricypher.core import TriCypher


def evaluate_dataset(dataset_path):
    dataset_path = Path(dataset_path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8-sig") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Dataset must contain a JSON list of records.")

    engine = TriCypher()

    results = []
    total_expected = 0
    total_protected = 0
    total_missed = 0
    total_errors = 0

    for record in records:
        doc_id = record.get("doc_id", "UNKNOWN")
        content = record.get("content", "")
        expected_labels = record.get("expected_pii_labels", {})

        expected_values = [
            str(value)
            for values in expected_labels.values()
            for value in (values if isinstance(values, list) else [values])
            if value is not None
        ]

        total_expected += len(expected_values)

        try:
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Document content is empty.")

            protected = engine.protect(content)
            protected_text = protected["protected_text"]

            protected_values = [
                value for value in expected_values
                if value not in protected_text
            ]

            missed_values = [
                value for value in expected_values
                if value in protected_text
            ]

            total_protected += len(protected_values)
            total_missed += len(missed_values)

            results.append({
                "doc_id": doc_id,
                "doc_type": record.get("doc_type", "Unknown"),
                "status": "SUCCESS",
                "expected_pii_count": len(expected_values),
                "protected_pii_count": len(protected_values),
                "missed_pii_count": len(missed_values),
                "missed_values": missed_values,
                "detected_count": protected["detected_count"],
                "detected_types": protected["detected_types"],
                "protected_text": protected_text,
            })

        except Exception as error:
            total_errors += 1
            results.append({
                "doc_id": doc_id,
                "doc_type": record.get("doc_type", "Unknown"),
                "status": "ERROR",
                "error": str(error),
                "expected_pii_count": len(expected_values),
            })

    recall = (
        total_protected / total_expected * 100
        if total_expected else 0
    )

    output_dir = PROJECT_ROOT / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "total_documents": len(records),
        "successful_documents": len(records) - total_errors,
        "failed_documents": total_errors,
        "total_expected_pii": total_expected,
        "total_protected_pii": total_protected,
        "total_missed_pii": total_missed,
        "protection_recall_percent": round(recall, 2),
        "results": results,
    }

    json_path = output_dir / "evaluation_report.json"
    csv_path = output_dir / "evaluation_report.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        if results:
            writer = csv.DictWriter(
                file,
                fieldnames=results[0].keys()
            )
            writer.writeheader()
            writer.writerows(results)

    print("\n========== TRICYPHER DATASET EVALUATION ==========")
    print(f"Total documents       : {len(records)}")
    print(f"Successful documents  : {len(records) - total_errors}")
    print(f"Failed documents      : {total_errors}")
    print(f"Expected PII values   : {total_expected}")
    print(f"Protected PII values  : {total_protected}")
    print(f"Missed PII values     : {total_missed}")
    print(f"Protection recall     : {recall:.2f}%")
    print("==================================================")
    print(f"\nJSON report: {json_path}")
    print(f"CSV report : {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate TriCypher against a labeled JSON dataset."
    )

    parser.add_argument(
        "dataset",
        nargs="?",
        default=str(
            Path.home()
            / "OneDrive"
            / "Desktop"
            / "tricypher-dataset-eval"
            / "text_documents.json"
        ),
        help="Path to the labeled JSON dataset"
    )

    args = parser.parse_args()
    evaluate_dataset(args.dataset)
