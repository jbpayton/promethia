import glob
import os
import re

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import hashlib


def getTextPage(text_string, page_num, characters_per_page=256, overlap=64):
    """
    Given a text string, return the text for the specified page number.
    The text is divided into pages of characters_per_page characters.
    The overlap is the number of characters that the pages overlap.
    """
    start = page_num * (characters_per_page - overlap)
    end = start + characters_per_page
    return text_string[start:end]


def getListOfOverlappedPages(text_string, characters_per_page=256, overlap=64):
    """
    Given a text string, return a list of text pages. (without a loop)
    The text is divided into pages of characters_per_page characters.
    The overlap is the number of characters that the pages overlap.
    """
    # calculate the number of pages
    num_pages = len(text_string) // (characters_per_page - overlap)

    # create a list of pages
    pages = [getTextPage(text_string, i, characters_per_page, overlap) for i in range(num_pages)]

    return pages


def calculateHashForString(text_string):
    """
    Given a text string, return the hash of the string.
    """
    return hashlib.md5(text_string.encode()).hexdigest()


def calculateHashForListOfStrings(text_list):
    """
    Given a list of text strings, return the hash of the list.
    """
    text_string = ''.join(text_list)
    return calculateHashForString(text_string)


def calculateHashForFile(file_path):
    """
    Given a file path, return the hash of the file. Without loading the the whole file into memory at once.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def pdfToText(file_path):
    """
    Given a file path to a PDF, return the text of the PDF.
    """
    # import the module
    from pypdf import PdfReader

    # open the PDF file
    pdf_file = open(file_path, 'rb')

    # create a PDF file reader
    pdf_reader = PdfReader(pdf_file)

    # get the number of pages
    num_pages = len(pdf_reader.pages)

    # create a list of pages
    pages = [pdf_reader.pages[i].extract_text() for i in range(num_pages)]

    text = "".join(pages)
    # close the PDF file
    pdf_file.close()

    return text


def calculateHashForDirectory(directory_path):
    """
    Given a directory path, return the hash of the directory.
    """

    # get a list of all text files in the directory
    files = glob.glob(os.path.join(directory_path, "*.txt"))

    # sort the files by name
    files.sort()

    # get the hash of each file
    file_hashes = [calculateHashForFile(file) for file in files]

    # get the hash of the list of file hashes
    return calculateHashForListOfStrings(file_hashes)


def convertStringListToEmbeddings(page_list, model):
    """
    Given a list of text pages, return a list of embeddings.
    """
    return [model.encode(page) for page in page_list]


def getIndexFromListOfEmbeddings(embeddings, cache_file=None):
    """
    Given a list of embeddings, return a Faiss index.
    """
    index = None
    if cache_file is not None:
        try:
            index = faiss.read_index(cache_file)
            return index
        except:
            pass

    if index is None:
        index = faiss.IndexFlatL2(embeddings[0].shape[0])
        index.add(np.array(embeddings))

        if cache_file is not None:
            faiss.write_index(index, cache_file)

    return index


def getIndexFromFile(file_path, model, page_size=256, overlap=64):
    index = None

    # first, lets get hash of the file
    file_hash = calculateHashForFile(file_path)

    # the hash of the file is used to create a cache file
    cache_file = f"{file_hash}.faiss"

    # if the cache file exists, we can load the index from the cache file
    try:
        index = faiss.read_index(cache_file)
        return index
    except:
        pass

    if index is None:
        # if the index is not loaded from the cache file, we need to create the index
        with open(file_path, 'r', encoding="utf-8") as f:
            text_string = f.read()
            pages = getListOfOverlappedPages(text_string, page_size, overlap)
            embeddings = convertStringListToEmbeddings(pages, model)
            index = getIndexFromListOfEmbeddings(embeddings, cache_file)

    return index


def getIndexFromDirectory(directory_path, model, page_size=256, overlap=64):
    index = None

    # first, lets get hash of the directory
    directory_hash = calculateHashForDirectory(directory_path)

    # the hash of the directory is used to create a cache file in the directory
    cache_file = os.path.join(directory_path, f"{directory_hash}.faiss")

    # if the cache file exists, we can load the index from the cache file
    try:
        index = faiss.read_index(cache_file)
        return index
    except:
        pass

    if index is None:
        # if there is an old cache file in the directory, we need to remove it
        old_cache_files = glob.glob(os.path.join(directory_path, '*.faiss'))
        for old_cache_file in old_cache_files:
            os.remove(old_cache_file)

        # if the index is not loaded from the cache file, we need to create the index
        files = glob.glob(os.path.join(directory_path, '*'))
        embeddings = []
        for file in files:
            with open(file, 'r', encoding="utf-8") as f:
                text_string = f.read()
                pages = getListOfOverlappedPages(text_string, page_size, overlap)
                embeddings += convertStringListToEmbeddings(pages, model)

        index = getIndexFromListOfEmbeddings(embeddings, cache_file)

    return index


def pageNumberToOffset(page_number, page_size=256, overlap=64):
    return page_number * (page_size - overlap)


def getSliceAroundOffset(text_string, offset, slice_size):
    start = max(offset - slice_size // 2, 0)
    end = min(offset + slice_size // 2, len(text_string))
    return text_string[start:end]

def getTextAroundPage(text_string, page_number, page_size=256, overlap=64, slice_size=512):
    offset = pageNumberToOffset(page_number, page_size, overlap)
    return getSliceAroundOffset(text_string, offset, slice_size)

def doSubstringMatch(text_string, query_string):
    # match all instances of the query string in the text string
    return [m.start() for m in re.finditer(query_string, text_string)]

def getMostSimilarPages(index, query_embedding, k=3):
    """
    Given a Faiss index, a list of embeddings, a query embedding, and a number of similar pages to return,
    return the indices of the most similar pages.
    """
    D, I = index.search(np.array([query_embedding]), k)
    return I[0]


if __name__ == "__main__":
    # convert pdf to text
    pdf_file = "promethia-memory/NIPS-2017-attention-is-all-you-need-Paper.pdf"
    text = pdfToText(pdf_file)

    text_pages = getListOfOverlappedPages(text)

    # load the model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # create an index
    index = getIndexFromListOfEmbeddings(convertStringListToEmbeddings(text_pages, model))

    # query the index
    query = "attention"
    query_embedding = model.encode(query)
    similar_pages = getMostSimilarPages(index, query_embedding)

    match = doSubstringMatch(text, query)

    print(f"The most similar pages to the query '{query}' are:")
    for page in similar_pages:
        around_page = getTextAroundPage(text, page, slice_size=1024)
        print(around_page)
        print()
        print("-----")
        print()




