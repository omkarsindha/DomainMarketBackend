import unittest
import time
from unittest.mock import patch
from services.domain_search_service import DomainSearchService


class PerformanceTestDomainSearch(unittest.TestCase):
    """Non-functional test to verify search performance meets requirements."""

    def setUp(self):
        """Set up test environment with sample domain data."""
        self.search_service = DomainSearchService()
        # Pre-populate service with test data
        self.test_domains = self._generate_test_domains(10000)
        with patch('services.domain_search_service.domain_repository.get_all_domains') as mock_repo:
            mock_repo.return_value = self.test_domains
            self.search_service.initialize_search_index()

    def _generate_test_domains(self, count):
        """Generate a large set of test domains."""
        domains = []
        tlds = ['.com', '.net', '.org', '.io', '.co']
        words = ['domain', 'market', 'buy', 'sell', 'trade', 'web', 'site', 'online', 'digital', 'cyber']

        for i in range(count):
            word_combo = words[i % len(words)] + words[(i + 3) % len(words)]
            domains.append({
                'domain_name': f"{word_combo}{tlds[i % len(tlds)]}",
                'price': 10.99 + (i % 100),
                'category': ['business', 'technology'][i % 2],
                'length': len(word_combo) + len(tlds[i % len(tlds)])
            })
        return domains

    def test_search_performance_under_load(self):
        """Verify domain search completes within performance requirements (100ms)."""
        # Define search terms
        search_terms = ["domain", "market", "business", "tech"]

        # Measure search performance
        for term in search_terms:
            start_time = time.time()
            results = self.search_service.search(term, limit=20)
            end_time = time.time()

            search_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Assert search completes within performance requirement
            self.assertLessEqual(search_time, 100,
                                 f"Search for '{term}' took {search_time:.2f}ms, exceeding 100ms requirement")

            # Verify correct number of results returned
            self.assertLessEqual(len(results), 20,
                                 f"Search returned more than requested limit of 20 results")
