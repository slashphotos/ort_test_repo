import io
import platform
import sys
import types
import unittest
import unittest.case

from et_xmlfile.tests._vendor.test import test_xml_etree
from et_xmlfile.tests._vendor.test.test_xml_etree import *  # noqa: F401, F403


old_serialize = test_xml_etree.serialize


def is_version_before(*versions):
    sys_ver = sys.version_info[:3]
    for version in sorted(versions):
        if sys_ver[:2] == version[:2]:
            # Check for point release eg. (3, 12, 10)
            if sys_ver < version:
                return True
    if sys_ver < min(versions):
        return True
    return False


def serialize(elem, **options):
    if "root_ns_only" not in options:
        options["root_ns_only"] = True

    return old_serialize(elem, **options)


def install_tests(mod_globals, modified_tests=None, more_skip_classes=None):
    # Test classes should have __module__ referring to this module.
    # We want to skip the module test as that tests for equivalence between
    # python's xml.etree.ElementTree and _elementtree modules which doesn't
    # apply here.
    skip_test_classes = [
        "ModuleTest",
        "C14NTest",
    ]
    if more_skip_classes:
        skip_test_classes.extend(more_skip_classes)

    registered_tests = []
    if modified_tests:
        for test_cls in modified_tests:
            name = test_cls.__name__
            assert name not in mod_globals
            registered_tests.append(name)
            mod_globals[name] = test_cls

    for name, base in globals().items():
        if name in skip_test_classes or name in registered_tests:
            continue
        if isinstance(base, type) and issubclass(base, unittest.TestCase):
            class Temp(base):
                pass
            Temp.__name__ = Temp.__qualname__ = name
            Temp.__module__ = mod_globals["__name__"]
            assert name not in mod_globals
            mod_globals[name] = Temp


