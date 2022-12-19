import os.path
import re

from .lexer import tokenize, SyntaxChecker, SYNTAX

IMPORT_REGEX = re.compile(SYNTAX["IMPORT"][1])
DEFINE_REGEX = re.compile(SYNTAX["DEFINE"][1])
STRING_REGEX = re.compile(SYNTAX["STRING"][1])
ID_REGEX = re.compile(SYNTAX["ID"][1])

def preprocess(filepath):
    source_code = combine_code(filepath)
    source_code = process_defines(source_code)
    source_code = process_strings(source_code)
    return source_code

def find_dependencies(filepath):
    source_code = open(filepath, "r").read()
    dependencies = []
    for match in IMPORT_REGEX.finditer(source_code):
        dependencies.append(match.group(1))
    return list(set(dependencies))

def combine_code(filepath):
    filepath = os.path.abspath(filepath)
    project_path = os.path.dirname(filepath)
    files = [filepath]
    i = 0
    while i < len(files):
        dependencies = find_dependencies(files[i])
        dependencies.reverse()
        for dependency in dependencies:
            if dependency.startswith("."):
                dependency_path = os.path.abspath(os.path.join(os.path.dirname(files[i]), dependency))
            else:
                dependency_path = os.path.abspath(os.path.join(project_path, dependency))
            if dependency_path not in files:
                files.append(dependency_path)
        i += 1
    
    files.reverse()
    all_source_code = "\n\n".join(open(file, "r").read().replace("\r", "") for file in files)
    all_source_code = IMPORT_REGEX.sub("", all_source_code)
    return all_source_code

def process_defines(source_code):
    defines = {}
    for match in DEFINE_REGEX.finditer(source_code):
        defines[match.group(1)] = match.group(2)
    source_code = DEFINE_REGEX.sub("", source_code)
    for key, val in defines.items():
        source_code = re.sub(fr"\b{key}\b", val, source_code)
    return source_code

ESCAPE_CHARACTERS = {
    "n": 10,
    "t": 9,
    "\\": 92,
    "\"": 34,
    "r": 13
}
def process_strings(source_code):
    all_possible_ids = set(ID_REGEX.findall(source_code))
    all_strings = set(m.group(1) for m in STRING_REGEX.finditer(source_code))

    all_strings = sorted(all_strings, key=lambda s: len(s), reverse=True)

    i = 0
    for string in all_strings:
        while f"__temp__string_{i}" in all_possible_ids or f"__temp__stringarr_{i}" in all_possible_ids:
            i += 1
        
        temp_string_var = f"__temp__string_{i}"
        temp_stringarr_var = f"__temp__stringarr_{i}"
        all_possible_ids.add(temp_string_var)
        all_possible_ids.add(temp_stringarr_var)

        ascii_values = []
        j = 0
        while j < len(string):
            if string[j] == "\\":
                if string[j + 1] not in ESCAPE_CHARACTERS:
                    raise Exception(f"Invalid escape character: \\{string[j + 1]}")
                ascii_values.append(ESCAPE_CHARACTERS[string[j + 1]])
                j += 2
                continue
            ascii_values.append(ord(string[j]))
            j += 1

        new_source_code = f"{temp_stringarr_var}[{len(ascii_values) + 1}]\n"
        new_source_code += f"{temp_string_var} = {temp_stringarr_var} + 1\n"
        new_source_code += f"{temp_string_var}[-1] = {len(ascii_values)}\n"
        for j, ch in enumerate(ascii_values):
            new_source_code += f"{temp_string_var}[{j}] = {ch}\n"
        
        source_code = source_code.replace(f"\"{string}\"", temp_string_var)
        source_code = new_source_code + "\n\n" + source_code

    return source_code
