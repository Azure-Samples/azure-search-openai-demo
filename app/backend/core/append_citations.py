import re

def append_citations(text_with_sources : str, sources : list[str]) -> str:
    print(text_with_sources)
    regex = r'\[([^\]]+)\]'             
    matches = re.findall(regex, text_with_sources) 
    output = text_with_sources
    
    for source in sources:
        if source not in matches:
            output += "[{cit}]".format(cit = source)
            
    
    return output