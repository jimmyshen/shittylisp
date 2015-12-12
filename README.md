
Shitty lisp is a Lisp written in Python out of boredom. As the name suggests, it is quite a piece of shit. I'll be
tinkering with it to make it less shitty over time but I assure you it will retain some amount of shit regardless.

Here's what sort of works so far:

- Support for various basic types (e.g. nil, boolean, integer, decimal, and string).
- Standard functions include:
  - Arithmetic functions (`+`, `-`, `/`, `*`)
  - Built in string concatenation (`str`)
- Support for conditional evaluation using `if`; arguments are lazily evaluated.

TODO
----

- Add `let`, `def` and `defn`
- Support some basic I/O functionality
- Ability to interop with Python libraries?
