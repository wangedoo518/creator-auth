import time
import unittest

from creator_auth.crypto import sign_json, verify_signed_json


class CryptoTest(unittest.TestCase):
    def test_sign_and_verify_json(self):
        token = sign_json({"sub": "usr_1", "exp": int(time.time()) + 60}, "secret")
        payload = verify_signed_json(token, "secret")
        self.assertEqual(payload["sub"], "usr_1")

    def test_expired_token_rejected(self):
        token = sign_json({"sub": "usr_1", "exp": int(time.time()) - 1}, "secret")
        with self.assertRaises(ValueError):
            verify_signed_json(token, "secret")


if __name__ == "__main__":
    unittest.main()
