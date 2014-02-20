"""
Byte-compile trivial programs with if, while, globals, calls, and
a bit more.
"""

import ast, collections, dis, types
from assembler import op, assemble

def bytecomp(t, f_globals):
    return types.FunctionType(CodeGen().compile(t), f_globals)

class CodeGen(ast.NodeVisitor):

    def __init__(self):
        self.constants = make_table()
        self.names     = make_table()
        self.varnames  = make_table()

    def compile_body(self, body):
        t = body[0]
        if not (isinstance(t, ast.Expr) and isinstance(t.value, ast.Str)):
            self.constants[None] # The doc comment starts the constant table.
        return self.compile(body)

    def compile(self, t):
        bytecode = [self.of(t), self.load_const(None), op.RETURN_VALUE]
        argcount = 0
        kwonlyargcount = 0
        nlocals = 0
        stacksize = 10          # XXX
        flags = 64  # XXX I don't understand the flags
        filename = '<stdin>'
        name = 'the_name'
        firstlineno = 1
        lnotab = b''
        return types.CodeType(argcount, kwonlyargcount, nlocals, stacksize, flags,
                              assemble(bytecode),
                              collect(self.constants),
                              collect(self.names),
                              collect(self.varnames),
                              filename, name, firstlineno, lnotab,
                              freevars=(), cellvars=())

    def of(self, t):
        return list(map(self.of, t)) if isinstance(t, list) else self.visit(t)

    def load_const(self, constant):
        return op.LOAD_CONST(self.constants[constant])

    def store(self, name):
        return op.STORE_NAME(self.names[name])

    def visit_Module(self, t):
        return self.of(t.body)

    def visit_FunctionDef(self, t):
        assert not t.args.args
        assert not t.decorator_list
        code = CodeGen().compile_body(t.body)
        return [self.load_const(code), op.MAKE_FUNCTION(0), self.store(t.name)]

    def visit_If(self, t):
        return {0: [self.of(t.test), op.POP_JUMP_IF_FALSE(1),
                    self.of(t.body), op.JUMP_FORWARD(2)],
                1: [self.of(t.orelse)],
                2: []}

    def visit_While(self, t):
        return {0: [op.SETUP_LOOP(2)],
                1: [self.of(t.test), op.POP_JUMP_IF_FALSE(2),
                    self.of(t.body), op.JUMP_ABSOLUTE(1)],
                2: [op.POP_BLOCK]}

    def visit_Expr(self, t):
        return [self.of(t.value), op.POP_TOP]

    def visit_Assign(self, t):
        assert 1 == len(t.targets) and isinstance(t.targets[0], ast.Name)
        return [self.of(t.value), op.DUP_TOP, self.store(t.targets[0].id)]

    def visit_Call(self, t):
        return [self.of(t.func), self.of(t.args), op.CALL_FUNCTION(len(t.args))]

    def visit_BinOp(self, t):
        return [self.of(t.left), self.of(t.right), self.ops2[type(t.op)]]
    ops2 = {ast.Add:    op.BINARY_ADD,      ast.Sub:      op.BINARY_SUBTRACT,
            ast.Mult:   op.BINARY_MULTIPLY, ast.Div:      op.BINARY_TRUE_DIVIDE,
            ast.Mod:    op.BINARY_MODULO,   ast.Pow:      op.BINARY_POWER,
            ast.LShift: op.BINARY_LSHIFT,   ast.RShift:   op.BINARY_RSHIFT,
            ast.BitOr:  op.BINARY_OR,       ast.BitXor:   op.BINARY_XOR,
            ast.BitAnd: op.BINARY_AND,      ast.FloorDiv: op.BINARY_FLOOR_DIVIDE}

    def visit_Num(self, t):
        return self.load_const(t.n)

    def visit_Str(self, t):
        return self.load_const(t.s)

    def visit_Name(self, t):
        return op.LOAD_NAME(self.names[t.id])

def make_table():
    table = collections.defaultdict(lambda: len(table))
    return table

def collect(table):
    return tuple(sorted(table, key=table.get))


if __name__ == '__main__':

    def diss(code):
        dis.dis(code)
        for c in code.co_consts:
            if isinstance(c, types.CodeType):
                print()
                print('------', c, '------')
                diss(c)

    eg_ast = ast.parse("""
a = 2+3
def f():
    "doc comment"
    while a:
        if a - 1:
            print(a, 137)
        a = a - 1
f()
print(pow(2, 16))
""")
    try:
        import astpp
    except ImportError:
        astpp = ast
    print(astpp.dump(eg_ast))
    f = bytecomp(eg_ast, globals())
    diss(f.__code__)
    f()   # It's alive!
