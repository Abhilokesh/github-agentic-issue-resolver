from stringkit.slug import slugify


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_custom_separator():
    assert slugify("Hello World", separator="_") == "hello_world"
