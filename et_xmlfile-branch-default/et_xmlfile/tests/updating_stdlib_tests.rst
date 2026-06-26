======================
Updating stdlib tests
======================

The ``incremental_tree.py`` code extends many classes defined by Python's
``xml.etree.ElementTree`` adding additional functionality with regards to how
these trees are serialised. Serialising xml is not a trivial task so we
leverage the standard library tests to take advantage of the ~4600 loc of tests
to ensure the implementation in this package is working as expected.

An overview:

* We vendor the latest tests from a Python release in the the ``tests/_vendor``
  directory.
* ``pytest`` is configured to ignore the tests in ``tests/_vendor`` so we can apply
  some shims and workarounds to support mulitple versions of Pythons.
* Modifications to the stdlib ``TestCase`` classes are created in subclasses of
  the those TestCases in the ``tests/stdlib_base_tests.py`` file. This keeps
  the vendored code clean to allow easy updates to newer releases of cPython.
* The test runner will find these modified test cases via the
  ``tests/test_incremental_tree_with_stdlib_tests.py`` file.


# Updating the stdlib tests

As cPython implements new features and adds bug fixes, the snapshot of the
tests we've vendored from the cPython project (under the ``tests/_vendor``
directory) may start to fail for more recent versions of cPython.

To update the vendored tests:

* Clone the cPython repository
* Checkout the latest release tag. It's important it is a release tag so that
  we don't include tests that aren't released yet as that may cause test
  failures.
* Copy the ``Lib/test/test_xml_etree.py`` file over the
  ``tests/_vendor/teststest_xml_etree.py`` file in this repository.
* Changes to the local ``teststest_xml_etree.py`` are kept to a minimum but there
  are a few required modifications. They are surrounded by the comments:

    ```
    # et_xmlfile change: ...
    <changes>
    # end et_xmlfile change
    ```

    Check the hg diff after replacing the local ``test_xml_etree.py`` with the
    newer version to find any of these sections that may have been removed and
    readd them.
* Run ``pytest`` for supported python versions. Look for test failures due to new
  features or code changes and update the corresponding classes in
  ``stdlib_base_tests.py`` to override the tests in ``test_xml_etree.py``. This can
  mean copying the old version of a test and running that on older versions of
  Python while retaining the newer test for the Pythons that support that.
* Don't forget to check pypy :)
