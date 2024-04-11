from ActionLoader import ActionLoader

from transformers import pipeline, set_seed
generator = pipeline('text-generation', model='gpt2-xl')
set_seed(42)

action_loader = ActionLoader()
error_state = action_loader.load_actions_from_files()
print("done loading actions")
if error_state is not None:
    print(f"Error loading actions: {error_state}")
print(f"Loaded {len(action_loader.function_map)} actions")

def prompt_gpt2(prompt):
    TOOL_PROMPT = "Query: Can you look up 'puffins'?\nAction: search for 'puffins' on wikipedia.\n"
    "Query: Can you look up 'cheese'?\nAction: search for 'cheese' on wikipedia.\n"

    prompt = TOOL_PROMPT + "Query: " + prompt + "\nAction: "
    response = generator(prompt, max_length=50, num_return_sequences=1)

    # remove the prompt from the response
    response_only = response[0]['generated_text'][len(prompt):]
    return response_only


query = "Can you look up 'ants'?"
print(query)
response = prompt_gpt2(query)
print(response)
action_loader.parse_string(response)
print(action_loader.last_result)

query = "Can you search wikipedia for BlazBlue?"
print(query)
response = prompt_gpt2(query)
print(response)
action_loader.parse_string(response)
print(action_loader.last_result)

query = "Now, how about panda bears?"
print(query)
response = prompt_gpt2(query)
print(response)
action_loader.parse_string(response)
print(action_loader.last_result)
