from PromethiaParser import PromethiaParser

from transformers import pipeline, set_seed
generator = pipeline('text-generation', model='gpt2-xl')
set_seed(42)

action_parser = PromethiaParser()

def prompt_gpt2(prompt):
    TOOL_PROMPT = "Query: Can you look up 'puffins'?\nAction: search wikipedia for puffins\n"
    "Query: Can you look up 'cheese'?\nAction: search wikipedia for cheese\n"

    prompt = TOOL_PROMPT + "Query: " + prompt + "\nAction: "
    response = generator(prompt, num_return_sequences=1)

    # remove the prompt from the response
    response_only = response[0]['generated_text'][len(prompt):]
    # only take the first sentence
    response_only = response_only.split(". ")[0]
    return response_only


query = "Can you look up some info on ants?"
print(query)
response = prompt_gpt2(query)
print(response)
action_parser.parse_string(response, verbose=True)
print(action_parser.last_result)

query = "Now, how about panda bears?"
print(query)
response = prompt_gpt2(query)
print(response)
action_parser.parse_string(response)
print(action_parser.last_result)
