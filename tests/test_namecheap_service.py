# import unittest
# from unittest.mock import patch, MagicMock
# from services.namecheap_service import NamecheapService
#
#
# class TestNamecheapService(unittest.TestCase):
#     def setUp(self):
#         """Set up an instance of NamecheapService for testing."""
#         self.service = NamecheapService()
#
#     @patch("services.namecheap_service.NamecheapService._generate_similar_domains")
#     @patch("requests.get")
#     def test_check_domain_availability(self, mock_get, mock_generate_domains):
#         """Test checking domain availability with a mocked API response."""
#         # Mock the similar domains generation
#         mock_generate_domains.return_value = ["example.net", "example.org", "myexample.com"]
#
#         # Create a sequence of responses for batched requests
#         mock_responses = [
#             MagicMock(status_code=200, text="""
#             <ApiResponse xmlns="http://api.namecheap.com/xml.response">
#                 <CommandResponse>
#                     <DomainCheckResult Domain="example.com" Available="false"/>
#                     <DomainCheckResult Domain="example.net" Available="true"/>
#                 </CommandResponse>
#             </ApiResponse>
#             """),
#             MagicMock(status_code=200, text="""
#             <ApiResponse xmlns="http://api.namecheap.com/xml.response">
#                 <CommandResponse>
#                     <DomainCheckResult Domain="example.org" Available="true"/>
#                     <DomainCheckResult Domain="myexample.com" Available="false"/>
#                 </CommandResponse>
#             </ApiResponse>
#             """)
#         ]
#
#         # Configure the mock to return different responses for each call
#         mock_get.side_effect = mock_responses
#
#         # Test the function
#         result = self.service.check_domain_availability("example.com")
#
#         # Expected output should only include available domains
#         expected_output = {
#             "suggestions": [
#                 {
#                     "domain": "example.net",
#                     "regular_price": 10.99,
#                     "sale_price": 8.99,
#                     "sale_percentage": 18
#                 },
#                 {
#                     "domain": "example.org",
#                     "regular_price": 10.99,
#                     "sale_price": 8.99,
#                     "sale_percentage": 18
#                 }
#             ]
#         }
#
#         self.assertEqual(result, expected_output)
#
#         # Verify that the mocked methods were called correctly
#         mock_generate_domains.assert_called_once_with("example")
#         self.assertEqual(mock_get.call_count, 2)  # Two batches of API calls
#
#     @patch("services.namecheap_service.NamecheapService._generate_similar_domains")
#     @patch("requests.get")
#     def test_check_domain_availability_with_available_original(self, mock_get, mock_generate_domains):
#         """Test when the original domain is available."""
#         # Mock the similar domains generation
#         mock_generate_domains.return_value = ["test.net", "test.org"]
#
#         # Create a mock response where the original domain is available
#         mock_response = MagicMock(status_code=200, text="""
#         <ApiResponse xmlns="http://api.namecheap.com/xml.response">
#             <CommandResponse>
#                 <DomainCheckResult Domain="test.com" Available="true"/>
#                 <DomainCheckResult Domain="test.net" Available="true"/>
#                 <DomainCheckResult Domain="test.org" Available="false"/>
#             </CommandResponse>
#         </ApiResponse>
#         """)
#
#         mock_get.return_value = mock_response
#
#         # Test the function
#         result = self.service.check_domain_availability("test")
#
#         # Expected output should include the original domain and one suggestion
#         expected_output = {
#             "domain": {
#                 "domain": "test.com",
#                 "regular_price": 10.99,
#                 "sale_price": 8.99,
#                 "sale_percentage": 18
#             },
#             "suggestions": [
#                 {
#                     "domain": "test.net",
#                     "regular_price": 10.99,
#                     "sale_price": 8.99,
#                     "sale_percentage": 18
#                 }
#             ]
#         }
#
#         self.assertEqual(result, expected_output)
#
#
# if __name__ == "__main__":
#     unittest.main()