import unittest

import prepdocslib.blobmanager  # noqa
import prepdocslib.embeddings  # noqa
import prepdocslib.filestrategy  # noqa
import prepdocslib.listfilestrategy  # noqa
import prepdocslib.pdfparser  # noqa
import prepdocslib.searchmanager  # noqa
import prepdocslib.strategy  # noqa
import prepdocslib.textsplitter  # noqa


# Currently just verifying imports.
class PrepdocsLibVerificationTest(unittest.TestCase):
    ...


if __name__ == "__main__":
    unittest.main()
