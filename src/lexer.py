import json
import re

SYNTAX = json.load(open("./spec.json"))
SYNTAX_DIRECTIVES = ("REGEX_MATCH", "ONE_OF", "REPEAT", "OPTIONAL")

def find_special_tokens(syntax="program", visited=set()):
    if isinstance(syntax, str):
        if syntax in SYNTAX_DIRECTIVES:
            return set()
        if syntax in SYNTAX:
            if syntax in visited:
                return set()
            visited.add(syntax)
            return find_special_tokens(SYNTAX[syntax], visited)
        return { syntax }
    if isinstance(syntax, list):
        tokens = set()
        for i, item in enumerate(syntax):
            if i > 0 and syntax[i - 1] == "REGEX_MATCH":
                continue
            tokens |= find_special_tokens(item, visited)
        return tokens
    raise Exception("Unknown syntax type: " + str(syntax))

def clean_tokens(tokens):
    return sorted(tokens, key=lambda x: -len(x))

SPECIAL_TOKENS = clean_tokens(find_special_tokens())
REGEX_MATCHES = [v[1] for _, v in SYNTAX.items() if v[0] == "REGEX_MATCH"]

def tokenize(code):
    tokens = []
    while code:
        if code[0].isspace():
            code = code[1:]
            continue
        next_token = None
        for special_token in SPECIAL_TOKENS:
            special_token: str
            if special_token.isalpha():
                if match := re.match(fr"{special_token}\b", code):
                    next_token = match.group(0)
                    break
            elif code.startswith(special_token):
                next_token = special_token
                break
        else:
            for rm in REGEX_MATCHES:
                if match := re.match(rm, code):
                    next_token = match.group(0)
                    break
        if next_token is not None:
            tokens.append(next_token)
            code = code[len(next_token):]
        else:
            raise Exception("Unknown token: " + code[:50])
    return tokens

class SyntaxChecker:
    def __init__(self, tokens):
        self.tokens = tokens
        self.reset()
    
    def reset(self, current=-1):
        self.current = current
        self.callbacks = {}
        self.current_path = []
        self.log = []
    
    def next(self):
        self.current += 1
        return self.tokens[self.current]
    
    def has_next(self):
        return self.current < len(self.tokens) - 1

    def check(self, syntax="program", allow_leftovers=False):
        result = None
        if isinstance(syntax, str):
            if syntax in SYNTAX:
                old_current = self.current
                self.current_path.append(syntax)
                result = self.check(SYNTAX[syntax], True)
                self.current_path.pop()
                if not allow_leftovers and self.has_next():
                    result = False
                if result and syntax in self.callbacks:
                    for callback in self.callbacks[syntax]:
                        callback(self, old_current + 1, self.current + 1)
            else:
                result = self.has_next() and self.next() == syntax
        elif isinstance(syntax, list):
            index = 0
            while index < len(syntax):
                item = syntax[index]
                if item in SYNTAX_DIRECTIVES:
                    index += 1
                    if not getattr(self, "check_" + item.lower())(syntax[index]):
                        result = False
                        break
                elif not self.check(item, True):
                    result = False
                    break
                index += 1
            else:
                result = True
        else:
            raise Exception("Unknown syntax type: " + str(syntax))
        return result

    def check_regex_match(self, regex):
        if not self.has_next() or not re.fullmatch(regex, self.next()):
            return False
        return True
    
    def check_one_of(self, choices):
        current = self.current
        for choice in choices:
            if self.check(choice, True):
                return True
            self.current = current
        return False
    
    def check_repeat(self, repeat_syntax):
        while self.has_next():
            current = self.current
            if not self.check(repeat_syntax, True):
                self.current = current
                break
        return True
    
    def check_optional(self, optional_syntax):
        current = self.current
        if not self.check(optional_syntax, True):
            self.current = current
        return True

    def add_callback(self, syntax, callback):
        self.callbacks[syntax] = self.callbacks.get(syntax, []) + [callback]

    def add_collector_callback(self, syntax, index=None, path_filter=None):
        collection = []
        def callback(syntax_checker, start, end):
            if path_filter is not None and not path_filter(syntax_checker.current_path):
                return
            tokens = syntax_checker.tokens[start:end]
            if index is not None:
                tokens = tokens[index]
            collection.append(tokens)
        self.add_callback(syntax, callback)
        return collection

    def collect(self, syntax, start=None):
        if start is None:
            start = self.current + 1
        self.reset(start - 1)
        if not self.check(syntax, True):
            raise Exception("SyntaxChecker collect failed for " + str(syntax))
        return self.tokens[start:self.current + 1]
    
    # def get_code_around(self, token_index, before=2, after=0):
    #     code_index = self.token_indices[token_index]
    #     before_code_index = code_index
    #     for _ in range(before+1):
    #         before_code_index = max(0, self.source_code.rfind("\n", 0, before_code_index))
    #     after_code_index = code_index
    #     for _ in range(after+1):
    #         after_code_index = max(after_code_index, self.source_code.find("\n", after_code_index + 1))
    #     return self.source_code[before_code_index:after_code_index].strip("\n")
    
    # def get_code_around_with_pointer(self, token_index, before=2, after=0):
    #     before_code = self.get_code_around(token_index, before, 0)
    #     index_in_line = len(before_code.rpartition("\n")[2])
    #     pointer_line = "\n" + " " * index_in_line + "^\n"
    #     after_code = self.get_code_around(token_index, 0, after).partition("\n")[2]
    #     return before_code + pointer_line + after_code

    @staticmethod
    def quick_check(tokens, syntax):
        return SyntaxChecker(tokens).check(syntax)

