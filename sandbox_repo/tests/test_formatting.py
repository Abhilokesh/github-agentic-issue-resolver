from stringkit.formatting import (
    human_readable_size,
    build_report_lines,
    generated_at_label,
)


def test_human_readable_size_bytes():
    assert human_readable_size(500) == "500.0 B"


def test_human_readable_size_kb():
    assert human_readable_size(2048) == "2.0 KB"


def test_build_report_lines():
    assert build_report_lines(["a", "b"]) == ["- a", "- b"]


def test_generated_at_label_no_deprecation_warning():
    # pytest.ini turns DeprecationWarning from stringkit.formatting into
    # an error, so this raises until the function stops using a
    # deprecated datetime API.
    generated_at_label()
