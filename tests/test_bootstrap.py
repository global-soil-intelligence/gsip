from pathlib import Path


def test_governing_documents_exist() -> None:
    root = Path(__file__).parents[1]
    assert (root / "docs" / "SPEC.md").is_file()
    assert (root / "docs" / "BUILD_ORDER.md").is_file()
