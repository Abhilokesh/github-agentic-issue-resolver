Feature: URL validation behavior

  Scenario: Recognize a valid https URL
    Given the string "https://example.com"
    When I validate it as a URL
    Then it is considered valid

  Scenario: Reject a string that is not a URL
    Given the string "not a url"
    When I validate it as a URL
    Then it is considered invalid
