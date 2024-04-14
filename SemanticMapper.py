import re

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


class SemanticMapper:
    def __init__(self, ids_to_descriptions = None, similarity_threshold = 0.7, embedding_model = None):
        self.words = []
        self.ids = []
        self.d = 0
        self.index = None
        self.pronouns = ["it",  "him", "her", "that"]
        self.articles = ["the", "a", "an"]
        self.conjunctions = ["and"]


        self.threshold = similarity_threshold

        if embedding_model is None:
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        else:
            self.model = embedding_model

        if ids_to_descriptions is not None:
            self.id_to_descriptions = ids_to_descriptions
            # make sure that in the id to description dictionary, the id is in the description list
            for key in self.id_to_descriptions:
                if key not in self.id_to_descriptions[key]:
                    self.id_to_descriptions[key] = self.id_to_descriptions[key] + [key]
            self.build_index()
        else:
            self.id_to_descriptions = {}

    def add_id_and_descriptions(self, new_id, description_list, force_rebuild=False):
        self.id_to_descriptions[new_id] = description_list + [new_id]

        if force_rebuild:
            self.build_index()
        else:
            self.words += description_list
            self.ids += [new_id] * len(description_list)
            added_x = self.model.encode(description_list)
            self.index.add(added_x)

    def remove_id(self, id):
        del self.id_to_descriptions[id]
        self.build_index()

    def build_index(self):
        for key in self.id_to_descriptions:
            self.words += self.id_to_descriptions[key]
            self.ids += [key] * len(self.id_to_descriptions[key])

        x = self.model.encode(self.words)
        self.d = x.shape[1]
        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(x)

    def parse_word(self, word, verbose=False):
        filter_word = self.filter_special_word(word)
        if filter_word is not None:
            return filter_word

        # get the embeddings for the words
        test_embedding = self.model.encode(word)

        D, I = self.index.search(np.array([test_embedding]), 1)
        matching_indices = I[0]

        # filter out the words that are not similar enough
        matching_indices = [matching_indices[j] for j in range(len(matching_indices)) if
                               D[0][j] < self.threshold]

        # matching indices is a list of lists, where each list contains the indices of the c
        # now, for each word, find all the categories of the words that are similar to it
        matching_ids = []
        matching_ids.append([self.ids[j] for j in matching_indices])

        if len(matching_ids) == 0:
            matching_ids = ["_unknown_"]

        if verbose:
            # Now, for each word in the test string,
            print(f"Word {word} points to the id {matching_ids}")
            # then show the rounded distances of the words that are similar to it
            for j in range(len(matching_indices)):
                print(f"  Word {self.words[matching_indices[j]]} is at distance {round(D[0][j], 3)}")

        # flatten the list of matching ids to the first in the list
        if len(matching_ids[0]) == 0:
            matching_id = "_unknown_"
        else:
            matching_id = matching_ids[0][0]

        return matching_id

    def filter_special_word(self, word):
        # if the word is a pronoun, then replace it with the last result
        if word in self.pronouns:
            return "it"
        if word in self.articles:
            return "_null_"
        if word in self.conjunctions:
            return "_stop_"
        return None


if __name__ == "__main__":
    id_to_descriptions = {}
    id_to_descriptions['put'] = ["put", "place", "set", "store"]
    id_to_descriptions['get'] = ["get", "fetch", "retrieve", "grab", "take", "bring"]
    id_to_descriptions['page'] = ["webpage", "page", "site", "website"]
    id_to_descriptions['text'] = ["text", "text data", "words", "ascii"]
    id_to_descriptions['at'] = ["from", "found at", "at", "located at", "at the location of"]
    id_to_descriptions['file'] = ["local file", "file", "document", "record"]
    id_to_descriptions['wikipedia'] = ["wiki", "wikipedia", "encyclopedia"]
    id_to_descriptions['in'] = ["in", "into", "inside", "within"]
    id_to_descriptions['search'] = ["search", "look for", "find", "seek", "duckduckgo", "google"]

    # measure the amount of time it takes to get the ids for a sentence
    import time
    start = time.time()
    sm = SemanticMapper(id_to_descriptions)
    print(f"Time to build the index: {time.time() - start}")

    # lets add a new function
    start = time.time()
    sm.add_id_and_descriptions('delete', ["zap", "shoot", "fire", "destroy", "annihilate", "obliterate", "remove"])
    print(f"Time to add a new function: {time.time() - start}")

    sm.parse_word("zap!!", verbose=True)

