"""Shared test configuration for API tests."""

import os

# Set test environment before any app code is imported.
# This disables domain blocking in email_validation so test fixtures
# using @example.com and @test.com work without modification.
os.environ["API_ENV"] = "test"
