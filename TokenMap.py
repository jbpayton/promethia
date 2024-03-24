import json
from collections import defaultdict


# A class that maps tokens to unique IDs and vice versa
class TokenMap:
    def __init__(self, synonyms_file=None):
        # Initialize defaultdict with a factory function that counts up for each new token
        self.token_to_id = defaultdict(lambda: len(self.token_to_id))
        self.id_to_token = {}  # For reverse lookup

        # hardcode "__param__" token to id 0
        self.token_to_id["__param__"] = 0
        self.token_to_id["_s_literal_"] = 0
        self.token_to_id["_n_literal_"] = 0
        self.token_to_id["_last_result_"] = -1
        self.id_to_token[0] = "__param__"
        self.id_to_token[-1] = "_last_result_"

        # load synonyms
        self.synonyms = {}
        self.string_to_synonyms_map = {}
        with open(synonyms_file, "r") as f:
            self.synonyms = json.load(f)

    def add_or_get_token_id(self, token):
        """Add a new token to the map and return its unique ID. If the token already exists, return its ID."""
        # The defaultdict takes care of assigning a new ID if necessary
        token_id = self.token_to_id[token]
        # Update the reverse map
        self.id_to_token[token_id] = token

        # check to see if this token ha synonyms, if so, then add the list of synonyms to the string_to_synonyms_map
        if token in self.synonyms:
            self.string_to_synonyms_map[token] = self.synonyms[token]

    def get_token_by_id(self, token_id):
        """Return the token associated with a given ID."""
        return self.id_to_token.get(token_id, None)


if __name__ == "__main__":
    # Example usage of the TokenMap
    token_map = TokenMap()

    # Adding some tokens and getting their IDs
    token_id1 = token_map.add_or_get_token_id("get")
    token_id2 = token_map.add_or_get_token_id("webpage")
    token_id3 = token_map.add_or_get_token_id("get")  # This should return the same ID as token_id1
    print(token_id1, token_id2, token_id3)

    # Retrieving a token by its ID
    token = token_map.get_token_by_id(token_id1)
    print(token)  # Output: get