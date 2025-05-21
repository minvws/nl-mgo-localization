class CouldNotTraverse(Exception):
    @staticmethod
    def because_element_not_found(tag_name: str) -> "CouldNotTraverse":
        return CouldNotTraverse(f"Element '{tag_name}' not found")

    @staticmethod
    def because_more_than_one_element(tag_name: str) -> "CouldNotTraverse":
        return CouldNotTraverse(f"Element '{tag_name}' occurs more than once")

    @staticmethod
    def because_child_element_not_found(parent_tag_name: str) -> "CouldNotTraverse":
        return CouldNotTraverse(f"Child element of parent '{parent_tag_name}' not found")

    @staticmethod
    def because_text_is_empty(tag_name: str) -> "CouldNotTraverse":
        return CouldNotTraverse(f"Element '{tag_name}' contains no text")
