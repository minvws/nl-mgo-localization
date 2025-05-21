from pathlib import Path
from xml.etree.ElementTree import Element, fromstring

from pytest import fixture, raises

from app.xml.exceptions import CouldNotTraverse
from app.xml.services import ElementTraverser


class TestElementTraverser:
    @fixture
    def example_xml(self) -> Element:
        with open(Path(__file__).parent / "dummy.xml", "r") as example_xml_file:
            return fromstring(example_xml_file.read())

    @fixture
    def xml_traverser(self, example_xml: Element) -> ElementTraverser:
        return ElementTraverser(example_xml)

    def test_init_decomposes_root_into_name_and_namespaces(
        self, xml_traverser: ElementTraverser, example_xml: Element
    ) -> None:
        root_name, namespaces = xml_traverser.decompose_tag(example_xml)

        assert root_name == "IAmRoot"
        assert namespaces == {"": "xmlns://foo.bar/xml/namespace/"}

    def test_it_decomposes_root_into_name_and_no_namespaces(self) -> None:
        example_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <Foo>
                <Bar>Hello worwld</Bar>
            </Foo>"""

        traverser = ElementTraverser(fromstring(example_xml))
        root_name, namespaces = traverser.decompose_tag(fromstring(example_xml))

        assert root_name == "Foo"
        assert namespaces is None

    def test_get_child_element_returns_first_child_of_class_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        child = xml_traverser.get_child_element()

        assert child.tag == "{xmlns://foo.bar/xml/namespace/}Test"

    def test_get_child_element_returns_child_of_given_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        nested = xml_traverser.get_nested_element("Nested")
        child = xml_traverser.get_child_element(nested)

        assert child.tag == "{xmlns://foo.bar/xml/namespace/}Elements"

    def test_get_child_element_raises_exception_when_child_not_found(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        child = xml_traverser.get_child_element()

        with raises(
            CouldNotTraverse,
            match="Child element of parent '{xmlns://foo.bar/xml/namespace/}Test' not found",
        ):
            xml_traverser.get_child_element(child)

    def test_get_nested_element_returns_matching_element_of_class_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        match = xml_traverser.get_nested_element("Nested/Elements")

        assert match.tag == "{xmlns://foo.bar/xml/namespace/}Elements"

    def test_get_nested_element_returns_matching_element_of_given_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        single = xml_traverser.get_nested_element("Single")
        match = xml_traverser.get_nested_element("Nested/Element", single)

        assert match.tag == "{xmlns://foo.bar/xml/namespace/}Element"
        assert match.text == "IAmRoot/Single/Nested/Element"

    def test_get_nested_element_raises_exception_when_multiple_matches_found(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        with raises(
            CouldNotTraverse,
            match="Element 'Nested/Elements/Element' occurs more than once",
        ):
            xml_traverser.get_nested_element("Nested/Elements/Element")

    def test_get_nested_element_raises_exception_when_no_match(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        with raises(
            CouldNotTraverse,
            match="Element 'DoesNotExist' not found",
        ):
            xml_traverser.get_nested_element("DoesNotExist")

    def test_get_nested_text_returns_matching_element_content_of_class_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        content = xml_traverser.get_nested_text("Test")

        assert content == "IAmRoot/Test"

    def test_get_nested_text_returns_matching_element_content_of_given_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        single = xml_traverser.get_nested_element("Single")
        content = xml_traverser.get_nested_text("Nested/Element", single)

        assert content == "IAmRoot/Single/Nested/Element"

    def test_get_nested_text_raises_exception_when_text_is_empty(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        with raises(
            CouldNotTraverse,
            match="Element 'NoText' contains no text",
        ):
            xml_traverser.get_nested_text("NoText")

    def test_get_nested_elements_returns_matching_elements_of_class_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        matches = xml_traverser.get_nested_elements("Nested/Elements/Element")

        assert len(matches) == 2
        assert matches[0].text == "IAmRoot/Nested/Elements/Element1"
        assert matches[1].text == "IAmRoot/Nested/Elements/Element2"

    def test_get_nested_elements_returns_matching_elements_of_given_root(
        self,
        xml_traverser: ElementTraverser,
    ) -> None:
        elements = xml_traverser.get_nested_element("Nested/Elements")
        matches = xml_traverser.get_nested_elements("Element", elements)

        assert len(matches) == 2
        assert matches[0].text == "IAmRoot/Nested/Elements/Element1"
        assert matches[1].text == "IAmRoot/Nested/Elements/Element2"