class ElementTreeTest(test_xml_etree.ElementTreeTest):
    if sys.version_info[:2] < (3, 14):
        def assertHasAttr(self, obj, name, msg=None):
            if not hasattr(obj, name):
                if isinstance(obj, types.ModuleType):
                    standardMsg = f'module {obj.__name__!r} has no attribute {name!r}'
                elif isinstance(obj, type):
                    standardMsg = f'type object {obj.__name__!r} has no attribute {name!r}'
                else:
                    standardMsg = f'{type(obj).__name__!r} object has no attribute {name!r}'
                self.fail(self._formatMessage(msg, standardMsg))

    @unittest.skipIf(
        sys.version_info[:2] < (3, 13, 6),
        "Added in 3.13.6"
    )
    def test_setroot(self):
        super().test_setroot()

    @unittest.skipIf(
        sys.version_info[:2] < (3, 13, 6),
        "Added in 3.13.6"
    )
    def test_constructor(self):
        super().test_constructor()

    def _test_simpleops_pre_3_13(self):
        # Basic method sanity checks.

        elem = test_xml_etree.ET.XML("<body><tag/></body>")
        self.serialize_check(elem, '<body><tag /></body>')
        e = test_xml_etree.ET.Element("tag2")
        elem.append(e)
        self.serialize_check(elem, '<body><tag /><tag2 /></body>')
        elem.remove(e)
        self.serialize_check(elem, '<body><tag /></body>')
        elem.insert(0, e)
        self.serialize_check(elem, '<body><tag2 /><tag /></body>')
        elem.remove(e)
        elem.extend([e])
        self.serialize_check(elem, '<body><tag /><tag2 /></body>')
        elem.remove(e)
        elem.extend(iter([e]))
        self.serialize_check(elem, '<body><tag /><tag2 /></body>')
        elem.remove(e)

        element = test_xml_etree.ET.Element("tag", key="value")
        self.serialize_check(element, '<tag key="value" />')  # 1
        subelement = test_xml_etree.ET.Element("subtag")
        element.append(subelement)
        self.serialize_check(element, '<tag key="value"><subtag /></tag>')  # 2
        element.insert(0, subelement)
        self.serialize_check(element,
                             '<tag key="value"><subtag /><subtag /></tag>')  # 3
        element.remove(subelement)
        self.serialize_check(element, '<tag key="value"><subtag /></tag>')  # 4
        element.remove(subelement)
        self.serialize_check(element, '<tag key="value" />')  # 5
        with self.assertRaises(ValueError) as cm:
            element.remove(subelement)
        self.assertEqual(str(cm.exception), 'list.remove(x): x not in list')
        self.serialize_check(element, '<tag key="value" />')  # 6
        element[0:0] = [subelement, subelement, subelement]
        self.serialize_check(element[1], '<subtag />')
        self.assertEqual(element[1:9], [element[1], element[2]])
        self.assertEqual(element[:9:2], [element[0], element[2]])
        del element[1:2]
        self.serialize_check(element,
                             '<tag key="value"><subtag /><subtag /></tag>')

    @unittest.skipIf(
        (
            platform.python_implementation() == "PyPy"
            and sys.version_info[:3] < (3, 12)
        ),
        "Functionality reverted but not picked up by PyPy yet",
    )
    def test_simpleops(self):
        if sys.version_info[:2] < (3, 14):
            self._test_simpleops_pre_3_13()
        else:
            super().test_simpleops()

    def _test_iterparse_pre_3_13(self):
        # Test iterparse interface.

        iterparse = test_xml_etree.ET.iterparse

        context = iterparse(test_xml_etree.SIMPLE_XMLFILE)
        self.assertIsNone(context.root)
        action, elem = next(context)
        self.assertIsNone(context.root)
        self.assertEqual((action, elem.tag), ('end', 'element'))
        self.assertEqual([(action, elem.tag) for action, elem in context], [
                ('end', 'element'),
                ('end', 'empty-element'),
                ('end', 'root'),
            ])
        self.assertEqual(context.root.tag, 'root')

        context = iterparse(test_xml_etree.SIMPLE_NS_XMLFILE)
        self.assertEqual([(action, elem.tag) for action, elem in context], [
                ('end', '{namespace}element'),
                ('end', '{namespace}element'),
                ('end', '{namespace}empty-element'),
                ('end', '{namespace}root'),
            ])

        events = ()
        context = iterparse(test_xml_etree.SIMPLE_XMLFILE, events)
        self.assertEqual([(action, elem.tag) for action, elem in context], [])

        events = ()
        context = iterparse(test_xml_etree.SIMPLE_XMLFILE, events=events)
        self.assertEqual([(action, elem.tag) for action, elem in context], [])

        events = ("start", "end")
        context = iterparse(test_xml_etree.SIMPLE_XMLFILE, events)
        self.assertEqual([(action, elem.tag) for action, elem in context], [
                ('start', 'root'),
                ('start', 'element'),
                ('end', 'element'),
                ('start', 'element'),
                ('end', 'element'),
                ('start', 'empty-element'),
                ('end', 'empty-element'),
                ('end', 'root'),
            ])

        events = ("start", "end", "start-ns", "end-ns")
        context = iterparse(test_xml_etree.SIMPLE_NS_XMLFILE, events)
        self.assertEqual(
            [
                (action, elem.tag)
                if action in ("start", "end") else (action, elem)
                for action, elem in context
            ], [
                ('start-ns', ('', 'namespace')),
                ('start', '{namespace}root'),
                ('start', '{namespace}element'),
                ('end', '{namespace}element'),
                ('start', '{namespace}element'),
                ('end', '{namespace}element'),
                ('start', '{namespace}empty-element'),
                ('end', '{namespace}empty-element'),
                ('end', '{namespace}root'),
                ('end-ns', None),
            ]
        )

        events = ('start-ns', 'end-ns')
        context = iterparse(io.StringIO(r"<root xmlns=''/>"), events)
        res = [action for action, elem in context]
        self.assertEqual(res, ['start-ns', 'end-ns'])

        events = ("start", "end", "bogus")
        with open(test_xml_etree.SIMPLE_XMLFILE, "rb") as f:
            with self.assertRaises(ValueError) as cm:
                iterparse(f, events)
            self.assertFalse(f.closed)
        self.assertEqual(str(cm.exception), "unknown event 'bogus'")

        with test_xml_etree.warnings_helper.check_no_resource_warning(self):
            with self.assertRaises(ValueError) as cm:
                iterparse(test_xml_etree.SIMPLE_XMLFILE, events)
            self.assertEqual(str(cm.exception), "unknown event 'bogus'")
            del cm

        source = io.BytesIO(
            b"<?xml version='1.0' encoding='iso-8859-1'?>\n"
            b"<body xmlns='http://&#233;ffbot.org/ns'\n"
            b"      xmlns:cl\xe9='http://effbot.org/ns'>text</body>\n")
        events = ("start-ns",)
        context = iterparse(source, events)
        self.assertEqual([(action, elem) for action, elem in context], [
                ('start-ns', ('', 'http://\xe9ffbot.org/ns')),
                ('start-ns', ('cl\xe9', 'http://effbot.org/ns')),
            ])

        source = io.StringIO("<document />junk")
        it = iterparse(source)
        action, elem = next(it)
        self.assertEqual((action, elem.tag), ('end', 'document'))
        with self.assertRaises(test_xml_etree.ET.ParseError) as cm:
            next(it)
        self.assertEqual(
            str(cm.exception),
            'junk after document element: line 1, column 12',
        )

        self.addCleanup(test_xml_etree.os_helper.unlink, test_xml_etree.TESTFN)
        with open(test_xml_etree.TESTFN, "wb") as f:
            f.write(b"<document />junk")
        it = iterparse(test_xml_etree.TESTFN)
        action, elem = next(it)
        self.assertEqual((action, elem.tag), ('end', 'document'))
        with test_xml_etree.warnings_helper.check_no_resource_warning(self):
            with self.assertRaises(test_xml_etree.ET.ParseError) as cm:
                next(it)
            self.assertEqual(
                str(cm.exception),
                'junk after document element: line 1, column 12',
            )
            del cm, it

        # Not exhausting the iterator still closes the resource (bpo-43292)
        with test_xml_etree.warnings_helper.check_no_resource_warning(self):
            it = iterparse(test_xml_etree.TESTFN)
            del it

        with self.assertRaises(FileNotFoundError):
            iterparse("nonexistent")

    def test_iterparse(self):
        if sys.version_info[:2] < (3, 9):
            pass
        elif sys.version_info[:2] < (3, 13):
            self._test_iterparse_pre_3_13()
        else:
            super().test_iterparse()

    @unittest.skipIf(
        sys.version_info[:2] < (3, 13),
        "iterparse close not implemented"
    )
    def test_iterparse_close(self):
        super().test_iterparse_close()

    def _test_html_empty_elems_serialization_pre_3_11(self):
        # issue 15970
        # from http://www.w3.org/TR/html401/index/elements.html
        for element in ['AREA', 'BASE', 'BASEFONT', 'BR', 'COL', 'FRAME', 'HR',
                        'IMG', 'INPUT', 'ISINDEX', 'LINK', 'META', 'PARAM']:
            for elem in [element, element.lower()]:
                expected = '<%s>' % elem
                serialized = serialize(test_xml_etree.ET.XML('<%s />' % elem), method='html')
                self.assertEqual(serialized, expected)
                serialized = serialize(
                    test_xml_etree.ET.XML('<%s></%s>' % (elem, elem)),
                    method='html',
                )
                self.assertEqual(serialized, expected)

    def test_html_empty_elems_serialization(self):
        if sys.version_info[:2] < (3, 11):
            self._test_html_empty_elems_serialization_pre_3_11()
        else:
            super().test_html_empty_elems_serialization()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "Fails in py3.8")
    def test_attrib(self):
        super().test_attrib()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "py3.8 doesn't have indent")
    def test_indent(self):
        super().test_indent()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "py3.8 doesn't have indent")
    def test_indent_level(self):
        super().test_indent_level()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "py3.8 doesn't have indent")
    def test_indent_space(self):
        super().test_indent_space()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "py3.8 doesn't have indent")
    def test_indent_space_caching(self):
        super().test_indent_space_caching()

    @unittest.skipIf(sys.version_info[:3] < (3, 9, 11), "Test / change introduced in 3.9.11")
    def test_initialize_parser_without_target(self):
        super().test_initialize_parser_without_target()


