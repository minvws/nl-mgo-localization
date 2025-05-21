from xml.etree.ElementTree import Element

from .exceptions import CouldNotTraverse


class ElementTraverser:
    def __init__(self, root: Element) -> None:
        self.__root: Element = root

    @staticmethod
    def decompose_tag(element: Element) -> tuple[str, dict[str, str] | None]:
        """
        :param element: Element to decompose
        :return: Tuple with root name and namespaces
        """
        if "}" in element.tag:
            parts = element.tag.split("}", 1)
            namespaces = {"": parts[0][1:]}
            root_name = parts[1]
        else:
            namespaces = None
            root_name = element.tag

        return (root_name, namespaces)

    def get_root_element_name(self) -> str:
        root_name, _ = self.decompose_tag(self.__root)
        return root_name

    def get_child_element(self, root: Element | None = None) -> Element:
        root_element = root if isinstance(root, Element) else self.__root
        _, namespaces = self.decompose_tag(root_element)

        child = root_element.find(path="*", namespaces=namespaces)

        if child is None:
            raise CouldNotTraverse.because_child_element_not_found(root_element.tag)

        return child

    def get_nested_element(self, name: str, root: Element | None = None) -> Element:
        matches = self.__get_all_by_name(name, root)

        if len(matches) > 1:
            raise CouldNotTraverse.because_more_than_one_element(name)

        return matches[0]

    def get_nested_text(self, name: str, root: Element | None = None) -> str:
        element = self.get_nested_element(name, root)

        if not element.text:
            raise CouldNotTraverse.because_text_is_empty(name)

        return element.text

    def get_nested_elements(self, name: str, root: Element | None = None) -> list[Element]:
        return self.__get_all_by_name(name, root)

    def __get_all_by_name(self, name: str, root: Element | None = None) -> list[Element]:
        root_element = root or self.__root
        _, namespaces = self.decompose_tag(root_element)

        matches = root_element.findall(path=name, namespaces=namespaces)

        if len(matches) == 0:
            raise CouldNotTraverse.because_element_not_found(name)

        return matches
