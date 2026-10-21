# Authored-by: Perplexity (AI assistant by Perplexity AI), model family: Perplexity
import unittest

from api import users


class TestUsers(unittest.TestCase):
    def test_get_user_known(self):
        self.assertEqual(users.get_user(1)["name"], "Ada Lovelace")

    def test_get_user_unknown_returns_none(self):
        self.assertIsNone(users.get_user(999))

    def test_list_user_ids_sorted(self):
        self.assertEqual(users.list_user_ids(), [1, 2, 3])

    def test_user_schema_keys_locked(self):
        keys = {"id", "name", "email", "bio", "avatar", "photos"}
        for u in users.USERS.values():
            self.assertEqual(set(u), keys)


if __name__ == "__main__":
    unittest.main()
