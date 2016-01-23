#### What's Shitty?

Shitty is a Lisp interpreter I pieced together out of boredom. It is implemented in Python and as the name suggests, it
is a piece of shit. I don't have much experience writing interpreters and such so you can expect that a certain degree
of shittiness will persist even as I continue to tinker and try to improve it.

Here's what (sort of) works so far:

- Support for various basic types (e.g. nil, boolean, integer, decimal, and string).
- Standard functions include:
  - Arithmetic functions (`+`, `-`, `/`, `*`)
  - Comparison functions (`==`, `!=`, `<=`, `<`, etc.)
  - Built in string concatenation (`str`)
- Support for conditional evaluation using `if`; arguments are lazily evaluated.

#### TODO

- Add `let`, `def` and `defn`
- Support some basic I/O functionality
- Ability to interop with Python libraries?