class BasicElementTest(test_xml_etree.BasicElementTest):
    @unittest.skipIf(
        platform.python_implementation() == "PyPy",
        "Fails on pypy",
    )
    def test_pickle_issue18997(self):
        super().test_pickle_issue18997()


class BugsTest(test_xml_etree.BugsTest):
    @unittest.skipIf(sys.version_info[:2] < (3, 9), "Fails in py3.8")
    def test_39495_treebuilder_start(self):
        super().test_39495_treebuilder_start()

    @unittest.skipIf(
        platform.python_implementation() == "PyPy",
        "sys.getrefcount doesn't exist",
    )
    def test_bug_xmltoolkit63(self):
        super().test_bug_xmltoolkit63()

    @unittest.skipIf(
        sys.version_info[:3] < (3, 12, 6),
        "Changed in 3.12.6",
    )
    def test_issue123213_correct_extend_exception(self):
        super().test_issue123213_correct_extend_exception()


class XIncludeTest(test_xml_etree.XIncludeTest):
    @unittest.skipIf(sys.version_info[:2] < (3, 9), "Fails in py3.8")
    def test_xinclude_failures(self):
        super().test_xinclude_failures()

    @unittest.skipIf(sys.version_info[:2] < (3, 9), "Fails in py3.8")
    def test_xinclude_repeated(self):
        super().test_xinclude_repeated()


