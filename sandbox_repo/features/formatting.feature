Feature: Formatting helpers behavior
  As a developer using stringkit
  I want human_readable_size and pluralize fully specified by tests
  So that their behavior is guaranteed not to regress

  Scenario: Format a byte count in the megabyte range
    Given a byte count of 1500000
    When I format it as a human readable size
    Then the result is "1.4 MB"

  Scenario: Pluralize a regular word
    Given the word "cat" with count 2
    When I pluralize it
    Then the result is "cats"

  Scenario: Do not pluralize a singular count
    Given the word "cat" with count 1
    When I pluralize it
    Then the result is "cat"
