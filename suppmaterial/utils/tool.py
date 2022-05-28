import re


def url_param_From_dict(dt):
    params = ""
    for key in dt:
        params = params + key+"="+dt[key]+"&"
    if len(params) > 0:
        params = params[:-1]
    return params

def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)