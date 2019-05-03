A simple example:
=================

`--scope` defaults to `.` (the toplevel scope of each file).  
`--type` defines what kind of statement it is.

```sh
pysnip --scope . --type classdef Bar file1.py file2.py
```

Shorter:

```sh
pysnip -s . -t classdef Bar file1.py file2.py
```


Using scopes:
=============

Similarly to Python's import system, dots separate the scope names.

```sh
pysnip --scope Bar.method.inner_func --type funcdef baz
```

Separate results
================

Supports an arbitrary length string as separator between results. Also
supports common escapes (e.g., \0, \n, \t)

```sh
pysnip --separator 'foo' --type funcdef baz
```

