# Test et_xmlfile.incremental_tree using Python's Lib/test/test_xml_etree.py tests
#
# This imports the test from the python installation that is running the test
# and might be quite flakey as python changes. It is good as a sanity check but
# should be disabled if it starts causing too many headaches.
#
# Hint: If you need to debug any of the stdlib tests in detail, create a new
# test file in this repository and copy the failing test over to play with.
import sys
import unittest

from . import stdlib_base_tests


def make_modified_tests():
    class ElementTreeTest(stdlib_base_tests.ElementTreeTest):
        @unittest.skip("3.8 has incompatible xml declaration case")
        def test_tostring_xml_declaration_cases(self):
            super().test_tostring_xml_declaration_cases()

        @unittest.skip("3.8 has incompatible xml declaration case")
        def test_tostring_xml_declaration_unicode_encoding(self):
            super().test_tostring_xml_declaration_unicode_encoding()

        @unittest.skip("3.8 has incompatible xml declaration case")
        def test_tostringlist_xml_declaration(self):
            super().test_tostringlist_xml_declaration()

    if sys.version_info[:2] == (3, 10):
        class IOTest(stdlib_base_tests.IOTest):
            @unittest.skip(
                "Fixed by: gh-91810: Fix regression with writing an XML declaration with encoding='unicode'"
            )
            def test_write_to_text_file(self):
                pass
    else:
        IOTest = stdlib_base_tests.IOTest

    return (
        ElementTreeTest,
        IOTest,
    )


stdlib_base_tests.install_tests(globals(), make_modified_tests())


def setUpModule():
    import et_xmlfile.tests.stdlibshim
    stdlib_base_tests.setUpModule(module=et_xmlfile.tests.stdlibshim)


def tearDownModule():
    stdlib_base_tests.tearDownModule()
