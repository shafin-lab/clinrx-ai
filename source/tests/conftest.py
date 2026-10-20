"""Capture exact executed synthetic inputs/results; not application/API captures."""
import hashlib
import json
import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def capture_contract_calls(request, monkeypatch):
    folder = os.environ.get('RF2_HARNESS_CAPTURE_DIR')
    module = request.module
    if not folder or not hasattr(module, 'evaluate'):
        yield
        return
    directory = Path(folder)
    directory.mkdir(parents=True, exist_ok=True)
    real = module.evaluate
    calls = []
    def captured(raw):
        # Bytes are immutable. Serialize the returned object immediately before test mutation.
        result = real(raw)
        n = len(calls) + 1
        key = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:20] + f'-{n:03}'
        input_path = directory / (key + '.input.bin')
        output_path = directory / (key + '.output.json')
        input_path.write_bytes(raw)
        output_path.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
        calls.append({'input':input_path.name,'input_sha256':hashlib.sha256(raw).hexdigest(),'output':output_path.name,'output_sha256':hashlib.sha256(output_path.read_bytes()).hexdigest()})
        return result
    monkeypatch.setattr(module, 'evaluate', captured)
    yield
    record = {'test':request.node.nodeid,'calls':calls,'scope':'in-memory synthetic harness calls, not clinical API or runtime observations'}
    name = hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:20]
    (directory / (name + '.index.json')).write_text(json.dumps(record, indent=2) + '\n')
