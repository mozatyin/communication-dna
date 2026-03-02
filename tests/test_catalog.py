# tests/test_catalog.py
from communication_dna.catalog import FEATURE_CATALOG, get_features_for_dimension, ALL_DIMENSIONS


def test_all_13_dimensions_present():
    assert len(ALL_DIMENSIONS) == 13
    expected_codes = {"LEX", "SYN", "DIS", "PRA", "AFF", "INT", "IDN", "MET", "TMP", "ERR", "CSW", "PTX", "DSC"}
    assert set(ALL_DIMENSIONS.keys()) == expected_codes


def test_catalog_has_features_for_every_dimension():
    for code in ALL_DIMENSIONS:
        features = get_features_for_dimension(code)
        assert len(features) >= 3, f"Dimension {code} has fewer than 3 features"


def test_each_feature_has_required_fields():
    for entry in FEATURE_CATALOG:
        assert "dimension" in entry
        assert "name" in entry
        assert "description" in entry
        assert "detection_hint" in entry
        assert "value_anchors" in entry


def test_lexical_features_include_formality():
    lex_features = get_features_for_dimension("LEX")
    names = [f["name"] for f in lex_features]
    assert "formality" in names
