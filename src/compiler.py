import pickle
import os.path

from PIL import Image

from .lexer import *
from .grid import PietGrid, Direction
from .piet import PietColor
from .transformer import transform_code

with open(os.path.join(os.path.dirname(__file__), "numgen.pickle"), "rb") as f:
    numgen = pickle.load(f)

def compile(code):
    tokens = tokenize(code)
    checker = SyntaxChecker(tokens)
    if not checker.check("program"):
        print("Syntax Error")
        exit()
    tokens = transform_code(tokens)
    PietCompiler(tokens).compile()

class PietCompiler:
    OPERATORS_TO_COMMANDS = {
        "+": "add",
        "-": "subtract",
        "*": "multiply",
        "/": "divide",
        "%": "mod",
        ">": "greater",
        "<": "push subtract greater not",
        ">=": "push subtract greater",
        "<=": "greater not",
        "==": "subtract not",
        "!=": "subtract not not",
        "and": "multiply not not",
        "or": "add not not"
    }

    def __init__(self, tokens):
        self.tokens = tokens
        self.checker = SyntaxChecker(tokens)
        is_valid = self.checker.check()
        if not is_valid:
            raise Exception("Syntax ERROR")
        self.grid = PietGrid()
        self.painter = self.grid.get_painter()
    
    def compile(self):
        self.compile_program()
        img = self.grid.get_image()
        img.save("output.png")
        scale = 10
        img = img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)
        img.save("output_scaled.png")

    def compile_program(self):
        self.checker.reset()
        self.global_variables = self.checker.add_collector_callback("assignment", 0, lambda path: "function" not in path)
        global_arrays = self.checker.add_collector_callback("array_declaration")
        functions = self.checker.add_collector_callback("function")
        top_level_code = self.checker.add_collector_callback("statement", path_filter=lambda path: path[-1] == "program")
        used_ids = self.checker.add_collector_callback("ID", 0)
        self.checker.check()

        self.used_ids = set(used_ids)

        global_arrays = { x[0] : int(x[2]) for x in global_arrays }
        if self.global_variables & global_arrays.keys():
            raise Exception("Global variables and arrays cannot have the same name")
        self.global_variables = sorted(set(self.global_variables) | global_arrays.keys())
        self.global_variable_sizes = { x : (global_arrays[x] + 1 if x in global_arrays else 1) for x in self.global_variables }
        self.globals_space_size = sum(self.global_variable_sizes.values())
        self.global_variable_indices = {}
        running_sum_index = 0
        for gv in self.global_variables:
            self.global_variable_indices[gv] = running_sum_index
            running_sum_index += self.global_variable_sizes[gv]

        function_names = [f[f.index("func") + 1] for f in functions]

        entry_function_name = "__main__"
        entry_function_number = 0
        while entry_function_name in function_names:
            entry_function_name = "__main__" + str(entry_function_number)
            entry_function_number += 1
        
        arrays_setup_code = []
        for ga in global_arrays:
            arrays_setup_code.extend([ga, "=", str(self.global_variable_indices[ga])])

        top_level_code = sum(top_level_code, [])
        main_function = ["func", entry_function_name, "(", ")", "{"] + arrays_setup_code + top_level_code + ["}"]
        functions.insert(0, main_function)
        function_names.insert(0, entry_function_name)

        used_function_indices = [0]
        i = 0
        while i < len(used_function_indices):
            function_statement = functions[used_function_indices[i]]
            if "variadic" in function_statement[:function_statement.index("func")]:
                for required_function in ("malloc", "free"):
                    if required_function not in function_names:
                        raise Exception("Variadic functions require " + required_function + ". Please import the mem library.")
                    idx = function_names.index(required_function)
                    if idx not in used_function_indices:
                        used_function_indices.append(idx)
            
            function_checker = SyntaxChecker(function_statement)
            function_calls = function_checker.add_collector_callback("function_call", 0)
            function_checker.check()
            for fc in function_calls:
                f_index = next((i for i, f in enumerate(functions) if f[f.index("func") + 1] == fc), None)
                if f_index and f_index not in used_function_indices:
                    used_function_indices.append(f_index)
            i += 1

        functions = [functions[i] for i in sorted(used_function_indices)]
        self.functions = functions
        
        painter = self.painter

        # 0 -1 G 0 0
        self.compile_numbers(0, -1, 0)
        painter.paint(["duplicate"] * (self.globals_space_size + 1))
        
        # wrap around for returning to a function
        painter.forward().dot().move(-1, 4).dot()
        painter.move_to(0, 1).dots_str("00000\n....0\n..0..")
        function_chooser_lane_x = 3

        function_entry_lane_ys = []
        for fid, function in enumerate(functions):
            self.function_id = fid
            self.entry_lane_y = self.grid.get_max_y() + 7
            function_entry_lane_ys.append(self.entry_lane_y)
            painter.move_to(function_chooser_lane_x, self.entry_lane_y).dots([(-1, -1)]).face(Direction.DOWN)
            painter.paint("duplicate not pointer push subtract").move(0, -2).turn_right().paint("pop").forward().dot()
            painter.move_to(function_chooser_lane_x, self.entry_lane_y)
            self.compile_function(function)

        painter.move_to(function_chooser_lane_x, self.grid.get_max_y() + 2)
        painter.dots_str("00O00\n01110\n00000", "black light_red")
        
        cmds = self.number_as_commands(self.globals_space_size + 3)
        cmds.extend(self.number_as_commands(1))
        cmds.append("roll")
        cmds.extend(self.number_as_commands(self.globals_space_size + 2))
        cmds.extend(self.number_as_commands(-2))
        cmds.append("roll")
        painter.move_to(len(cmds) + 1, self.grid.get_max_y() + 2)
        painter.face(Direction.LEFT).paint(cmds)

        painter.move_to(self.grid.get_max_x() + 2, self.grid.get_max_y()).dot()
        for entry_lane_y in function_entry_lane_ys:
            painter.move_to(self.grid.get_max_x() - 1, entry_lane_y - 1).dot()

    def compile_function(self, function):
        painter = self.painter
        painter.face(Direction.RIGHT)
        painter.paint("duplicate not pointer")
        painter.turn_right().paint("pop").forward()
        painter.dots_str("00.\n0.O\n000", "black")
        painter.face(Direction.RIGHT).forward()
        self.entrance_id_counter = 1

        function_checker = SyntaxChecker(function)
        assignments = function_checker.add_collector_callback("assignment", 0)
        parameters = function_checker.add_collector_callback("ID", 0, lambda path: "function_params" in path)
        statement = function_checker.add_collector_callback("statement", path_filter=lambda path: path[-1] == "function")
        functions_called = function_checker.add_collector_callback("function_call", 0)
        function_checker.check()
        
        is_variadic = "variadic" in function[:function.index("func")]
        if is_variadic and len(parameters) != 1:
            raise Exception("Variadic functions must have exactly one parameter")

        if any(True for x in parameters if x in self.global_variables):
            raise Exception("Parameter name conflict with global variable")

        statement = statement[0]
        
        temp_vars = []
        tv_i = 0
        for function_name in functions_called:
            func_index = self.get_function_index(function_name, raise_error=False)
            if func_index is None:
                continue
            func_call_statement = self.functions[func_index]
            if "variadic" not in func_call_statement[:func_call_statement.index("func")]:
                continue
            while (temp_var := f"__temp__var_{tv_i}") in self.used_ids:
                tv_i += 1
            self.used_ids.add(temp_var)
            temp_vars.append(temp_var)
        self.temp_vars = temp_vars

        new_local_variables = sorted(x for x in set(assignments + temp_vars) if x not in self.global_variables and x not in parameters)
        if new_local_variables:
            painter.paint(["push", "not"] + ["duplicate"] * (len(new_local_variables) - 1))
        
        self.local_variables = parameters + new_local_variables
        original_stack_frame_size = len(self.local_variables)
        self.stack_frame_size = original_stack_frame_size
        self.compile_statement(statement)
        self.compile_statement(["return", "0"])

        if self.stack_frame_size != original_stack_frame_size:
            raise Exception("Stack frame size mismatch")
        
        painter.move_to(y=self.entry_lane_y - 1)
        self.compile_numbers(self.stack_frame_size + 1, 1)
        painter.paint(["roll"] + ["pop"] * original_stack_frame_size)
    
    def compile_statement(self, statement):
        first_token = statement[0]
        if first_token == "return":
            self.compile_return_statement(statement)
            return

        if first_token == "{":
            checker = SyntaxChecker(statement[1:-1])
            while checker.has_next():
                st = checker.collect("statement")
                self.compile_statement(st)
            return

        if first_token == "if":
            self.compile_if_statement(statement)
            return
        
        if first_token == "while":
            self.compile_while_statement(statement)
            return
        
        if first_token in ("break", "continue"):
            self.compile_break_continue_statement(statement)
            return

        if SyntaxChecker.quick_check(statement, "assignment"):
            self.compile_assignment(statement)
            return
        
        if SyntaxChecker.quick_check(statement, "array_assignment"):
            self.compile_array_assignment(statement)
            return
        
        if SyntaxChecker.quick_check(statement, "function_call"):
            self.compile_function_call(statement)
            self.painter.paint("pop")
            self.stack_frame_size -= 1
            return

        raise Exception("Unknown statement")

    def compile_return_statement(self, statement):
        self.compile_expression(statement[1:])
        self.stack_frame_size -= 1
        self.compile_number(3)
        forwardAmount = 2
        while not (self.grid.is_noop_path(self.painter.get_x() + 1, self.painter.get_y(), Direction.UP, ey=self.entry_lane_y - 1) \
            and self.grid.get(self.painter.get_x() + 1, self.entry_lane_y - 2) in (PietColor.WHITE, PietColor.BLACK)):
            self.painter.forward(forwardAmount)
            forwardAmount = 1
        self.painter.paint("pointer")
        self.grid.insert(self.painter.get_x(), self.entry_lane_y - 2, "black")

    def compile_if_statement(self, statement):
        checker = SyntaxChecker(statement[1:])
        condition = checker.collect("expression")
        self.compile_numbers(3)
        self.stack_frame_size += 1
        self.compile_expression(condition)
        self.painter.paint("not pointer pop")
        before_statement_x = self.painter.get_x() - 1
        before_statement_y = self.painter.get_y()
        self.stack_frame_size -= 2
        self.compile_statement(checker.collect("statement"))
        if checker.has_next():
            checker.next()
            after_statement_x = self.painter.get_x() + 2
            else_lane_y = self.grid.get_max_y(range(before_statement_x, after_statement_x + 1)) + 2
            self.painter.move_to(before_statement_x, else_lane_y).face(Direction.DOWN).paint("pointer").turn_left()
            self.compile_statement(checker.collect("statement"))
            self.compile_numbers(3)
            after_statement_x = max(after_statement_x, self.painter.get_x() + 3)
            self.painter.move_to(x=after_statement_x - 1).face(Direction.RIGHT).paint("pointer")
            self.painter.move_to(after_statement_x, before_statement_y).dots([(0, -1)])
        else:
            after_statement_x = max(before_statement_x + 8, self.painter.get_x() + 2)
            else_lane_y = self.grid.get_max_y(range(before_statement_x, after_statement_x + 1)) + 2
            self.painter.move_to(before_statement_x, else_lane_y).face(Direction.DOWN).paint("pointer")
            self.painter.face(Direction.RIGHT)
            self.compile_numbers(3)
            self.painter.move_to(x=after_statement_x - 1).paint("pointer")
            self.painter.move_to(y=before_statement_y).dots([(0, -1)])

    def compile_while_statement(self, statement):
        checker = SyntaxChecker(statement[1:])
        condition = checker.collect("expression")
        statement = checker.collect("statement")

        before_statement_y = self.painter.get_y()

        self.painter.forward(2).dots([(0, -1)])
        before_condition_x = self.painter.get_x()

        self.compile_numbers(3, 3)
        self.stack_frame_size += 2
        self.compile_expression(condition)
        self.painter.paint("not pointer pop pop")
        after_condition_x = self.painter.get_x() - 2
        self.stack_frame_size -= 3
        
        self.compile_statement(statement)

        while not self.grid.is_noop_path(self.painter.get_x(), self.painter.get_y() + 1, Direction.UP, ey=self.entry_lane_y - 5) \
            and not self.grid.is_noop_path(self.painter.get_x() - 1, self.entry_lane_y - 5, Direction.RIGHT, ex=self.painter.get_x()):
            self.painter.forward()
        self.painter.dots([(1, 0)])
        self.painter.move_to(y=self.entry_lane_y - 5).move(-1, 0).paint("pointer")
        
        after_statement_x = self.painter.get_x()
        self.painter.move_to(y=before_statement_y)
        self.painter.forward(3)
        while not self.grid.is_noop_path(self.painter.get_x(), self.painter.get_y() + 2, Direction.UP, ey=self.entry_lane_y - 5):
            self.painter.forward()
        self.painter.dots_str("00.\n0.O\n0.0")
        self.grid.insert(self.painter.get_x() + 1, self.entry_lane_y - 5, "black")
        exit_loop_x = self.painter.get_x()
        saved_painter_xy = self.painter.get_xy()
        
        restart_loop_y = self.grid.get_max_y(range(before_condition_x, after_statement_x)) + 1
        self.grid.insert(after_statement_x, restart_loop_y + 1, "black")
        self.grid.insert(before_condition_x - 1, restart_loop_y, "black")

        exit_loop_y = self.grid.get_max_y(range(after_condition_x, exit_loop_x)) + 1
        self.painter.move_to(after_condition_x, exit_loop_y - 1).face(Direction.DOWN).paint("pointer")
        self.painter.move_to(exit_loop_x - 2, exit_loop_y).face(Direction.RIGHT).paint("pointer")
        
        self.painter.move_to(*saved_painter_xy)

    def compile_break_continue_statement(self, statement):
        self.compile_numbers(int(statement[0] == "continue"), 3)
        forwardAmount = 2
        while not self.grid.is_noop_path(self.painter.get_x(), self.painter.get_y(), Direction.UP, ey=self.entry_lane_y - 6):
            self.painter.forward(forwardAmount)
            forwardAmount = 1
        self.painter.paint("pointer")
        self.grid.insert(self.painter.get_x(), self.entry_lane_y - 6, "black")
        self.painter.forward()

    # result of expression left at top of stack
    def compile_expression(self, expression):
        if SyntaxChecker.quick_check(expression, "exp_par"):
            if not expression[-1] == ")":
                raise Exception("Missing closing parenthesis")
            self.compile_expression(expression[1:-1])
            return
        if SyntaxChecker.quick_check(expression, "exp_not"):
            self.compile_expression(expression[1:])
            self.painter.paint("not")
            return
        if SyntaxChecker.quick_check(expression, "NUMBER"):
            self.compile_number(int(expression[0]))
            self.stack_frame_size += 1
            return
        if SyntaxChecker.quick_check(expression, "ID"):
            self.compile_get(expression[0])
            return
        if SyntaxChecker.quick_check(expression, "array_access"):
            self.compile_array_access(expression)
            return
        if SyntaxChecker.quick_check(expression, "function_call"):
            self.compile_function_call(expression)
            return
        if SyntaxChecker.quick_check(expression, "exp_unary"):
            sub_expression = expression[1:] if expression[0] == "-" else expression
            if expression[0] == "-":
                self.compile_expression(["0", "-"] + sub_expression)
            else:
                self.compile_expression(sub_expression)
            return
        
        split_expression_types = ["exp_unary", "exp_mult", "exp_add", "exp_comp", "exp_and", "exp_and", "exp_or"]
        for i in range(1, len(split_expression_types)):
            sub_expression_type = split_expression_types[i - 1]
            expression_type = split_expression_types[i]
            if SyntaxChecker.quick_check(expression, expression_type):
                self.compile_split_expression(expression, sub_expression_type)
                return
        
        raise Exception("Unknown expression")

    def compile_split_expression(self, expression, sub_expression):
        checker = SyntaxChecker(expression)
        left = checker.collect(sub_expression)
        self.compile_expression(left)
        while checker.has_next():
            op = checker.next()
            right = checker.collect(sub_expression)
            self.compile_expression(right)
            self.painter.paint(PietCompiler.OPERATORS_TO_COMMANDS[op])
            self.stack_frame_size -= 1

    def compile_function_call(self, function_call):
        if SyntaxChecker.quick_check(function_call, "builtin_function_call"):
            self.compile_builtin_function_call(function_call)
            return
        
        function_name = function_call[0]
        checker = SyntaxChecker(function_call)
        parameter_expressions = checker.add_collector_callback("expression", path_filter=lambda path: "expression" not in path)
        checker.check()
        num_params = len(parameter_expressions)

        matching_function_index = self.get_function_index(function_name)
        
        callee_function = self.functions[matching_function_index]
        function_checker = SyntaxChecker(callee_function)
        function_parameters = function_checker.add_collector_callback("ID", 0, lambda path: "function_params" in path)
        function_checker.check()
        is_variadic = "variadic" in callee_function[:callee_function.index("func")]

        if not is_variadic and len(function_parameters) != num_params:
            raise Exception("Wrong number of arguments for function call " + function_name)

        saved_stack_frame_size = self.stack_frame_size

        if is_variadic:
            temp_var = self.temp_vars.pop()
            self.compile_statement(tokenize(f"{temp_var} = malloc({num_params})"))
            for ie, expression in enumerate(parameter_expressions):
                self.compile_statement(tokenize(f"{temp_var}[{ie}] =") + expression)
            parameter_expressions = [[temp_var]]
        
        for expression in parameter_expressions:
            self.compile_expression(expression)
        
        self.compile_numbers(self.stack_frame_size, len(parameter_expressions))
        self.painter.paint("roll")
        entrance_id = self.entrance_id_counter
        self.entrance_id_counter += 1
        self.compile_numbers(entrance_id, self.function_id)
        self.compile_numbers(self.globals_space_size + self.stack_frame_size + 2, saved_stack_frame_size + 2)
        self.painter.paint("roll")
        self.compile_numbers(0, matching_function_index, 3)
        
        function_call_exit_y = self.entry_lane_y - 4
        forwardAmount = 2
        while not self.grid.is_noop_path(self.painter.get_x() + 1, self.painter.get_y(), Direction.UP, ey=function_call_exit_y):
            self.painter.forward(forwardAmount)
            forwardAmount = 1
        self.painter.paint("pointer")
        self.grid.insert(self.painter.get_x(), function_call_exit_y, "black")

        # need to move along x until we find free return point
        cmds = ["duplicate"] + self.number_as_commands(entrance_id) + ["subtract", "not", "pointer"]

        self.painter.forward(3)
        while not self.grid.is_noop_path(self.painter.get_x() - len(cmds), self.entry_lane_y, Direction.RIGHT, ex=self.painter.get_x()) \
            or not self.grid.is_noop_path(self.painter.get_x(), self.painter.get_y(), Direction.UP, ey=self.entry_lane_y):
            self.painter.forward(1)
        pxy = self.painter.get_xy()
        self.painter.move_to(y=self.entry_lane_y).move(-len(cmds), 0).paint(cmds)
        self.painter.move_to(*pxy).dots_str("00.\n0.O\n000").paint("pop")

        self.compile_numbers(self.globals_space_size + saved_stack_frame_size + 1, self.globals_space_size)
        self.painter.paint("roll")

        if is_variadic:
            self.compile_statement(tokenize(f"free({temp_var})"))

        self.stack_frame_size = saved_stack_frame_size + 1

    def compile_builtin_function_call(self, function_call):
        function_name = function_call[0]
        parameters = function_call[2:-1]

        if function_name.startswith("print"):
            self.compile_expression(parameters)
            self.painter.paint("out_number" if function_name == "printn" else "out_char")
            self.compile_number(0)
            return
        
        if function_name.startswith("get"):
            self.painter.paint("in_number" if function_name == "getn" else "in_char")
            self.stack_frame_size += 1
            return
        
        if function_name == "exit":
            exit_lane_y = self.entry_lane_y - 4
            self.compile_numbers(0, -1, 3)
            forwardAmount = 2
            while not self.grid.is_noop_path(self.painter.get_x() + 1, self.painter.get_y(), Direction.UP, ey=exit_lane_y):
                self.painter.forward(forwardAmount)
                forwardAmount = 1
            self.painter.paint("pointer")
            self.grid.insert(self.painter.get_x(), exit_lane_y, "black")
            self.compile_number(0)
            self.stack_frame_size += 1
            return

        raise Exception("Unknown builtin function " + function_name)

    def get_distance_from_top(self, identifier):
        if identifier in self.local_variables:
            return self.stack_frame_size - self.local_variables.index(identifier)
        if identifier in self.global_variables:
            return self.stack_frame_size + self.globals_space_size - self.global_variable_indices[identifier]
        raise Exception("Unknown variable")

    # moves the value at the top of the stack to the variable
    def compile_set(self, identifier):
        # inclusive   0 x 0 0|0 x 0 0 results in 3 and 7
        distance_from_top = self.get_distance_from_top(identifier)
        self.compile_numbers(distance_from_top, -1)
        self.painter.paint("roll pop")
        self.compile_numbers(distance_from_top - 1, 1)
        self.painter.paint("roll")
        self.stack_frame_size -= 1

    # brings a copy of the value to the top of the stack
    def compile_get(self, identifier):
        distance_from_top = self.get_distance_from_top(identifier)
        self.compile_numbers(distance_from_top, -1)
        self.painter.paint("roll duplicate")
        self.compile_numbers(distance_from_top + 1, 1)
        self.painter.paint("roll")
        self.stack_frame_size += 1

    def compile_assignment(self, statement):
        identifier = statement[0]
        op = statement[1]
        expression = statement[2:]
        if op != "=":
            self.compile_get(identifier)
        self.compile_expression(expression)
        if op != "=":
            self.painter.paint(PietCompiler.OPERATORS_TO_COMMANDS[op[0]])
            self.stack_frame_size -= 1
        self.compile_set(identifier)

    def compile_get_array_access_location(self, statement):
        last_index_operator = len(statement) - statement[::-1].index("[") - 1
        array_expression = statement[:last_index_operator]
        sub_expression = statement[last_index_operator + 1:-1]

        self.compile_number(self.stack_frame_size + self.globals_space_size - 1)
        self.stack_frame_size += 1
        self.compile_expression(array_expression)
        self.painter.paint("subtract")
        self.stack_frame_size -= 1
        self.compile_expression(sub_expression)
        self.painter.paint("subtract")
        self.stack_frame_size -= 1

    def compile_array_assignment(self, statement):
        checker = SyntaxChecker(statement)
        array_access_statement = checker.collect("array_access")
        checker.next()
        value_expression = checker.collect("expression")

        self.compile_expression(value_expression)
        self.compile_get_array_access_location(array_access_statement)
        
        # number at top of stack is the depth to the value
        self.painter.paint("duplicate push add")
        self.compile_number(-1)
        self.painter.paint("roll pop push subtract push roll")
        self.stack_frame_size -= 2

    def compile_array_access(self, expression):
        self.compile_get_array_access_location(expression)

        # number at top of stack is the depth to the value
        self.painter.paint("duplicate push add")
        self.compile_number(-1)
        self.painter.paint("roll duplicate")
        self.compile_numbers(3, -1)
        self.painter.paint("roll push add push roll")

    def number_as_commands(self, n):
        if not isinstance(n, int):
            raise Exception("Number must be an integer")
        if n < 0:
            return ["push", "not"] + self.number_as_commands(-n) + ["subtract"]
        if n < len(numgen):
            return numgen[n]
        commands = ["push"]
        binary = bin(n)[3:]
        for digit in binary:
            commands.extend(["duplicate", "add"])
            if digit == "1":
                commands.extend(["push", "add"])
        return commands

    def compile_number(self, n):
        self.painter.paint(self.number_as_commands(n))
    def compile_numbers(self, *nums):
        for i, n in enumerate(nums):
            if i > 0 and nums[i - 1] == n:
                self.painter.paint("duplicate")
            else:
                self.compile_number(n)

    def get_function_index(self, function_name, raise_error=True):
        idx = next((i for i, f in enumerate(self.functions) if f[f.index("func") + 1] == function_name), None)
        if idx is None and raise_error:
            raise Exception("Unknown function " + function_name)
        return idx


