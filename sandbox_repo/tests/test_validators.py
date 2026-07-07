from stringkit.validators import is_valid_email


def test_is_valid_email_true():
    assert is_valid_email("user@example.com") is True


def test_is_valid_email_false():
    assert is_valid_email("not-an-email") is False
