from stringkit.casing import to_camel_case


def test_to_camel_case():
    assert to_camel_case("hello_world") == "helloWorld"
