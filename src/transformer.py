from .lexer import SyntaxChecker, tokenize

def transform_code(tokens):
    transformer = SyntaxTransformer(tokens)
    transformer.transform()
    return transformer.tokens


class STException(Exception):
    def __init__(self, data):
        super().__init__("")
        self.data = data

class SyntaxTransformer:
    def __init__(self, tokens):
        self.tokens = tokens
    
    def transform(self):
        self.collect_unique_ids()
        self.transform_for_loops()
    
    def collect_unique_ids(self):
        checker = SyntaxChecker(self.tokens)
        all_ids = checker.add_collector_callback("ID", 0)
        checker.check()
        self.unique_ids = set(all_ids)
    def make_unique_id(self, base):
        i = 0
        while True:
            id = f"__temp__{base}_{i}"
            if id not in self.unique_ids:
                self.unique_ids.add(id)
                return id
            i += 1

    def transform_for_loops(self):
        def for_loop_callback(_, start, end):
            raise STException((start, end))

        while True:
            try:
                checker = SyntaxChecker(self.tokens)
                checker.add_callback("for_statement", for_loop_callback)
                checker.check()
                break
            except STException as e:
                start, end = e.data
                self.tokens[start:end] = self.transform_for_loop(self.tokens[start:end])
    
    def transform_for_loop(self, tokens):
        checker = SyntaxChecker(tokens)
        initial_assignments = checker.add_collector_callback("assignment_normal", path_filter=lambda path: path[-1] == "for_initial_assignment")
        expression = checker.add_collector_callback("expression", path_filter=lambda path: path[-1] == "for_statement")
        post_assignments = checker.add_collector_callback("assignment", path_filter=lambda path: path[-1] == "for_post_assignment")
        statement = checker.add_collector_callback("statement", path_filter=lambda path: path[-1] == "for_statement")
        checker.check()

        new_tokens = sum(initial_assignments, [])
        temp = self.make_unique_id("for_loop_run_post_assignments")
        new_tokens += tokenize(f"{temp} = 0")
        new_tokens += tokenize("while (1) {")
        new_tokens += tokenize(f"if ({temp})")
        new_tokens += ["{"] + sum(post_assignments, []) + ["}"]
        new_tokens += tokenize(f"{temp} = 1")
        new_tokens += tokenize("if (not (") + expression[0] + tokenize(")) break")
        new_tokens += statement[0]
        new_tokens += ["}"]

        return new_tokens


