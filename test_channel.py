"""
Cross-language interop tests for the Hospital-MP secure channel.

Asserts that Python's AES-256-GCM (via the `cryptography` package) agrees
with the constants in scripts/channel-vector.json at the umbrella root —
the same constants are baked into the Rust, Go, TypeScript, and Java tests.
"""

import base64
import json
import os
import sys

import pytest

# Channel reads BACKEND_CHANNEL_KEY at module import via init_from_env,
# so set it before importing.
VEC_KEY_B64 = "ASNFZ4mrze8BI0VniavN7wEjRWeJq83vASNFZ4mrze8="
VEC_IV_B64 = "CgsMDQ4PEBESExQV"
VEC_PLAINTEXT_B64 = "eyJoZWxsbyI6IndvcmxkIiwidGVuYW50IjoiZGVtbyIsIm4iOjQyfQ=="
VEC_CIPHERTEXT_B64 = "HA/jiyD9Ct203QHgmTq3vFe0VYYm5ynGin9Xn7B3QVGAZkDXaJLrEQ=="
VEC_TAG_B64 = "XjADTXgk4M//4jqs0Cu05g=="


@pytest.fixture(autouse=True)
def _enabled_channel():
    os.environ["BACKEND_CHANNEL_KEY"] = VEC_KEY_B64
    os.environ["BACKEND_CHANNEL_ENABLED"] = "true"
    # Force a fresh import of channel so init_from_env runs with the env above.
    sys.modules.pop("channel", None)
    import channel  # noqa: WPS433 — re-import is intentional
    channel.init_from_env()
    yield channel
    os.environ.pop("BACKEND_CHANNEL_KEY", None)
    os.environ.pop("BACKEND_CHANNEL_ENABLED", None)
    sys.modules.pop("channel", None)


def test_vector_decrypts_to_known_plaintext(_enabled_channel):
    channel = _enabled_channel
    env = {"v": 1, "iv": VEC_IV_B64, "ct": VEC_CIPHERTEXT_B64, "tag": VEC_TAG_B64}
    plain = channel.open_envelope(env)
    expected = base64.b64decode(VEC_PLAINTEXT_B64)
    assert plain == expected


def test_roundtrip_preserves_payload(_enabled_channel):
    channel = _enabled_channel
    payload = b'{"session":"abc","n":7,"msg":"hola"}'
    env = channel.seal(payload)
    assert env["v"] == 1
    assert channel.open_envelope(env) == payload


def test_tampered_ciphertext_fails(_enabled_channel):
    channel = _enabled_channel
    raw = bytearray(base64.b64decode(VEC_CIPHERTEXT_B64))
    raw[0] ^= 0x01
    env = {
        "v": 1,
        "iv": VEC_IV_B64,
        "ct": base64.b64encode(bytes(raw)).decode("ascii"),
        "tag": VEC_TAG_B64,
    }
    with pytest.raises(channel.ChannelError) as exc:
        channel.open_envelope(env)
    assert "AEAD" in str(exc.value)


def test_seal_json_passthrough_when_disabled():
    # Force-disable the channel for this test only.
    os.environ.pop("BACKEND_CHANNEL_KEY", None)
    os.environ["BACKEND_CHANNEL_ENABLED"] = "false"
    sys.modules.pop("channel", None)
    import channel  # noqa: WPS433
    channel.init_from_env()
    body, ct, encrypted = channel.seal_json({"a": 1})
    assert not encrypted
    assert ct == "application/json"
    assert json.loads(body) == {"a": 1}
