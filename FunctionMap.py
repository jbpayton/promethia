from collections import defaultdict


# A class that maps function signatures to unique IDs and vice versa
class FunctionMap:
    def __init__(self):
        self._map = defaultdict(lambda: len(self._map))
        self._reverse_map = {}

        self._function_info_map = {}

    def __len__(self):
        return len(self._map)

    def add_or_get_id(self, function_signature):
        """Add a new tuple of tokens representing a function signature and return its ID.
        If the tuple already exists, return its existing ID."""
        # Ensure the input is a tuple for hashability
        if not isinstance(function_signature, tuple):
            raise TypeError("Function signature must be a tuple.")

        # Get or assign new ID
        id = self._map[function_signature]

        # Update reverse map for easy lookup
        self._reverse_map[id] = function_signature

        return id

    def assign_function_reference_to_id(self, function_signature, function_reference, parameters):
        id = self.add_or_get_id(function_signature)
        self._function_info_map[id] = (function_reference, parameters)

    def get_signature_by_id(self, id):
        """Return the function signature tuple associated with the given ID."""
        return self._reverse_map.get(id, None)

    def get_function_reference_and_params_by_id(self, id):
        return self._function_info_map.get(id, None)

    def get_function_reference_and_params_by_signature(self, function_signature):
        id = self._map.get(function_signature, None)
        if id is None:
            return None
        return self._function_info_map.get(id, None)


if __name__ == "__main__":
    # Example usage
    function_map = FunctionMap()

    # Adding some function signatures and getting their IDs
    id1 = function_map.add_or_get_id(("get", "webpage", "<url>"))
    id2 = function_map.add_or_get_id(("get", "webpage", "from", "<url>"))
    id3 = function_map.add_or_get_id(("get", "webpage", "<url>"))  # This should return the same ID as id1

    # Retrieving a function signature by its ID
    signature = function_map.get_signature_by_id(id1)

    print(id1, id2, id3, signature)
