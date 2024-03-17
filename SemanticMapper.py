import re

from sentence_transformers import SentenceTransformer
import faiss

class SemanticMapper:
    def __init__(self, function_ids_to_descriptions = None, similarity_threshold = 0.75, embedding_model = None):
        self.words = []
        self.functions = []
        self.d = 0
        self.index = None

        self.threshold = similarity_threshold

        if embedding_model is None:
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        else:
            self.model = embedding_model

        if function_ids_to_descriptions is not None:
            self.f_id_to_descriptions = function_ids_to_descriptions
            self.build_index()
        else:
            self.f_id_to_descriptions = {}

    def build_index(self):
        for key in self.f_id_to_descriptions:
            self.words += self.f_id_to_descriptions[key]
            self.functions += [key] * len(self.f_id_to_descriptions[key])

        x = self.model.encode(self.words)
        self.d = x.shape[1]
        self.index = faiss.IndexFlatL2(self.d)
        self.index.add(x)

    def get_functions_for_sentence(self, sentence):
        # break the string into words (making sure to take care of punctuation)
        test_words, string_literals, numbers = self.split_string(sentence)

        # get the embeddings for the words
        test_embeddings = self.model.encode(test_words)

        D, I = self.index.search(test_embeddings, 3)
        matching_indices = [I[i] for i in range(len(test_words))]

        # filter out the words that are not similar enough
        for i in range(len(test_words)):
            matching_indices[i] = [matching_indices[i][j] for j in range(len(matching_indices[i])) if
                                   D[i][j] < self.threshold]

        # matching indices is a list of lists, where each list contains the indices of the c
        # now, for each word, find all the categories of the words that are similar to it
        matching_functions = []
        for i in range(len(test_words)):
            matching_functions.append([self.functions[j] for j in matching_indices[i]])

        # Now, for each word in the test string,
        for i in range(len(test_words)):
            print(f"Word {test_words[i]} is in category {matching_functions[i]}")
            # then show the rounded distances of the words that are similar to it
            for j in range(len(matching_indices[i])):
                print(f"  Word {self.words[matching_indices[i][j]]} is at distance {round(D[i][j], 3)}")

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
    f_id_to_descriptions = {}
    f_id_to_descriptions[1] = ["put", "place", "set", "store"]
    f_id_to_descriptions[2] = ["get", "fetch", "retrieve", "grab", "take", "bring"]
    f_id_to_descriptions[3] = ["webpage", "page", "site", "website"]
    f_id_to_descriptions[4] = ["text", "text data", "words", "ascii"]
    f_id_to_descriptions[5] = ["from", "found at", "at", "located at", "at the location of"]
    f_id_to_descriptions[6] = ["local file", "file", "document", "record"]
    f_id_to_descriptions[7] = ["wiki", "wikipedia", "encyclopedia"]
    f_id_to_descriptions[8] = ["in", "into", "inside", "within"]
    f_id_to_descriptions[9] = ["search", "look for", "find", "seek", "duckduckgo", "google"]

    sm = SemanticMapper(f_id_to_descriptions)

    test_string = "Get the text from the webpage 'www.google.com' and store it in the file 'output.txt'"
    sm.get_functions_for_sentence(test_string)

    test_string = "call the function monkeydude 44 times"
    sm.get_functions_for_sentence(test_string)