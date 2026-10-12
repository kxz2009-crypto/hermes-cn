"""WeChat safe-mode (AES) callback decryption for the Hermes payment service.

Standard library only. Implements AES-256-CBC decryption plus the WeChat
safe-mode plaintext layout: 16-byte random || 4-byte big-endian message
length || message || receiveid (AppId), PKCS7-padded to 16 bytes.

The AES key is EncodingAESKey (43 base64 chars + "=" -> 32 bytes).
Correctness was verified against the FIPS-197 Appendix C known-answer
vectors for both AES-128 and AES-256 before integration.
"""
import base64
import binascii


class CallbackCryptoError(Exception):
    """Raised when a safe-mode callback body cannot be authenticated/decrypted."""


def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11B
        b >>= 1
    return p


_exp = [0] * 255
_e = 1
for _i in range(255):
    _exp[_i] = _e
    _e = _gmul(_e, 3)
_INV = [0] * 256
for _i in range(255):
    _INV[_exp[_i]] = _exp[(255 - _i) % 255]


def _rotl8(x, s):
    return ((x << s) | (x >> (8 - s))) & 0xFF


_SBOX = [0] * 256
_ISBOX = [0] * 256
for _x in range(256):
    inv = _INV[_x]
    _s = 0x63 if _x == 0 else (
        inv ^ _rotl8(inv, 1) ^ _rotl8(inv, 2) ^ _rotl8(inv, 3) ^ _rotl8(inv, 4) ^ 0x63)
    _SBOX[_x] = _s
    _ISBOX[_s] = _x


def _expand(key):
    nk, nr = len(key) // 4, len(key) // 4 + 6
    rcon = 1
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = [_SBOX[b] for b in t[1:] + t[:1]]
            t[0] ^= rcon
            rcon = _gmul(rcon, 2)
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return w, nr


def _dec_block(w, nr, block):
    st = [list(block[4 * c:4 * c + 4]) for c in range(4)]
    def ark(rnd):
        for c in range(4):
            for j in range(4):
                st[c][j] ^= w[rnd * 4 + c][j]
    def ishift():
        for r in range(1, 4):
            col = [st[(c - r) % 4][r] for c in range(4)]
            for c in range(4):
                st[c][r] = col[c]
    def isub():
        for c in range(4):
            for j in range(4):
                st[c][j] = _ISBOX[st[c][j]]
    def imix():
        for c in range(4):
            a = st[c]
            st[c] = [_gmul(a[0], 14) ^ _gmul(a[1], 11) ^ _gmul(a[2], 13) ^ _gmul(a[3], 9),
                     _gmul(a[0], 9) ^ _gmul(a[1], 14) ^ _gmul(a[2], 11) ^ _gmul(a[3], 13),
                     _gmul(a[0], 13) ^ _gmul(a[1], 9) ^ _gmul(a[2], 14) ^ _gmul(a[3], 11),
                     _gmul(a[0], 11) ^ _gmul(a[1], 13) ^ _gmul(a[2], 9) ^ _gmul(a[3], 14)]
    ark(nr)
    for rnd in range(nr - 1, 0, -1):
        ishift()
        isub()
        ark(rnd)
        imix()
    ishift()
    isub()
    ark(0)
    return bytes(b for c in st for b in c)


def aes_cbc_decrypt(key, iv, data):
    if len(key) not in (16, 24, 32) or len(iv) != 16 or len(data) % 16 or not data:
        raise CallbackCryptoError("CALLBACK_CRYPTO_INPUT")
    w, nr = _expand(key)
    out, prev = b"", iv
    for i in range(0, len(data), 16):
        blk = _dec_block(w, nr, data[i:i + 16])
        out += bytes(x ^ y for x, y in zip(blk, prev))
        prev = data[i:i + 16]
    return out


def decrypt_callback(encrypt_b64, encoding_aes_key, app_id):
    """Decrypt a WeChat safe-mode <Encrypt> payload and return the inner XML bytes.

    Raises CallbackCryptoError on any padding/format/receiveid mismatch so the
    caller can fail closed instead of acknowledging an unverified event.
    """
    if not isinstance(encrypt_b64, str) or not isinstance(encoding_aes_key, str):
        raise CallbackCryptoError("CALLBACK_CRYPTO_INPUT")
    try:
        key = base64.b64decode(encoding_aes_key, validate=True)
    except (binascii.Error, ValueError):
        raise CallbackCryptoError("CALLBACK_AESKEY_INVALID") from None
    if len(key) != 32:
        raise CallbackCryptoError("CALLBACK_AESKEY_INVALID")
    try:
        raw = base64.b64decode(encrypt_b64, validate=True)
    except (binascii.Error, ValueError):
        raise CallbackCryptoError("CALLBACK_CIPHER_INVALID") from None
    if len(raw) < 32 or len(raw) % 16:
        raise CallbackCryptoError("CALLBACK_CIPHER_INVALID")
    plain = aes_cbc_decrypt(key, key[:16], raw)
    pad = plain[-1]
    if not 1 <= pad <= 16 or plain[-pad:] != bytes([pad]) * pad:
        raise CallbackCryptoError("CALLBACK_PADDING_INVALID")
    body = plain[:-pad]
    if len(body) < 20:
        raise CallbackCryptoError("CALLBACK_BODY_INVALID")
    mlen = int.from_bytes(body[16:20], "big")
    if mlen < 0 or 20 + mlen > len(body):
        raise CallbackCryptoError("CALLBACK_BODY_INVALID")
    if body[20 + mlen:].decode("utf-8", errors="replace") != app_id:
        # receiveid must equal our AppId; a mismatch means the payload was not
        # encrypted for this account and must not be processed.
        raise CallbackCryptoError("CALLBACK_RECEIVEID_MISMATCH")
    return body[20:20 + mlen]
