
import argparse
from pathlib import Path

from src.tricypher.core import TriCypher
from src.tricypher.document_processor import (
    protect_document,
    restore_document,
    save_document,
)


def main():
    parser = argparse.ArgumentParser(
        description="TriCypher automatic dataset protection and restoration"
    )

    parser.add_argument(
        "file",
        help="Path to the dataset file"
    )

    args = parser.parse_args()

    input_path = Path(args.file)

    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return

    output_dir = Path("processed")
    output_dir.mkdir(exist_ok=True)

    print("\n========== TRICYPHER DATASET PIPELINE ==========")
    print(f"Input file: {input_path}")

    # Create one engine for both protection and restoration.
    engine = TriCypher()

    try:
        # STEP 1: PROTECT
        print("\n[1/3] Detecting and protecting sensitive data...")

        result = protect_document(input_path, engine)

        file_type = result["file_type"]
        protected_content = result["protected_content"]

        protected_path = output_dir / (
            input_path.stem + ".protected" + file_type
        )

        save_document(
            protected_content,
            file_type,
            protected_path
        )

        print("Protection completed.")
        print("Detected PII:", result["detected_count"])
        print("Detected types:", result["detected_types"])
        print("Protected file:", protected_path)

        # STEP 2: RESTORE
        print("\n[2/3] Restoring original values locally...")

        restored_content = restore_document(
            protected_content,
            file_type,
            engine
        )

        restored_path = output_dir / (
            input_path.stem + ".restored" + file_type
        )

        save_document(
            restored_content,
            file_type,
            restored_path
        )

        print("Restoration completed.")
        print("Restored file:", restored_path)

        # STEP 3: SUMMARY
        print("\n[3/3] Pipeline completed.")

        print("\n========== RESULTS ==========")
        print("Original file :", input_path)
        print("Protected file:", protected_path)
        print("Restored file :", restored_path)
        print("PII detected  :", result["detected_count"])
        print("PII types     :", result["detected_types"])
        print("=============================")

    except Exception as error:
        print("\nTRICYPHER PIPELINE FAILED:")
        print(error)
        raise


if __name__ == "__main__":
    main()
