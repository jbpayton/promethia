import html2text
import requests

def FetchTextFromURL(url):
    """get webpage (from) <url>"""
    response = requests.get(url)
    html_content = response.text

    h = html2text.HTML2Text()
    h.ignore_links = False
    text = h.handle(html_content)
    return text
