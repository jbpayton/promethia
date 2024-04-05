
# A class that maps function signatures to unique IDs and vice versa
class FunctionMap:
    def __init__(self, priority_levels=3):
        self.priority_levels = priority_levels

        # Create a list of dicts for each priority level
        self._map = {}
        self.min_sig_sizes = 9999
        self.max_sig_sizes = 0

    def __len__(self):
        return len(self._map)

    def assign_function_reference_to_id(self, function_signature, function_reference, parameters, priority=0):
        # Convert to tuple to make it hashable
        tuple(function_signature)

        # Get or assign new ID
        self._map[function_signature] = (function_reference, parameters, priority)

        # update min and max signature size
        if len(function_signature) < self.min_sig_sizes:
            self.min_sig_sizes = len(function_signature)

        if len(function_signature) > self.max_sig_sizes:
            self.max_sig_sizes = len(function_signature)

    def get_function_reference_and_params_by_signature(self, function_signature):
        function_signature = tuple(function_signature)
        ref_and_params = self._map.get(function_signature, None)
        if ref_and_params is None:
            return None, None, None
        return ref_and_params

    def match_longest_signature(self, input_tokens, priority=0):
        # find the longest matching signature
        for i in range(self.max_sig_sizes, self.min_sig_sizes - 1, -1):
            if tuple(input_tokens[:i]) in self._map:
                return tuple(input_tokens[:i])
        return None


if __name__ == "__main__":
    # Example usage
    function_map = FunctionMap()

    # Assign a function reference to a function signature
    def my_func1():
        return "Hello, world!"

    function_map.assign_function_reference_to_id(("get", "webpage"), my_func1, ["url"], priority=0)
    print(function_map.get_function_reference_and_params_by_signature(("get", "webpage")))

    # Search for the longest matching signature
    print(function_map.match_longest_signature(["get", "webpage", "https://example.com"], priority=0))
