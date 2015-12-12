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
    INTEGER = 'int'
    REAL = 'real'
    STRING = 'str'

    @classmethod
    def get_non_paren(cls):
        return (cls.KEYWORD, cls.IDENT, cls.INTEGER, cls.REAL, cls.STRING)


class ExprPatterns:
    IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
    INTEGER = re.compile(r'^[+-]?\d+$')
    REAL = re.compile(r'^[+-]?\d+\.\d+$')


class StdLib:
    @staticmethod
    def add(*values):
        return reduce(operator.add, values)

    @staticmethod
    def subtract(*values):
        return reduce(operator.sub, values)

    @staticmethod
    def multiply(*values):
        return reduce(operator.mul, values)

    @staticmethod
    def divide(*values):
        return reduce(operator.div, values)

    @staticmethod
    def concat(*values):
        return ''.join(map(str, values))


Namespace = {
    '+': StdLib.add,
    '-': StdLib.subtract,
    '*': StdLib.multiply,
    '/': StdLib.divide,
    'str': StdLib.concat,
}


def lazyresolver(s):
    global Namespace

    def resolve():
        return Namespace[s]

    return resolve


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
        (TokenTypes.KEYWORD, lambda s: s in Namespace, lambda s: lazyresolver(s)),
        (TokenTypes.IDENT, ExprPatterns.IDENT.match, lambda s: lazyresolver(s)),
        (TokenTypes.INTEGER, ExprPatterns.INTEGER.match, int),
        (TokenTypes.REAL, ExprPatterns.REAL.match, float),
    )

    def __init__(self, stream):
        self.escape_char = '\\'
        self.char_iter = PeekableStream(stream)

    def __iter__(self):
        return self

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
            if not next_char.isspace() and next_char != ')':
                buf.append(self.char_iter.next())
                continue

            tokenstr = ''.join(buf)
            for tokentype, matcher, mapfunc in self.matchers:
                if matcher(tokenstr):
                    return Token(tokentype, mapfunc(tokenstr))

            raise Exception('unexpected token: %s' % (tokenstr,))

    def next(self):
        for char in self.char_iter:
            if char == '(':
                return Token(TokenTypes.LPAREN)
            elif char == ')':
                return Token(TokenTypes.RPAREN)
            elif char == '"':
                return Token(TokenTypes.STRING, self.get_quoted_string())
            elif not char.isspace():
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


def evaluate(expr):
    func = expr.func.value()
    evaluated_args = []

    for arg in expr.args:
        if isinstance(arg, ParsedExpr):
            evaluated_args.append(evaluate(arg))
        else:
            evaluated_args.append(arg.value)

    return func(*evaluated_args)


if __name__ == '__main__':
    print(StartupMessage)
    while True:
        try:
            expr = raw_input('shitty> ')
            while expr.count('(') != expr.count(')'):
                expr += ' ' + raw_input(' .... > ')
        except KeyboardInterrupt:
            print('Exiting!')
            break

        if expr.strip():
            print(evaluate(Parser(expr).parse()))

