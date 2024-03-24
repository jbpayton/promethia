import re

from sentence_transformers import SentenceTransformer
import faiss

class SemanticMapper:
    def __init__(self, ids_to_descriptions = None, similarity_threshold = 0.75, embedding_model = None):
        self.words = []
        self.ids = []
        self.d = 0
        self.index = None

        self.threshold = similarity_threshold

        if embedding_model is None:
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        else:
            self.model = embedding_model

        if ids_to_descriptions is not None:
            self.id_to_descriptions = ids_to_descriptions
            self.build_index()
        else:
            self.id_to_descriptions = {}

    def add_id_and_descriptions(self, new_id, description_list, force_rebuild=False):
        self.id_to_descriptions[new_id] = description_list

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

    def parse_string(self, sentence, verbose=False):
        # break the string into words (making sure to take care of punctuation)
        test_words, string_literals, numeric_literals = self.split_string(sentence)

        # get the embeddings for the words
        test_embeddings = self.model.encode(test_words)

        D, I = self.index.search(test_embeddings, 1)
        matching_indices = [I[i] for i in range(len(test_words))]

        # filter out the words that are not similar enough
        for i in range(len(test_words)):
            matching_indices[i] = [matching_indices[i][j] for j in range(len(matching_indices[i])) if
                                   D[i][j] < self.threshold]

        # matching indices is a list of lists, where each list contains the indices of the c
        # now, for each word, find all the categories of the words that are similar to it
        matching_ids = []
        for i in range(len(test_words)):
            matching_ids.append([self.ids[j] for j in matching_indices[i]])

            # if the test word at this index is _s_literal_ or _n_literal_, then replace it with the string or number
            # and make the id _s_literal_ or _n_literal_
            if test_words[i] == "_s_literal_":
                matching_ids[i] = ["_s_literal_"]
                test_words[i] = string_literals.pop(0)
            elif test_words[i] == "_n_literal_":
                matching_ids[i] = ["_n_literal_"]
                test_words[i] = numeric_literals.pop(0)
            elif test_words[i] == "_last_result_":
                matching_ids[i] = ["_last_result_"]
            elif len(matching_ids[i]) == 0:
                matching_ids[i] = ["_unknown_"]

        if verbose:
            # Now, for each word in the test string,
            for i in range(len(test_words)):
                print(f"Word {test_words[i]} points to the id {matching_ids[i]}")
                # then show the rounded distances of the words that are similar to it
                for j in range(len(matching_indices[i])):
                    print(f"  Word {self.words[matching_indices[i][j]]} is at distance {round(D[i][j], 3)}")

        # flatten the list of matching ids to the first in the list
        matching_ids = [matching_ids[i][0] for i in range(len(matching_ids))]
        return test_words, matching_ids

    @staticmethod
    def split_string(string):
        # get all quoted strings stored in a list (single or double quotes)
        quoted_strings = re.findall(r'\"(.+?)\"', string) + re.findall(r'\'(.+?)\'', string)

        # replace the quoted strings with a single word
        for quoted_string in quoted_strings:
            string = string.replace(quoted_string, "_s_literal_")

        # next get rid of all the punctuation except asterisks
        string = re.sub(r'[^\w\s\_]', '', string)

        # next get the numbers and put them in a list
        numbers = re.findall(r'\d+', string)

        # replace the numbers with a single word
        for number in numbers:
            string = string.replace(number, "_n_literal_")

        # split the string into words
        words = string.split()
        words = SemanticMapper.remove_articles(words)
        return words, quoted_strings, numbers

    @staticmethod
    def remove_articles(words):
        articles = ["the", "a", "an"]
        words = [word for word in words if word not in articles]

        pronouns = ["it", "he", "she", "they", "them", "him", "her", "his", "hers", "its", "their", "theirs"]
        # change the pronouns to a single word
        words = [word if word not in pronouns else "_last_result_" for word in words]
        return words


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


    start = time.time()
    test_string = "Get the text from the webpage 'www.google.com' and store it in the file 'output.txt'"
    sm.parse_string(test_string)
    print(f"Time to get the functions for a sentence: {time.time() - start}")

    test_string = "call the function kill monkeydude 44 times"
    sm.parse_string(test_string)
