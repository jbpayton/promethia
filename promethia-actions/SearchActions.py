from duckduckgo_search import DDGS
import wikipedia

def search_wikipedia_0(query):
    """search wikipedia for <query>"""
    output = wikipedia.summary(query, auto_suggest=False)
    return output


def duckduckgo_search_0(query, max_results=5):
    """search web for <query>"""
    # add quotes to the query to search for the exact phrase
    query = f'"{query}"'
    with DDGS() as ddgs:
        results = [result for result in ddgs.text(query, max_results=max_results)]
    print(results)
    return str(results)