#!/usr/bin/env python
#
# shitty.py is a shitty lisp interpreter I wrote in a few hours out of boredom.
# Enjoy how shitty it is.
#
# Copyright (c) 2015 Jimmy Shen
#

from __future__ import print_function

import re
import operator
from collections import deque

StartupMessage = """
 ____  _     _  _____  _____ ___  _
/ ___\/ \ /|/ \/__ __\/__ __\\  \//
|    \| |_||| |  / \    / \   \  /
\___ || | ||| |  | |    | |   / /
\____/\_/ \|\_/  \_/    \_/  /_/
                a really shit lisp.
"""


class TokenTypes:
    LPAREN = '('
    RPAREN = ')'
    KEYWORD = 'keyword'
    IDENT = 'ident'
    NIL = 'nil'
    BOOLEAN = 'bool'
    INTEGER = 'int'
    REAL = 'real'
    STRING = 'str'

    @classmethod
    def get_non_paren(cls):
        return (cls.KEYWORD, cls.IDENT, cls.NIL, cls.BOOLEAN, cls.INTEGER, cls.REAL, cls.STRING)


class ExprPatterns:
    IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
    NIL = re.compile(r'^nil$')
    BOOLEAN = re.compile(r'^(true|false)$')
    INTEGER = re.compile(r'^[+-]?\d+$')
    REAL = re.compile(r'^[+-]?\d+\.\d+$')


class StdLib:
    """All Python implementations of functions accept an `evaluator` function as the
    first argument, which can be used to perform lazy evaluation on arguments"""

    @staticmethod
    def add(_, *values):
        return reduce(operator.add, values)

    @staticmethod
    def subtract(_, *values):
        return reduce(operator.sub, values)

    @staticmethod
    def multiply(_, *values):
        return reduce(operator.mul, values)

    @staticmethod
    def divide(_, *values):
        return reduce(operator.div, values)

    @staticmethod
    def eq(_, a, b):
        return a == b

    @staticmethod
    def ne(_, a, b):
        return a != b

    @staticmethod
    def lt(_, a, b):
        return a < b

    @staticmethod
    def lte(_, a, b):
        return a <= b

    @staticmethod
    def gt(_, a, b):
        return a > b

    @staticmethod
    def gte(_, a, b):
        return a >= b

    @staticmethod
    def not_(_, exp):
        return (not exp)

    @staticmethod
    def concat(_, *values):
        return ''.join(map(str, values))

    @staticmethod
    def cond(evaluator, value, true_expr, else_expr=None):
        value = evaluator(value)
        if value:
            return evaluator(true_expr)

        if else_expr is not None:
            return evaluator(else_expr)

        return None


Namespace = {}


class bind(object):
    __slots__ = ['func', 'lazy_args', 'arity']

    def __init__(self, name, func, lazy_args=False, arity=None):
        global Namespace
        Namespace[name] = self

        self.func = func
        self.lazy_args = lazy_args
        self.arity = arity

    def __call__(self, *args):
        arglen = len(args) - 1
        if isinstance(self.arity, int):
            if arglen != self.arity:
                raise Exception('wrong number of arguments; expected {0}'.format(self.arity))
        elif isinstance(self.arity, basestring):
            if self.arity not in ('*', '+', '?'):
                raise Exception('invalid arity spec')
            elif not (self.arity == '*' or
                    (self.arity == '+' and arglen >= 1) or
                    (self.arity == '?' and arglen <= 1)):
                raise Exception('wrong number of arguments')

        return self.func(*args)


class Resolver(object):
    __slots__ = ['name']

    def __init__(self, name):
        self.name = name

    def resolve(self):
        global Namespace
        return Namespace[self.name]


bind('+', StdLib.add)
bind('-', StdLib.subtract)
bind('*', StdLib.multiply)
bind('/', StdLib.divide)
bind('==', StdLib.eq, arity=2)
bind('!=', StdLib.ne, arity=2)
bind('<', StdLib.lt, arity=2)
bind('<=', StdLib.lte, arity=2)
bind('>', StdLib.gt, arity=2)
bind('>=', StdLib.gte, arity=2)
bind('not', StdLib.not_, arity=1)
bind('str', StdLib.concat)
bind('if', StdLib.cond, lazy_args=True)


class Token(object):
    __slots__ = ['type', 'value']

    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def __repr__(self):
        return 'Token(type=%r, value=%r)' % (self.type, self.value)


class ParsedExpr(object):
    __slots__ = ['func', 'args']

    def __init__(self, func):
        self.func = func
        self.args = []

    def __repr__(self):
        return '(%r [%r])' % (self.func, self.args)


