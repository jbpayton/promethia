import json
import re
from collections import defaultdict
from inspect import signature, getmembers, isfunction
import importlib.util
import os
from itertools import product
from TokenMap import TokenMap
from SemanticMapper import SemanticMapper
from VariableMap import VariableMap

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

    def parse_string(self, input_string, verbose=False):
        words = self.split_words_and_string_literals(input_string)
        current_node = self.function_map.root

        reading_param = False
        param_index = 0
        param_map = {}

        if verbose:
            print(f"Parsing string: {input_string}")

        while words:
            word = words.pop(0)
            token_id = self.token_from_word(word)

            if token_id == -4:
                # a stop token only counts as a stop token if it is followed by noting or a valid next start of a sequence
                peek_node = self.function_map.get_next_node(self.function_map.root, self.token_from_word(words[0]))
                if not words or peek_node is not None:
                    # if we have a stop token, we can stop parsing
                    self.execute_function(current_node, param_map, verbose=verbose)
                    param_map = {}
                    current_node = self.function_map.root
                    param_index = 0
                else:
                    token_id = -1

            if token_id == -5:
                #a variable is always a param, an entire param
                value = VariableMap.get_instance().get_data(word)
                param_map[param_index] = [value]
                param_index += 1
                next_node = self.function_map.get_next_node(current_node, -1)
                if next_node is not None:
                    current_node = next_node
                    self.execute_function(current_node, param_map, verbose=verbose)
                    param_map = {}
                    current_node = self.function_map.root
                    param_index = 0
                else:
                    current_node = self.function_map.root
                continue

            if token_id == -3:
                # check to see if this would work as a param
                if not reading_param:
                    if self.function_map.get_next_node(current_node, -1) is not None:
                        token_id = -1
                    else:
                        # if we're not reading a param, we can skip the null token
                        continue

            if current_node is not None:
                next_node = self.function_map.get_next_node(current_node, token_id)
                if next_node is not None:
                    current_node = next_node
                else:
                    current_node = self.function_map.root
                    continue

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

                            # there are 3 possible cases here:
                            # 1. the word is an unknown token (token_id == -1)
                            # 2. the word is a known token, but it would not lead to a valid next node
                            # 3. the word is a known token, and it would lead to a valid next node
                            # in case 1, we add the word to the current param_map

                            if token_id == -4:
                                peek_node = self.function_map.get_next_node(self.function_map.root,
                                                                            self.token_from_word(words[0]))
                                if not words or peek_node is not None:
                                    # if we have a stop token, we can stop parsing
                                    reading_param = False
                                    self.execute_function(current_node, param_map, verbose=verbose)
                                    param_map = {}
                                    current_node = self.function_map.root
                                    param_index = 0
                                    break
                                else:
                                    param_map[param_index].append(word)

                            if token_id == -1:
                                param_map[param_index].append(word)
                            elif token_id == -2:
                                # last result token
                                param_map[param_index].append(self.last_result)
                                reading_param = False
                                param_index += 1
                            elif self.function_map.get_next_node(self.function_map.root, token_id) is not None:
                                reading_param = False
                                # push the word back into the stack
                                words.insert(0, word)
                                self.execute_function(current_node, param_map, verbose=verbose)
                                param_map = {}
                                current_node = self.function_map.root
                                param_index = 0
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
                            self.execute_function(current_node, param_map, verbose=verbose)
                            param_map = {}
                            current_node = self.function_map.root
                            param_index = 0
                            break
                elif token_id == -3: # if not a param and we have a null token, we can skip it
                    # if we have a null token, we can skip it
                    continue
        else:
            if current_node is not None:
                if current_node.action is not None:
                    self.execute_function(current_node, param_map)

    def execute_function(self, current_node, param_map, verbose=False):
        if current_node is None:
            if verbose:
                print("No node found for this action")
            return
        if current_node.action is not None:
            func_ref = current_node.action[0]
            params = current_node.action[1]
            parsed_args = []
            # go through the param_map and turn it into a list of arguments, joining the words
            for param_index in range(len(param_map)):
                parsed_args.append(" ".join(param_map[param_index]))

            self.last_result = func_ref(*parsed_args)

            if verbose:
                print(f"Executing function {func_ref.__name__} with params {parsed_args}")
                print(f"Result: {self.last_result}")
        else:
            if verbose:
                print("No action found for this node")


    def token_from_word(self, word):
        # only parse a word if it is not a string literal
        if word[0] == '"' or word[0] == "'":
            return -1

        # also dont try to parse something without alpha characters in it
        if not any(c.isalpha() for c in word):
            return -1

        if VariableMap.get_instance().is_variable(word):
            return -5

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

    '''
    # Test cases
    action_loader.parse_string("say hello to Alice")
    print(action_loader.last_result)  # Output: Hello, Alice!

    action_loader.parse_string("say hello to Rachel Alucard")
    print(action_loader.last_result)  # Output: Hello, Rachel Alucard!

    action_loader.parse_string("add 5 plus 3", verbose=True)
    print(action_loader.last_result)  # Output: 8

    action_loader.parse_string("say hello to Bob and add 2 plus 4", verbose=True)
    print(action_loader.last_result)  # Output: 6

    action_loader.parse_string("say hello to the whole world add 2 plus 4", verbose=True)
    print(action_loader.last_result)  # Output: 6

    action_loader.parse_string("save a bunch of the fish and eels to variable bucket", verbose=True)
    action_loader.parse_string("say hello to bucket", verbose=True)
    
    action_loader.parse_string("unknown action", verbose=True)
    print(action_loader.last_result)  # Output: None

    action_loader.parse_string("say hello to bucket and add 1 plus 1", verbose=True)
    action_loader.parse_string("I'mma gonna say hello to bucket and add 1 plus 1", verbose=True)
    '''
    action_loader.parse_string("Search for golem on wikipedia and save it to a file named 'wikigolem.txt'", verbose=True)


    print("Done running actions")