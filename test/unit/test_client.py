"""test_client.py"""
# pylint: disable=missing-docstring,line-too-long,protected-access

from unittest import TestCase, main
import itertools
import json

from jsonschema import ValidationError
from testfixtures import LogCapture

from jsonrpcclient import Request, config, exceptions
from jsonrpcclient.client import Client


class DummyClient(Client):
    """A dummy class for testing the abstract Client class"""
    def _send_message(self, request):
        return 15


class TestClient(TestCase):

    def setUp(self):
        Request.id_iterator = itertools.count(1)
        self.client = DummyClient('http://non-existant:80/')

    def tearDown(self):
        config.validate = True


class TestLogging(TestClient):

    def test_request(self):
        with LogCapture() as l:
            self.client._log_request('{"jsonrpc": "2.0", "method": "go"}')
        l.check(('jsonrpcclient.client.request', 'INFO', '{"jsonrpc": "2.0", "method": "go"}'))

    def test_response(self):
        with LogCapture() as l:
            self.client._log_response('{"jsonrpc": "2.0", "result": 5, "id": 1}')
        l.check(('jsonrpcclient.client.response', 'INFO', '{"jsonrpc": "2.0", "result": 5, "id": 1}'))


class TestSend(TestClient):

    def test(self):
        self.assertEqual(15, self.client.send({'jsonrpc': '2.0', 'method': 'out', 'id': 1}))


class TestRequest(TestClient):

    def test(self):
        self.assertEqual(15, self.client.request('multiply', 3, 5))


class TestNotify(TestClient):

    def test(self):
        self.assertEqual(15, self.client.notify('multiply', 3, 5))


class TestDirect(TestClient):

    def test_alternate_usage(self):
        self.assertEqual(15, self.client.multiply(3, 5))


class TestProcessResponse(TestClient):
    # pylint: disable=protected-access

    def test_none(self):
        response = None
        self.assertEqual(None, self.client._process_response(response))

    def test_empty_string(self):
        response = ''
        self.assertEqual(None, self.client._process_response(response))

    def test_valid_json(self):
        response = {'jsonrpc': '2.0', 'result': 5, 'id': 1}
        self.assertEqual(5, self.client._process_response(response))

    def test_valid_json_null_id(self):
        response = {'jsonrpc': '2.0', 'result': 5, 'id': None}
        self.assertEqual(5, self.client._process_response(response))

    def test_valid_string(self):
        response = '{"jsonrpc": "2.0", "result": 5, "id": 1}'
        self.assertEqual(5, self.client._process_response(response))

    def test_invalid_json(self):
        response = '{dodgy}'
        with self.assertRaises(exceptions.ParseResponseError):
            self.client._process_response(response)

    def test_invalid_jsonrpc(self):
        response = {'json': '2.0'}
        with self.assertRaises(ValidationError):
            self.client._process_response(response)

    def test_invalid_jsonrpc_no_validation(self):
        config.validate = False
        response = {'json': '2.0'}
        self.client._process_response(response)

    def test_error_response(self):
        response = {'jsonrpc': '2.0', 'error': {'code': -32000, 'message': 'Not Found'}, 'id': None}
        with self.assertRaises(exceptions.ReceivedErrorResponse) as e:
            self.client._process_response(response)
        self.assertEqual(e.exception.code, -32000)
        self.assertEqual(e.exception.message, 'Not Found')
        self.assertEqual(e.exception.data, None)

    def test_error_response_with_data(self):
        response = {'jsonrpc': '2.0', 'error': {'code': -32000, 'message': 'Not Found', 'data': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit'}, 'id': None}
        with self.assertRaises(exceptions.ReceivedErrorResponse) as e:
            self.client._process_response(response)
        self.assertEqual(e.exception.code, -32000)
        self.assertEqual(e.exception.message, 'Not Found')
        self.assertEqual(e.exception.data, 'Lorem ipsum dolor sit amet, consectetur adipiscing elit')

    def test_batch(self):
        response = [
            {'jsonrpc': '2.0', 'result': 5, 'id': 1},
            {'jsonrpc': '2.0', 'result': None, 'id': 2},
            {'jsonrpc': '2.0', 'error': {'code': -32000, 'message': 'Not Found'}, 'id': 3}]
        self.assertEqual(response, self.client._process_response(response))

    def test_batch_string(self):
        response = '[ \
            {"jsonrpc": "2.0", "result": 5, "id": 1}, \
            {"jsonrpc": "2.0", "result": null, "id": 2}, \
            {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Not Found"}, "id": 3}]'
        self.assertEqual(json.loads(response), self.client._process_response(response))


if __name__ == '__main__':
    main()
