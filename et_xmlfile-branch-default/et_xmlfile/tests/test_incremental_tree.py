import io
import operator
import unittest
import xml.etree.ElementTree as ET

from et_xmlfile import incremental_tree as inc_tree


def serialize(elem, to_string=True, encoding="unicode", **options):
    if encoding != "unicode":
        file = io.BytesIO()
    else:
        file = io.StringIO()
    tree = inc_tree.IncrementalTree(elem)
    tree.write(file, encoding=encoding, **options)
    if to_string:
        return file.getvalue()
    else:
        file.seek(0)
        return file


class BaseETTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_namespace_map = ET.register_namespace._namespace_map.copy()

    def tearDown(self):
        # Clear any namespaces registered during tests
        ET.register_namespace._namespace_map.clear()
        ET.register_namespace._namespace_map.update(self._orig_namespace_map)

    def assertEqualElements(self, alice, bob):
        self.assertEqual(len(list(alice)), len(list(bob)))
        for x, y in zip(alice, bob):
            self.assertEqualElements(x, y)


class ETModTests(BaseETTestCase):

    def test_namespaces_returns_only_used(self):
        "_namespaces only returns uris that were used in the docuemnt"
        elem = ET.Element("{namespace0}foo")
        out_nsmap = inc_tree._namespaces(
            elem,
        )
        self.assertEqual(
            out_nsmap,
            {"ns0": "namespace0"},
        )

    def test_namespaces_default_namespace_not_used(self):
        "_namespaces doesn't return default_namespace if not used"
        elem = ET.Element("{namespace1}foo")
        out_nsmap = inc_tree._namespaces(
            elem,
            default_namespace="other",
        )
        self.assertEqual(
            out_nsmap,
            {"ns1": "namespace1"},
        )

    def test_default_namespace_not_used(self):
        "Serializing will declare the default_namespace even if unused"
        elem = ET.Element("{namespace1}foo")
        self.assertEqual(
            serialize(elem, default_namespace="other"),
            '<ns1:foo xmlns="other" xmlns:ns1="namespace1" />'
        )

    def test_default_namespace_not_used_minimal(self):
        "Serializing will declare the default_namespace even if unused unless minimal ns declared"
        elem = ET.Element("{namespace1}foo")
        self.assertEqual(
            serialize(elem, default_namespace="other", minimal_ns_only=True),
            '<ns1:foo xmlns:ns1="namespace1" />'
        )

    def test_nsmap_not_used_minimal(self):
        "Serializing will declare the default_namespace even if unused unless minimal ns declared"
        elem = ET.Element("{namespace0}foo")
        self.assertEqual(
            serialize(elem, nsmap={"oth": "other"}, minimal_ns_only=True),
            '<ns0:foo xmlns:ns0="namespace0" />'
        )

    def test_minimal_ns_only_implies_root_ns_only(self):
        elem = ET.Element("{namespace1}foo")
        ET.SubElement(elem, "{namespace2}bar")
        self.assertEqual(
            serialize(
                elem,
                default_namespace="default",
                nsmap={"oth": "other"},
                minimal_ns_only=True,
            ),
            '<ns1:foo xmlns:ns1="namespace1" xmlns:ns2="namespace2"><ns2:bar /></ns1:foo>'
        )


