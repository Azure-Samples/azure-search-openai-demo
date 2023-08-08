import unittest

from app import app 
app.testing = True

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_model(self, approach):
        app.run(debug = True)

if __name__ == "__main__":
    unittest.main()