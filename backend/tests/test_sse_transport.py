"""Verify connection reuse with a real WSGI socket, not only Flask's test client."""
from threading import Thread

import requests
from flask import Flask, Response, request
from werkzeug.serving import make_server

from app.services.llm_stream import sse_headers, sse_event


def test_sse_completion_does_not_strand_next_request_on_conflicting_keep_alive():
    app = Flask(__name__)

    @app.post('/stream')
    def stream():
        _ = request.get_json()
        return Response(iter([sse_event({'type':'done','reply':'verified'})]), headers=sse_headers())

    @app.post('/next')
    def next_request():
        return {'received':request.get_json()['request_id']}

    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with requests.Session() as client:
            base = f'http://127.0.0.1:{server.server_port}'
            response = client.post(base + '/stream', json={'message':'Python'}, timeout=3)
            assert response.status_code == 200 and 'verified' in response.text
            assert response.headers.get('Connection', '').lower() == 'close'
            response = client.post(base + '/next', json={'request_id':'same-turn'}, timeout=3)
            assert response.status_code == 200 and response.json()['received'] == 'same-turn'
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
