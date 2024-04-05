import json
from collections import defaultdict


# A class that maps tokens to unique IDs and vice versa
class TokenMap:
    def __init__(self, synonyms_file=None):
        # Initialize defaultdict with a factory function that counts up for each new token
        self.token_to_id = defaultdict(lambda: len(self.token_to_id))
        self.id_to_token = {}  # For reverse lookup

        # hardcode "__param__" token to id 0
        self.token_to_id["__param__"] = -1
        self.token_to_id["_s_literal_"] = -1
        self.token_to_id["_n_literal_"] = -1
        self.token_to_id["_last_result_"] = -2
        self.id_to_token[-1] = "__param__"
        self.id_to_token[-2] = "_last_result_"

        # load synonyms
        self.synonyms = {}
        self.string_to_synonyms_map = {}
        with open(synonyms_file, "r") as f:
            self.synonyms = json.load(f)

    def add_or_get_token_id(self, token):
        """Add a new token to the map and return its unique ID. If the token already exists, return its ID."""

        # first check if the token is a synonym, if so, then return the id of the original token
        # (search for the token in the dict values, not keys)
        for key, value in self.synonyms.items():
            if token in value:
                token = key
                break


        # The defaultdict takes care of assigning a new ID if necessary
        token_id = self.token_to_id[token]

        # Update the reverse map
        self.id_to_token[token_id] = token

        # check to see if this token has synonyms, if so, then add the list of synonyms to the string_to_synonyms_map
        if token in self.synonyms:
            self.string_to_synonyms_map[token] = self.synonyms[token]

        return token_id

    def get_token_by_id(self, token_id):
        """Return the token associated with a given ID."""
        return self.id_to_token.get(token_id, None)

    def get_ids_from_string_list(self, string_list):
        ids = []
        for string in string_list:
            ids.append(self.token_to_id[string])
        return ids


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
