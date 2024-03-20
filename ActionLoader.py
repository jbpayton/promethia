import re
import sys
from inspect import signature, getmembers, isfunction
import importlib.util
import os

# Function to get the dictionary of a tool
def get_action_name_and_dict(func):
    # Extracting parameter names
    params = list(signature(func).parameters.keys())
    # Extracting the docstring as description

    # If there is no docstring, print to the console and return None
    if not func.__doc__:
        print(f"Warning: {func.__name__} has no docstring. So it will not be loaded as an action.")
        return None, None
    description = func.__doc__.strip()

    # example docstring: "get webpage (from) <url>"
    # get words from signature
    # get rid of all the punctuation except parentheses and angle brackets with regex
    description = re.sub(r'[^\w\s\(\)\<\>]', '', description)
    words = description.split()

    # return the name of the function and the dictionary
    return func.__name__, {"params": params, "words": words, "func": func}


def load_actions_from_files(action_filenames=None, action_path="./promethia-actions"):
    # create a dictionary to store the tools temporarily
    actions = {}

    if action_filenames is None:
        # Get all the files in the directory
        action_filenames = os.listdir(action_path)
        # Remove the __init__.py file
        action_filenames = [action_filename for action_filename in action_filenames if action_filename.endswith(".py") and action_filename != "__init__.py" and action_filename != "ToolTemplate.py"]

    for action_filename in action_filenames:
        loaded_tools = load_actions_from_file(action_filename, action_path)

        # add the tools to the tools dictionary
        actions.update(loaded_tools)

    return actions


def load_actions_from_file(action_filename, action_path="./promethia-actions"):
    # create a dictionary to store the tools temporarily
    tools = {}

    # Parse the module name from the filename
    module_name = os.path.splitext(os.path.basename(action_filename))[0]

    # Check if the module is already loaded
    if module_name in sys.modules:
        print("Module already loaded, we are going to reload it")

    # Load the module
    try:
        spec = importlib.util.spec_from_file_location(module_name, action_path + "/" + action_filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
    except Exception as e:
        print(f"Error loading module {module_name}: {e}")
        # return a dictionary with the module name and a detailed error message
        # also a create a function that returns the error message and add it to func
        return {module_name: {"params": [], "description": f"Error loading module {module_name}: {e}", "func": lambda: f"Error loading module {module_name}"}}


    # iterate through all functions in the module
    for name, obj in getmembers(module):
        # if the object is a function
        if isfunction(obj):
            # get the name and dictionary of the function
            name, dictionary = get_action_name_and_dict(obj)
            # if the dictionary is not None
            if dictionary is not None:
                # store the dictionary in the tools dictionary
                tools[name] = dictionary
                print(name, dictionary)

    return tools

def compare_word_lists(base, input):
    # we need to do a compare with words, if word is in parentheses, it is optional, if it is in angle brackets, it can match with any word
    # example: "get webpage (from) <url>" and "get webpage "www.google.com" should match
    # example: "get webpage (from) <url>" and "get webpage from "www.google.com" should also match




if __name__ == "__main__":
    #actions = load_actions_from_file("FileTools.py")
    actions = load_actions_from_files()
    print(actions)