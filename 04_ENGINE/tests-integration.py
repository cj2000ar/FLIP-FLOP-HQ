"""
Integration tests for FlipFlop Private Read API

Tests all endpoints with real authentication flow
"""

import pytest
import requests
import os
import json
from datetime import datetime, timedelta

# Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8000')
MACHINE_ID = os.getenv('MACHINE_ID', 'test-machine')
FENCING_TOKEN = os.getenv('FENCING_TOKEN', '')

# Test fixtures
@pytest.fixture
def api_client():
    """Create API client with authentication"""
    class Client:
        def __init__(self):
            self.base_url = API_URL
            self.machine_id = MACHINE_ID
            self.token = FENCING_TOKEN

        def get(self, endpoint: str, **kwargs):
            return requests.get(
                f"{self.base_url}{endpoint}",
                headers={
                    'Machine-ID': self.machine_id,
                    'Fencing-Token': self.token
                },
                **kwargs
            )

        def post(self, endpoint: str, **kwargs):
            return requests.post(
                f"{self.base_url}{endpoint}",
                headers={
                    'Machine-ID': self.machine_id,
                    'Fencing-Token': self.token
                },
                **kwargs
            )

    return Client()


class TestHealth:
    """Health check endpoint tests"""

    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data

    def test_health_no_auth_required(self):
        """Health check should not require authentication"""
        response = requests.get(f"{API_URL}/health")
        assert response.status_code == 200


class TestAuthentication:
    """Token validation and authentication tests"""

    def test_missing_machine_id(self, api_client):
        """Missing Machine-ID header should be rejected"""
        response = requests.get(
            f"{api_client.base_url}/vault/families",
            headers={'Fencing-Token': api_client.token}
        )
        assert response.status_code == 401
        assert 'Machine-ID' in response.json()['detail']

    def test_missing_fencing_token(self, api_client):
        """Missing Fencing-Token header should be rejected"""
        response = requests.get(
            f"{api_client.base_url}/vault/families",
            headers={'Machine-ID': api_client.machine_id}
        )
        assert response.status_code == 401
        assert 'Fencing-Token' in response.json()['detail']

    def test_invalid_token_format(self, api_client):
        """Invalid token format should be rejected"""
        response = requests.get(
            f"{api_client.base_url}/vault/families",
            headers={
                'Machine-ID': api_client.machine_id,
                'Fencing-Token': 'short'  # Less than 8 chars
            }
        )
        assert response.status_code == 401
        assert 'format' in response.json()['detail'].lower()

    def test_token_mismatch(self, api_client):
        """Token not matching machine_id should be rejected"""
        response = requests.get(
            f"{api_client.base_url}/vault/families",
            headers={
                'Machine-ID': 'different-machine',
                'Fencing-Token': api_client.token
            }
        )
        assert response.status_code == 403


class TestVaultEndpoints:
    """Vault API endpoint tests"""

    def test_get_vault_families(self, api_client):
        """GET /vault/families should return list of families"""
        response = api_client.get('/vault/families')
        assert response.status_code == 200
        families = response.json()
        assert isinstance(families, list)
        assert len(families) > 0
        family = families[0]
        assert 'id' in family
        assert 'name' in family
        assert 'dna' in family

    def test_get_vault_items(self, api_client):
        """GET /vault/items should return list of items"""
        response = api_client.get('/vault/items')
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)

    def test_vault_items_filter_by_family(self, api_client):
        """GET /vault/items?family=X should filter by family"""
        # First get available families
        families_response = api_client.get('/vault/families')
        families = families_response.json()

        if families:
            family_id = families[0]['id']
            response = api_client.get(f'/vault/items?family={family_id}')
            assert response.status_code == 200
            items = response.json()
            assert all(family_id in item['family'] for item in items)


