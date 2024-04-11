import json
import re
from collections import defaultdict
from inspect import signature, getmembers, isfunction
import importlib.util
import os
from itertools import product
from TokenMap import TokenMap
from SemanticMapper import SemanticMapper

class Node:
    def __init__(self, token_id, next_nodes=None, action=None):
        self.token_id = token_id
        self.next_nodes = next_nodes or []
        self.action = action


class FunctionMap:
    def __init__(self):
        self.root = Node(None)

    def assign_function_reference_to_signature(self, token_signature, function_reference, parameters):
        current_node = self.root
        for token_id in token_signature:
            match_found = False
            for next_node in current_node.next_nodes:
                if token_id == next_node.token_id:
                    current_node = next_node
                    match_found = True
                    break
            if not match_found:
                new_node = Node(token_id)
                current_node.next_nodes.append(new_node)
                current_node = new_node
        current_node.action = (function_reference, parameters)

    def get_next_node(self, current_node, token_id):
        for next_node in current_node.next_nodes:
            if token_id == next_node.token_id:
                return next_node
        return None


class ActionLoader:
    def __init__(self, action_path="./promethia-actions", synonyms_file="promethia-actions/synonyms.json"):
        self.function_map = FunctionMap()
        self.action_path = action_path
        self.token_map = TokenMap(synonyms_file)

        self.load_actions_from_files()
        # Create a semantic mapper
        self.semantic_mapper = SemanticMapper(self.token_map.string_to_synonyms_map)
        self.last_result = None

    def register_action(self, func):
        params = list(signature(func).parameters.keys())

        if not func.__doc__:
            print(f"Warning: {func.__name__} has no docstring. It will not be loaded as an action.")
            return

        print(f"Registering action: {func.__name__}")
        description = func.__doc__.strip()

        # Tokenize the function signature
        words = description.split()
        optional_map = [1 if '(' in word and ')' in word else 0 for word in words]
        words = [word.strip('()') for word in words]
        words = ['__param__' if '<' in word and '>' in word else word for word in words]
        token_ids = [self.token_map.add_or_get_token_id(word) for word in words]

        # Generate token signature tuples
        token_signature_tuples = self.generate_token_signature_tuples(token_ids, optional_map)
        for token_signature in token_signature_tuples:
            self.function_map.assign_function_reference_to_signature(token_signature, func, params)

    @staticmethod
    def generate_token_signature_tuples(token_ids, optional_map):
        assert len(token_ids) == len(optional_map), "token_ids and optional_map must be of the same length."

        optional_elements = [(i, t) for i, (t, is_optional) in enumerate(zip(token_ids, optional_map)) if is_optional]
        combinations = list(product([True, False], repeat=len(optional_elements)))

        token_signature_tuples = []
        for combination in combinations:
            current_signature = token_ids[:]
            for include, (index, _) in zip(combination, optional_elements):
                if not include:
                    current_signature[index] = None
            token_signature_tuples.append(tuple(filter(None, current_signature)))

        return token_signature_tuples

    def load_actions_from_files(self, action_filenames=None):
        if action_filenames is None:
            action_filenames = [filename for filename in os.listdir(self.action_path)
                                if filename.endswith(".py") and filename != "__init__.py"]

        for action_filename in action_filenames:
            self.load_actions_from_file(action_filename)

    def load_actions_from_file(self, action_filename):
        module_name = os.path.splitext(os.path.basename(action_filename))[0]

        try:
            spec = importlib.util.spec_from_file_location(module_name, self.action_path + "/" + action_filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return

        for name, obj in getmembers(module):
            if isfunction(obj):
                self.register_action(obj)

    @staticmethod
    def split_words_and_string_literals(input_string):
        # Correct pattern to match quoted strings or non-whitespace characters
        pattern = r'"[^"]*"|\'[^\']*\'|\S+'
        matches = re.findall(pattern, input_string)
        return matches

    def parse_string(self, input_string):
        words = self.split_words_and_string_literals(input_string)
        current_node = self.function_map.root

        reading_param = False
        param_index = 0
        param_map = {}

        while words:
            word = words.pop(0)
            token_id = self.token_from_word(word)

            if token_id == -3:
                # if we have  null token, we can skip it
                continue

            if token_id == -4:
                # if we have a stop token, we can stop parsing
                self.execute_function(current_node, param_map)
                current_node = self.function_map.root
                param_index = 0
                break

            if current_node is not None:
                next_node = self.function_map.get_next_node(current_node, token_id)
                if next_node is not None:
                    current_node = next_node

            if current_node is not None:
                if current_node.token_id == -1:
                    if not reading_param:
                        param_map[param_index] = []
                        reading_param = True
                        # the first one's always a param
                        param_map[param_index].append(word)
                    while reading_param:
                        if words:
                            word = words.pop(0)
                            token_id = self.token_from_word(word)

                            if token_id == -3:
                                # if we have  null token, we can skip it
                                continue

                            # there are 3 possible cases here:
                            # 1. the word is an unknown token (token_id == -1)
                            # 2. the word is a known token, but it would not lead to a valid next node
                            # 3. the word is a known token, and it would lead to a valid next node
                            # in case 1, we add the word to the current param_map

                            if token_id == -1:
                                param_map[param_index].append(word)
                            elif token_id == -2:
                                # last result token
                                param_map[param_index].append(self.last_result)
                                reading_param = False
                                param_index += 1
                            elif token_id == -3:
                                # if we have  null token, we can skip it
                                continue
                            elif token_id == -4:
                                # if we have a stop token, we can stop parsing
                                reading_param = False
                                self.execute_function(current_node, param_map)
                                current_node = self.function_map.root
                                param_index = 0
                                break
                            else:
                                next_node = self.function_map.get_next_node(current_node, token_id)
                                if next_node is not None:
                                    current_node = next_node
                                    reading_param = False
                                    param_index += 1
                                else:
                                    param_map[param_index].append(word)
                        else:
                            reading_param = False
                            # if the string ends while reading a param then we are done
                            self.execute_function(current_node, param_map)
                            current_node = self.function_map.root
                            param_index = 0
                            break
        else:
            if current_node is not None:
                self.execute_function(current_node, param_map)

    def execute_function(self, current_node, param_map):
        if current_node.action is not None:
            func_ref = current_node.action[0]
            params = current_node.action[1]
            parsed_args = []
            # go through the param_map and turn it into a list of arguments, joining the words
            for param_index in range(len(param_map)):
                parsed_args.append(" ".join(param_map[param_index]))

            self.last_result = func_ref(*parsed_args)
        else:
            print("No action found for this node")


    def token_from_word(self, word):
        # only parse a word if it is not a string literal
        if word[0] == '"' or word[0] == "'":
            token_id = -1
        # also dont try to parse something without alpha characters in it
        elif not any(c.isalpha() for c in word):
            token_id = -1
        else:
            parsed_word = self.semantic_mapper.parse_word(word)
            token_id = self.token_map.token_to_id.get(parsed_word, -1)
        return token_id


# Example actions
def greet(name):
    """say hello to <name>"""
    return f"Hello, {name}!"

def add_numbers(num1, num2):
    """add <num1> plus <num2>"""
    return int(num1) + int(num2)

if __name__ == "__main__":
    action_loader = ActionLoader()
    action_loader.register_action(greet)
    action_loader.register_action(add_numbers)

    # Create a semantic mapper
    action_loader.semantic_mapper = SemanticMapper(action_loader.token_map.string_to_synonyms_map)

    # Test cases
    action_loader.parse_string("say hello to Alice")
    print(action_loader.last_result)  # Output: Hello, Alice!

    action_loader.parse_string("say hello to Rachel Alucard")
    print(action_loader.last_result)  # Output: Hello, Rachel Alucard!

    action_loader.parse_string("add 5 plus 3")
    print(action_loader.last_result)  # Output: 8

    action_loader.parse_string("say hello to Bob and add 2 plus 4")
    print(action_loader.last_result)  # Output: Hello, Bob!
    print(action_loader.last_result)  # Output: 6

    action_loader.parse_string("unknown action")
    print(action_loader.last_result)  # Output: None

    print("Done running actions")