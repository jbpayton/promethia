import html2text
import requests
import VariableMap

def store_variable_1(data, name):
    """save <data> (to) variable (named) <name>"""
    VariableMap.VariableMap.get_instance().set_data(name, data)
    return data

def get_variable_1(name):
    """get (from) variable (named) <Var_name>"""
    return VariableMap.VariableMap.get_instance().get_data(name)

def store_file_1(data, name):
    """save <data> (to) file (named) <name>"""
    with open(name, 'w', encoding="utf-8") as f:
        f.write(data)
    return data

def get_file_1(name):
    """get (from) file (named) <name>"""
    with open(name, 'r', encoding="utf-8") as f:
        return f.read()

def webpage_0(url):
    """webpage (from) <url>"""
    response = requests.get(url)
    html_content = response.text

    h = html2text.HTML2Text()
    h.ignore_links = False
    text = h.handle(html_content)
    return text
