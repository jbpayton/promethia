import re
import sys
from inspect import signature, getmembers, isfunction
import importlib.util
import os
from itertools import product
from TokenMap import TokenMap
from FunctionMap import FunctionMap
from SemanticMapper import SemanticMapper
from VariableMap import VariableMap


class ActionLoader:
    def __init__(self, action_path="./promethia-actions", synonyms_file="promethia-actions/synonyms.json"):
        self.token_map = TokenMap(synonyms_file)
        self.function_map = FunctionMap()
        self.action_path = action_path

        # Load all actions from the action path
        self.load_actions_from_files()

        # Create a semantic mapper
        self.semantic_mapper = SemanticMapper(self.token_map.string_to_synonyms_map)

        self.last_result = None

    # Function to get the dictionary of a tool
    def register_action(self, func):
        # Extracting parameter names
        params = list(signature(func).parameters.keys())
        # Extracting the docstring as description

        # If there is no docstring, print to the console and return None
        if not func.__doc__:
            print(f"Warning: {func.__name__} has no docstring. So it will not be loaded as an action.")
            return None, None
        description = func.__doc__.strip()

        # check to see if there is a "_<number" at the end of the function name, if so, then assign that number as the
        # priority
        priority = self.function_map.priority_levels - 1  # default priority is the highest value (the lowest priority)
        if func.__name__[-1].isdigit():
            priority = int(func.__name__[-1])

        # example docstring: "get webpage (from) <url>"
        # get words from signature
        # get rid of all the punctuation except parentheses and angle brackets with regex
        description = re.sub(r'[^\w\s\(\)\<\>]', '', description)
        words = description.split()

        optional_map = [1 if s.startswith("(") and s.endswith(")") else 0 for s in words]

        # get rid of the parentheses for the optional words
        words = [s[1:-1] if s.startswith("(") and s.endswith(")") else s for s in words]

        # for all parameters (which are in angle brackets), replace them with the word "__param__"
        words = ["__param__" if s.startswith("<") and s.endswith(">") else s for s in words]

        # Turn the words into a token id list
        words = [self.token_map.add_or_get_token_id(word) for word in words]

        # Generate all possible signatures
        token_signature_tuples = self.generate_token_signature_tuples(words, optional_map)
        for token_signature in token_signature_tuples:
            self.function_map.assign_function_reference_to_id(token_signature, func, params, priority)

        # return the name of the function and the dictionary
        return func.__name__, {"params": params, "words": words, "func": func}

    # Function to load all the actions in a file
    @staticmethod
    def generate_token_signature_tuples(tokens, optional_map):
        # Ensure the input lists are of the same length
        assert len(tokens) == len(optional_map), "Tokens and optional_map must be of the same length."

        # Filter out the optional elements and their indices
        optional_elements = [(i, t) for i, (t, is_optional) in enumerate(zip(tokens, optional_map)) if is_optional]

        # Generate all combinations of optional elements being included or excluded
        combinations = list(product([True, False], repeat=len(optional_elements)))

        # Generate the signatures using tokens, but return as tuples
        token_signature_tuples = []
        for combination in combinations:
            current_signature = tokens[:]  # Start with a copy of the original list of tokens
            for include, (index, _) in zip(combination, optional_elements):
                if not include:
                    current_signature[index] = None  # Exclude the optional element by marking it as None
            # Filter out None values (excluded tokens) and convert to tuple
            token_signature_tuples.append(tuple(filter(None, current_signature)))

        return token_signature_tuples

    def load_actions_from_files(self, action_filenames=None):
        if action_filenames is None:
            # Get all the files in the directory
            action_filenames = os.listdir(self.action_path)
            # Remove the __init__.py file
            action_filenames = [action_filename for action_filename in action_filenames if action_filename.endswith(
                ".py") and action_filename != "__init__.py" and action_filename != "ToolTemplate.py"]

        for action_filename in action_filenames:
            error_state = self.load_actions_from_file(action_filename)
            if error_state is not None:
                return error_state

    def load_actions_from_file(self, action_filename):
        # create a dictionary to store the tools temporarily
        tools = {}

        # Parse the module name from the filename
        module_name = os.path.splitext(os.path.basename(action_filename))[0]

        # Check if the module is already loaded
        if module_name in sys.modules:
            print("Module already loaded, we are going to reload it")

        # Load the module
        try:
            spec = importlib.util.spec_from_file_location(module_name, self.action_path + "/" + action_filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules[module_name] = module
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            # return a dictionary with the module name and a detailed error message
            # also a create a function that returns the error message and add it to func
            return {module_name: {"params": [], "description": f"Error loading module {module_name}: {e}",
                                  "func": lambda: f"Error loading module {module_name}"}}

        # iterate through all functions in the module
        for name, obj in getmembers(module):
            # if the object is a function
            if isfunction(obj):
                # get the name and dictionary of the function
                self.register_action(obj)

    def execute_action(self, token_id_list, action_string_list, priority=0):
        # Get the action from the string
        func_ref, params = self.function_map.get_function_reference_and_params_by_signature(token_id_list, priority)
        if func_ref is None:
            return None

        print("Executing function", func_ref.__name__)

        # token -1 is "_last_result_", we need to change and -1 to 0, and change the string to the last result
        token_id_list = [-1 if token_id == -2 else token_id for token_id in token_id_list]
        action_string_list = [self.last_result if action_string == "_last_result_" else
                              action_string for action_string in action_string_list]


        # for each -1 in token_id_list ad the string in the action_string_list to the params
        parsed_args = []
        for i, token_id in enumerate(token_id_list):
            if token_id == -1:
                parsed_args.append(self.auto_parse_parameter(action_string_list[i]))

        # Execute the function
        self.last_result = func_ref(*parsed_args)

    @staticmethod
    def auto_parse_parameter(input_str):
        # Regular expression for matching integers, including negative integers
        if re.match(r"^-?\d+$", input_str):
            return int(input_str)
        # Regular expression for matching floats, including negative floats and scientific notation
        elif re.match(r"^-?\d+(\.\d+)?(e[-+]?\d+)?$", input_str):
            return float(input_str)
        # Return the original string if it doesn't match the patterns
        else:
            return input_str

    def parse_string(self, input_string):
        action_string_list, filtered = self.semantic_mapper.parse_string(input_string)
        token_id_list = self.token_map.get_ids_from_string_list(filtered)

        # change all the -2 to -1
        token_id_list = [-1 if token_id == -2 else token_id for token_id in token_id_list]

        for priority in range(self.function_map.priority_levels):
            current_position = 0
            while current_position < len(token_id_list):
                longest_signature = self.function_map.match_longest_signature(token_id_list[current_position:], priority)
                if longest_signature is not None:
                    print(f"Matched signature: {longest_signature} at position {current_position} priority {priority}")
                    self.execute_action(longest_signature,
                                        action_string_list[current_position:current_position + len(longest_signature)],
                                        priority)
                    # Replace the matched tokens with a parameter token, and the string with the result
                    token_id_list[current_position] = -1
                    action_string_list[current_position] = self.last_result

                    #delete the rest of the tokens
                    for i in range(1, len(longest_signature)):
                        token_id_list.pop(current_position + 1)
                        action_string_list.pop(current_position + 1)

                current_position += 1

if __name__ == "__main__":
    action_loader = ActionLoader()
    error_state = action_loader.load_actions_from_files()
    print("done loading actions")
    if error_state is not None:
        print(f"Error loading actions: {error_state}")
    print(f"Loaded {len(action_loader.function_map)} actions")

    # Test the running of an action
    action_loader.parse_string("grab webpage at 'https://en.wikipedia.org/wiki/Golem' and save it to a variable named 'golem_page'")

    # Test the running of an action
    action_loader.parse_string("grab webpage at 'https://en.wikipedia.org/wiki/Golem' and save it to file 'golem.txt'")

    # Test the running of an action
    action_loader.parse_string("save webpage at 'https://en.wikipedia.org/wiki/Golem' to file 'golem2.txt'")
    # Test the running of an action
    action_loader.parse_string(
        "Save webpage at 'https://blazblue.fandom.com/wiki/Rachel_Alucard' to a variable named 'rachel_text'.")
    action_loader.parse_string(
        "Save value from variable 'rachel_text' to file 'rachel.txt'.")

    print("done running actions")
