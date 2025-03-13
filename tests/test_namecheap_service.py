import unittest
from unittest.mock import patch, MagicMock
from services.namecheap_service import NamecheapService


class TestNamecheapService(unittest.TestCase):
    def setUp(self):
        """Set up an instance of NamecheapService for testing."""
        self.service = NamecheapService()

    @patch("requests.get")
    def test_check_domains(self, mock_get):
        """Test checking domain availability with a mocked API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <ApiResponse xmlns="http://api.namecheap.com/xml.response">
            <CommandResponse>
                <DomainCheckResult Domain="example.com" Available="false"/>
                <DomainCheckResult Domain="newsite123.net" Available="true"/>
            </CommandResponse>
        </ApiResponse>
        """
        mock_get.return_value = mock_response

        result = self.service.check_domains(["example.com", "newsite123.net"])

        expected_output = {
            "domains": [
                {"domain": "example.com", "available": False},
                {"domain": "newsite123.net", "available": True},
            ]
        }

        self.assertEqual(result, expected_output)


if __name__ == "__main__":
    unittest.main()