# Need for _test_findall_with_mutating_pre_3_12_5_or_3_13_4
class MutatingElementPath(str):
    def __new__(cls, elem, *args):
        self = str.__new__(cls, *args)
        self.elem = elem
        return self

    def __eq__(self, o):
        del self.elem[:]
        return True


MutatingElementPath.__hash__ = str.__hash__


class BadElementPathTest(test_xml_etree.BadElementPathTest):
    @unittest.skipIf(
        sys.version_info[:2] < (3, 11),
        "Test fails / not available in Python 3.10 and lower.",
    )
    def test_findtext_with_falsey_text_attribute(self):
        super().test_findtext_with_falsey_text_attribute()

    def _test_findall_with_mutating_pre_3_12_10_or_3_13_4(self):
        e = test_xml_etree.ET.Element('foo')
        e.extend([test_xml_etree.ET.Element('bar')])
        e.findall(MutatingElementPath(e, 'x'))

    def test_findall_with_mutating(self):
        if is_version_before((3, 12, 10), (3, 13, 4)):
            self._test_findall_with_mutating_pre_3_12_10_or_3_13_4()
        else:
            super().test_findall_with_mutating()


class BadElementTest(test_xml_etree.BadElementTest):
    @unittest.skipIf(
        sys.version_info[:3] < (3, 13, 4),
        "Crashes python before fix",
    )
    def test_deepcopy_clear(self):
        super().test_deepcopy_clear()

    @unittest.skipIf(
        sys.version_info[:3] < (3, 13, 4),
        "Crashes python before fix",
    )
    def test_deepcopy_grow(self):
        super().test_deepcopy_grow()

    @unittest.skipIf(
        is_version_before((3, 12, 10), (3, 13, 4)),
        "Only fixed in 3.12.10 and after",
    )
    def test_remove_with_clear_assume_existing(self):
        super().test_remove_with_clear_assume_existing()

    @unittest.skipIf(
        is_version_before((3, 12, 10), (3, 13, 4)),
        "Only fixed in 3.12.10 and after",
    )
    def test_remove_with_clear_assume_missing(self):
        super().test_remove_with_clear_assume_missing()

    @unittest.skipIf(
        is_version_before((3, 12, 10), (3, 13, 4)),
        "Only fixed in 3.12.10 and after",
    )
    def test_remove_with_mutate_root_assume_existing(self):
        super().test_remove_with_mutate_root_assume_existing()


