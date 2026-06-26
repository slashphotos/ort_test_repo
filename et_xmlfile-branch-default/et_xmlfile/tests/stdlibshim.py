# A shim file to replace certain parts of xml.etree.ElementTree with this
# package's modified versions so that we can test against the stdlib tests
import xml.etree.ElementTree as pyET
from xml.etree.ElementTree import *
from et_xmlfile.incremental_tree import *

ElementTree = IncrementalTree
tostring = compat_tostring

_Element_Py = pyET._Element_Py