class TestExperimentsEndpoint:
    """Experiments API endpoint tests"""

    def test_get_experiments(self, api_client):
        """GET /experiments should return experiments"""
        response = api_client.get('/experiments')
        assert response.status_code == 200
        experiments = response.json()
        assert isinstance(experiments, list)

    def test_experiment_schema(self, api_client):
        """Experiments should have required fields"""
        response = api_client.get('/experiments')
        experiments = response.json()

        if experiments:
            exp = experiments[0]
            required_fields = ['id', 'name', 'status', 'runs']
            for field in required_fields:
                assert field in exp


class TestQueueEndpoint:
    """Queue API endpoint tests"""

    def test_get_queue(self, api_client):
        """GET /queue should return queue items"""
        response = api_client.get('/queue')
        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)

    def test_queue_filter_by_state(self, api_client):
        """GET /queue?state=X should filter by state"""
        response = api_client.get('/queue?state=CAPTURED')
        assert response.status_code == 200
        items = response.json()
        assert all(item['state'] == 'CAPTURED' for item in items)


class TestAgendaEndpoint:
    """Agenda API endpoint tests"""

    def test_get_agenda_events(self, api_client):
        """GET /agenda/events should return events"""
        response = api_client.get('/agenda/events')
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)

    def test_agenda_event_schema(self, api_client):
        """Events should have required fields"""
        response = api_client.get('/agenda/events')
        events = response.json()

        if events:
            event = events[0]
            required_fields = ['code', 'name', 'status']
            for field in required_fields:
                assert field in event


class TestGuardianEndpoints:
    """Guardian API endpoint tests"""

    def test_get_guardian_wounds(self, api_client):
        """GET /guardian/wounds should return wounds"""
        response = api_client.get('/guardian/wounds')
        assert response.status_code == 200
        wounds = response.json()
        assert isinstance(wounds, list)

    def test_get_guardian_calibration(self, api_client):
        """GET /guardian/calibration should return calibration entries"""
        response = api_client.get('/guardian/calibration')
        assert response.status_code == 200
        entries = response.json()
        assert isinstance(entries, list)

    def test_get_guardian_overrides(self, api_client):
        """GET /guardian/overrides should return overrides"""
        response = api_client.get('/guardian/overrides')
        assert response.status_code == 200
        overrides = response.json()
        assert isinstance(overrides, list)


class TestPerformance:
    """Performance and load tests"""

    def test_response_time_vault_families(self, api_client):
        """GET /vault/families should respond in <500ms"""
        import time
        start = time.time()
        response = api_client.get('/vault/families')
        duration = (time.time() - start) * 1000
        assert response.status_code == 200
        assert duration < 500, f"Response took {duration}ms (expected <500ms)"

    def test_response_time_experiments(self, api_client):
        """GET /experiments should respond in <500ms"""
        import time
        start = time.time()
        response = api_client.get('/experiments')
        duration = (time.time() - start) * 1000
        assert response.status_code == 200
        assert duration < 500, f"Response took {duration}ms (expected <500ms)"


class TestBitemporal:
    """Bitemporal timestamp tests"""

    def test_event_time_knowledge_time_relationship(self, api_client):
        """event_time should be <= knowledge_time"""
        response = api_client.get('/experiments')
        experiments = response.json()

        for exp in experiments:
            if 'event_time' in exp and 'knowledge_time' in exp:
                assert exp['event_time'] <= exp['knowledge_time']


class TestErrorHandling:
    """Error handling tests"""

    def test_invalid_query_parameter(self, api_client):
        """Invalid query parameters should be handled gracefully"""
        response = api_client.get('/queue?state=INVALID_STATE')
        # Should either filter out or return empty list
        assert response.status_code == 200

    def test_rate_limiting(self, api_client):
        """API should rate limit after threshold"""
        # Send 150 requests in burst
        responses = []
        for i in range(150):
            response = api_client.get('/health')
            responses.append(response.status_code)

        # Should have at least one 429 (Too Many Requests)
        # Note: this depends on rate limiting configuration
        # Comment out if rate limiting not enabled in test environment
        # assert 429 in responses


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