class CommonFixesTests(BaseETTestCase):
    """A collection of tests added to PRs for cpython for bug fixes / enhancements.

    The bug fixes are:
    - conflicts of registered namespaces and default_namespace uri
    - incorrect handling of attributes with a URI that is the same as the
      default_uri (attributes in that namespace must have a prefix - unprefixed
      attrs are not in the default namespace)

    Feature:
    - Add local namespace map arg, `nsmap` to write()`
    """
    compat_serialize = False

    def serialize(self, elem, to_string=True, encoding="unicode", **options):
        if self.compat_serialize:
            options["root_ns_only"] = True

        return serialize(elem, to_string=to_string, encoding=encoding, **options)

    def test_tostring_nsmap(self):
        elem = ET.XML(
            '<body xmlns="http://effbot.org/ns" xmlns:foo="bar"><foo:tag/></body>'
        )
        if self.compat_serialize:
            expected = '<ns0:body xmlns:ns0="http://effbot.org/ns" xmlns:ns1="bar"><ns1:tag /></ns0:body>'
        else:
            expected = '<ns0:body xmlns:ns0="http://effbot.org/ns"><ns1:tag xmlns:ns1="bar" /></ns0:body>'
        self.assertEqual(self.serialize(elem, encoding="unicode"), expected)

        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                nsmap={
                    "": "http://effbot.org/ns",
                    "foo": "bar",
                    "unused": "nothing",
                },
            ),
            '<body xmlns="http://effbot.org/ns" xmlns:foo="bar" xmlns:unused="nothing">'
            "<foo:tag /></body>",
        )

    def test_tostring_nsmap_default_namespace(self):
        elem = ET.XML('<body xmlns="http://effbot.org/ns"><tag/></body>')
        self.assertEqual(
            self.serialize(elem, encoding="unicode"),
            '<ns0:body xmlns:ns0="http://effbot.org/ns"><ns0:tag /></ns0:body>',
        )
        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                nsmap={"": "http://effbot.org/ns"},
            ),
            '<body xmlns="http://effbot.org/ns"><tag /></body>',
        )

    def test_tostring_nsmap_default_namespace_none(self):
        elem = ET.XML('<body xmlns="http://effbot.org/ns"><tag/></body>')
        self.assertEqual(
            self.serialize(elem, encoding="unicode"),
            '<ns0:body xmlns:ns0="http://effbot.org/ns"><ns0:tag /></ns0:body>',
        )
        msg = '^Found None as default nsmap prefix in nsmap. Use "" as the default namespace prefix.$'

        with self.assertRaisesRegex(ValueError, msg):
            self.serialize(
                elem,
                encoding="unicode",
                nsmap={None: "http://effbot.org/ns"},
            )

    def test_tostring_nsmap_default_namespace_overrides(self):
        elem = ET.XML('<body xmlns="http://effbot.org/ns"><tag/></body>')
        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                default_namespace="other",
                nsmap={"": "http://effbot.org/ns"},
            ),
            '<ns1:body xmlns="other" xmlns:ns1="http://effbot.org/ns">'
            "<ns1:tag />"
            "</ns1:body>",
        )
        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                default_namespace="http://effbot.org/ns",
                nsmap={"": "other"},
            ),
            '<body xmlns="http://effbot.org/ns"><tag /></body>',
        )

    def test_tostring_nsmap_default_namespace_attr(self):
        reg_name = "gh57587"
        namespace = "ns_gh57587"
        elem = ET.XML(
            f'<body xmlns="{namespace}" xmlns:foo="{namespace}" foo:status="good">'
            "<tag/></body>"
        )
        self.assertEqual(
            self.serialize(elem, encoding="unicode"),
            f'<ns0:body xmlns:ns0="{namespace}" ns0:status="good"><ns0:tag /></ns0:body>',
        )
        ET.register_namespace(reg_name, namespace)
        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                nsmap={
                    "": namespace,
                    "foo": namespace,
                },
            ),
            f'<body xmlns="{namespace}" xmlns:foo="{namespace}" foo:status="good">'
            "<tag /></body>",
        )
        # default attr gets name from global registered namespaces
        self.assertEqual(
            self.serialize(
                elem,
                encoding="unicode",
                nsmap={"": namespace},
            ),
            f'<body xmlns="{namespace}" xmlns:{reg_name}="{namespace}" {reg_name}:status="good">'
            "<tag /></body>",
        )

    def test_tostring_nsmap_default_namespace_original_no_namespace(self):
        elem = ET.XML("<body><tag/></body>")
        EXPECTED_MSG = "^cannot use non-qualified names with default_namespace option$"
        with self.assertRaisesRegex(ValueError, EXPECTED_MSG):
            self.serialize(elem, encoding="unicode", nsmap={"": "foobar"})

    def test_tostringlist_nsmap_default_namespace(self):
        elem = ET.XML('<body xmlns="http://effbot.org/ns"><tag/></body>')
        self.assertEqual(
            "".join(inc_tree.tostringlist(elem, encoding="unicode")),
            '<ns0:body xmlns:ns0="http://effbot.org/ns"><ns0:tag /></ns0:body>',
        )
        self.assertEqual(
            "".join(
                inc_tree.tostringlist(
                    elem,
                    encoding="unicode",
                    nsmap={"": "http://effbot.org/ns"},
                )
            ),
            '<body xmlns="http://effbot.org/ns"><tag /></body>',
        )

    def test_namespace_attribs(self):
        # Unprefixed attributes are unqualified even if a default
        # namespace is in effect. (This is a little unclear in some
        # versions of the XML TR but is clarified in errata and other
        # versions.) See bugs.python.org issue 17088.
        #
        # The reasoning behind this, alluded to in the spec, is that
        # attribute meanings already depend on the element they're
        # attached to; attributes have always lived in per-element
        # namespaces even before explicit XML namespaces were
        # introduced.  For that reason qualified attribute names are
        # only really needed when one XML module defines attributes
        # that can be placed on elements defined in a different module
        # (such as happens with XLINK or, for that matter, the XML
        # namespace spec itself).
        e = ET.XML(
            '<pf:elt xmlns:pf="space1" xmlns:pf2="space2" foo="value">'
            '<pf:foo foo="value2" pf2:foo="value3"/>'
            '<pf2:foo foo="value4" pf:foo="value5" pf2:foo="value6"/>'
            '<foo foo="value7" pf:foo="value8"/>'
            "</pf:elt>"
        )
        self.assertEqual(e.tag, "{space1}elt")
        self.assertEqual(e.get("foo"), "value")
        self.assertIsNone(e.get("{space1}foo"))
        self.assertIsNone(e.get("{space2}foo"))
        self.assertEqual(e[0].tag, "{space1}foo")
        self.assertEqual(e[0].attrib, {"foo": "value2", "{space2}foo": "value3"})
        self.assertEqual(e[1].tag, "{space2}foo")
        self.assertEqual(
            e[1].attrib,
            {"foo": "value4", "{space1}foo": "value5", "{space2}foo": "value6"},
        )
        self.assertEqual(e[2].tag, "foo")
        self.assertEqual(e[2].attrib, {"foo": "value7", "{space1}foo": "value8"})

        if self.compat_serialize:
            serialized1 = (
                '<ns0:elt xmlns:ns0="space1" xmlns:ns1="space2" foo="value">'
                '<ns0:foo foo="value2" ns1:foo="value3" />'
                '<ns1:foo foo="value4" ns0:foo="value5" ns1:foo="value6" />'
                '<foo foo="value7" ns0:foo="value8" />'
                "</ns0:elt>"
            )
        else:
            serialized1 = (
                '<ns0:elt xmlns:ns0="space1" foo="value">'
                '<ns0:foo xmlns:ns1="space2" foo="value2" ns1:foo="value3" />'
                '<ns1:foo xmlns:ns1="space2" foo="value4" ns0:foo="value5" ns1:foo="value6" />'
                '<foo foo="value7" ns0:foo="value8" />'
                "</ns0:elt>"
            )
        self.assertEqual(self.serialize(e), serialized1)
        self.assertEqualElements(e, ET.XML(serialized1))

        # Test writing with a default namespace.
        with self.assertRaisesRegex(
            ValueError, "cannot use non-qualified name.* with default_namespace option"
        ):
            self.serialize(e, default_namespace="space1")

        # Remove the unqualified element from the tree so we can test
        # further.
        del e[2]

        # Serialization can require a namespace prefix to be declared for
        # space1 even if no elements use that prefix, in order to
        # write an attribute name in that namespace.
        if self.compat_serialize:
            serialized2 = (
                '<ns1:elt xmlns="space2" xmlns:ns1="space1" xmlns:ns2="space2" foo="value">'
                '<ns1:foo foo="value2" ns2:foo="value3" />'
                '<foo foo="value4" ns1:foo="value5" ns2:foo="value6" />'
                "</ns1:elt>"
            )
        else:
            serialized2 = (
                '<ns1:elt xmlns="space2" xmlns:ns1="space1" foo="value">'
                '<ns1:foo xmlns:ns2="space2" foo="value2" ns2:foo="value3" />'
                '<foo xmlns:ns2="space2" foo="value4" ns1:foo="value5" ns2:foo="value6" />'
                "</ns1:elt>"
            )
        self.assertEqual(self.serialize(e, default_namespace="space2"), serialized2)
        self.assertEqualElements(e, ET.XML(serialized2))

        if self.compat_serialize:
            serialized3 = (
                '<elt xmlns="space1" xmlns:ns1="space2" xmlns:ns2="space1" foo="value">'
                '<foo foo="value2" ns1:foo="value3" />'
                '<ns1:foo foo="value4" ns2:foo="value5" ns1:foo="value6" />'
                "</elt>"
            )
        else:
            serialized3 = (
                '<elt xmlns="space1" foo="value">'
                '<foo xmlns:ns1="space2" foo="value2" ns1:foo="value3" />'
                '<ns1:foo xmlns:ns1="space2" xmlns:ns2="space1" foo="value4" ns2:foo="value5" ns1:foo="value6" />'
                "</elt>"
            )
        self.assertEqual(self.serialize(e, default_namespace="space1"), serialized3)
        self.assertEqualElements(e, ET.XML(serialized3))

    def test_pre_gh118416_register_default_namespace_behaviour(self):
        # All these examples worked prior to fixing bug gh118416
        ET.register_namespace("", "gh118416")

        # If the registered default prefix's URI is not used, don't raise an
        # error
        e = ET.Element("{other}elem")
        self.assertEqual(
            self.serialize(e),
            '<ns0:elem xmlns:ns0="other" />',
        )
        # no error even with unqualified tags
        e = ET.Element("elem")
        self.assertEqual(
            self.serialize(e),
            "<elem />",
        )

        # Uses registered default prefix, if used in tree
        e = ET.Element("{gh118416}elem")
        self.assertEqual(
            self.serialize(e),
            '<elem xmlns="gh118416" />',
        )

        # Use explicitly provided default_namespace if registered default
        # prefix is not used.
        e = ET.Element("{default}elem")
        ET.SubElement(e, "{other}otherEl")
        if self.compat_serialize:
            expected_xml = '<elem xmlns="default" xmlns:ns1="other"><ns1:otherEl /></elem>'
        else:
            expected_xml = '<elem xmlns="default"><ns1:otherEl xmlns:ns1="other" /></elem>'
        self.assertEqual(
            self.serialize(e, default_namespace="default"),
            expected_xml,
        )

    def test_gh118416_register_default_namespace(self):
        ET.register_namespace("", "gh118416")
        e = ET.Element("{gh118416}elem")
        ET.SubElement(e, "noPrefixElem")
        with self.assertRaises(ValueError) as cm:
            self.serialize(e)
        self.assertEqual(
            str(cm.exception),
            "cannot use non-qualified names with default_namespace option",
        )

        e = ET.Element("{gh118416}elem")
        # explicitly set default_namespace takes precedence
        self.assertEqual(
            self.serialize(e, default_namespace="otherdefault"),
            '<ns1:elem xmlns="otherdefault" xmlns:ns1="gh118416" />',
        )


class CommonFixesTestsCompat(CommonFixesTests):
    compat_serialize = True