class PeekableStream(object):
    def __init__(self, stream):
        self.queue = deque()
        self.stream = iter(stream)

    def __iter__(self):
        return self

    def peek(self):
        if not self.queue:
            self.queue.append(self.stream.next())

        return self.queue[0]

    def pop(self):
        return self.next()

    def put(self, char):
        self.queue.append(char)

    def next(self):
        if self.queue:
            value = self.queue.popleft()
        else:
            value = self.stream.next()

        return value


class Tokenizer(object):
    matchers = (
        (TokenTypes.NIL, ExprPatterns.NIL.match, lambda _: None),
        (TokenTypes.BOOLEAN, ExprPatterns.BOOLEAN.match, lambda s: s == 'true'),
        (TokenTypes.KEYWORD, lambda s: s in Namespace, Resolver),
        (TokenTypes.IDENT, ExprPatterns.IDENT.match, Resolver),
        (TokenTypes.INTEGER, ExprPatterns.INTEGER.match, int),
        (TokenTypes.REAL, ExprPatterns.REAL.match, float),
    )

    def __init__(self, stream):
        self.escape_char = '\\'
        self.char_iter = PeekableStream(stream)

    def __iter__(self):
        return self

    @staticmethod
    def is_special_char(char):
        return char.isspace() or char in '()"'

    def get_quoted_string(self):
        buf = []
        prevchar = None

        for char in self.char_iter:
            if char == self.escape_char and prevchar != self.escape_char:
                buf.append(char)
            elif char == '"':
                return ''.join(buf)
            else:
                buf.append(char)

            prevchar = char

        raise Exception('quoted string was not terminated!')

    def get_full_token(self):
        buf = []

        while True:
            next_char = self.char_iter.peek()
            if not self.is_special_char(next_char):
                buf.append(self.char_iter.next())
                continue

            tokenstr = ''.join(buf)
            for tokentype, matcher, mapfunc in self.matchers:
                if matcher(tokenstr):
                    return Token(tokentype, mapfunc(tokenstr))

            raise Exception('unexpected token: %s' % (tokenstr,))

    def next(self):
        for char in self.char_iter:
            if self.is_special_char(char):
                if char == '(':
                    return Token(TokenTypes.LPAREN)
                elif char == ')':
                    return Token(TokenTypes.RPAREN)
                elif char == '"':
                    return Token(TokenTypes.STRING, self.get_quoted_string())
            else:
                self.char_iter.put(char)
                return self.get_full_token()

        raise StopIteration


class Parser(object):
    def __init__(self, stream):
        self.tokenstream = PeekableStream(Tokenizer(stream))

    def __iter__(self):
        return self

    def is_ahead(self, *tokentypes):
        token = self.tokenstream.peek()
        return token.type in tokentypes

    def maybe(self, *tokentypes):
        token = self.tokenstream.peek()
        if token.type in tokentypes:
            return self.tokenstream.next()

    def expect(self, *tokentypes):
        token = self.tokenstream.peek()
        if token.type not in tokentypes:
            raise Exception('expected token %s, got %s instead' % (' or '.join(tokentypes), token.type))

        return self.tokenstream.next()

    def nexpect(self, n, tokentypes):
        if n in ('+', '?'):
            yield self.expect(*tokentypes)

        if n in ('+', '*'):
            while True:
                token = self.maybe(*tokentypes)
                if token is not None:
                    yield token
                else:
                    return

        if n == '?':
            yield self.maybe(*tokentypes)
            return

        raise ValueError('unexpected value for "n"')

    def parse(self):
        self.expect(TokenTypes.LPAREN)
        expr = ParsedExpr(self.expect(TokenTypes.KEYWORD, TokenTypes.IDENT))

        while True:
            if self.is_ahead(TokenTypes.LPAREN):
                expr.args.append(self.parse())
            elif self.is_ahead(*TokenTypes.get_non_paren()):
                for token in self.nexpect('*', TokenTypes.get_non_paren()):
                    expr.args.append(token)
            else:
                break

        self.expect(TokenTypes.RPAREN)
        return expr

def evaltoken(token):
    if isinstance(token, ParsedExpr):
        return evaluate(token)
    else:
        return token.value


def evaluate(expr):
    func = expr.func.value.resolve()
    evaluated_args = []

    for token in expr.args:
        if func.lazy_args:
            evaluated_args.append(token)
        else:
            evaluated_args.append(evaltoken(token))

    return func(evaltoken, *evaluated_args)


if __name__ == '__main__':
    print(StartupMessage)
    while True:
        try:
            expr = raw_input('shitty> ')
            while expr.count('(') != expr.count(')'):
                expr += ' ' + raw_input(' .... > ')
        except (EOFError, KeyboardInterrupt):
            print('Exiting!')
            break

        if expr.strip():
            print(evaluate(Parser(expr).parse()))

