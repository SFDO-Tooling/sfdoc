from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def gen_private_key():
    key = rsa.generate_private_key(
        backend=default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return private_key.decode("utf-8")


def process_key(key):
    """Ensure key string uses newlines instead of spaces."""
    KEY_BEGIN = "-----BEGIN RSA PRIVATE KEY-----"
    KEY_END = "-----END RSA PRIVATE KEY-----"
    key_out = KEY_BEGIN + "\n"
    for item in key.replace(KEY_BEGIN, "").replace(KEY_END, "").split():
        key_out += item + "\n"
    key_out += KEY_END
    return key_out