class NoAcceleratorTest(test_xml_etree.NoAcceleratorTest):
    @unittest.skipIf(
        sys.version_info[:2] < (3, 11),
        "Workaround for changes in import_fresh_module since 3.11 breaks some pyET tests",
    )
    def test_correct_import_pyET(self):
        super().test_correct_import_pyET()


class ElementFindTest(test_xml_etree.ElementFindTest):
    @unittest.skipIf(
        sys.version_info[:2] < (3, 10),
        "Support and tests were added for xpath != operator",
    )
    def test_findall(self):
        super().test_findall()


@unittest.skip("incremental_tree doesn't change the XMLPullParser so skip those tests")
class XMLPullParserTest(test_xml_etree.XMLPullParserTest):
    pass


class BoolTest(test_xml_etree.BoolTest):

    def _test_warning_pre_3_12_5(self):
        e = test_xml_etree.ET.fromstring('<a style="new"></a>')
        msg = (
            r"Testing an element's truth value will raise an exception in "
            r"future versions.  "
            r"Use specific 'len\(elem\)' or 'elem is not None' test instead.")
        with self.assertWarnsRegex(DeprecationWarning, msg):
            result = bool(e)
        # Emulate prior behavior for now
        self.assertIs(result, False)

        # Element with children
        test_xml_etree.ET.SubElement(e, 'b')
        with self.assertWarnsRegex(DeprecationWarning, msg):
            new_result = bool(e)
        self.assertIs(new_result, True)

    def test_warning(self):
        if sys.version_info[:2] < (3, 12):
            pass
        elif sys.version_info[:3] < (3, 12, 5):
            self._test_warning_pre_3_12_5()
        else:
            super().test_warning()


class ElementSlicingTest(test_xml_etree.ElementSlicingTest):
    @unittest.skipIf(
        sys.version_info[:3] < (3, 12, 6),
        "Changed in 3.12.6",
    )
    def test_issue123213_setslice_exception(self):
        super().test_issue123213_setslice_exception()


def setUpModule_old(module=None):
    # Adapted from test_xml_etree to avoid the `import_fresh_module` whose
    # implementation changed in older versions.

    # When invoked without a module, runs the Python ET tests by loading pyET.
    # Otherwise, uses the given module as the ET.
    # global pyET
    # pyET = import_fresh_module('xml.etree.ElementTree',
    #                            blocked=['_elementtree'])
    # if module is None:
    #     module = pyET

    # global ET
    # ET = module

    ET = test_xml_etree.ET = test_xml_etree.pyET = module

    # don't interfere with subsequent tests
    def cleanup():
        global ET
        ET = test_xml_etree.ET = test_xml_etree.pyET = None
    unittest.addModuleCleanup(cleanup)

    # Provide default namespace mapping and path cache.
    from xml.etree import ElementPath
    nsmap = ET.register_namespace._namespace_map
    # Copy the default namespace mapping
    nsmap_copy = nsmap.copy()
    unittest.addModuleCleanup(nsmap.update, nsmap_copy)
    unittest.addModuleCleanup(nsmap.clear)

    # Copy the path cache (should be empty)
    path_cache = ElementPath._cache
    unittest.addModuleCleanup(setattr, ElementPath, "_cache", path_cache)
    ElementPath._cache = path_cache.copy()

    # Align the Comment/PI factories.
    # if hasattr(ET, '_set_factories'):
    #     old_factories = ET._set_factories(ET.Comment, ET.PI)
    #     unittest.addModuleCleanup(ET._set_factories, *old_factories)


def setUpModule(module):
    test_xml_etree.serialize = serialize

    def revert_serialize():
        test_xml_etree.serialize = old_serialize

    unittest.addModuleCleanup(revert_serialize)
    if sys.version_info[:3] < (3, 11):
        setUpModule_old(module=module)
    else:
        test_xml_etree.setUpModule(module=module)


def tearDownModule():
    # pytest doesn't call doModuleCleanups implicitly like unittest
    unittest.case.doModuleCleanups()
