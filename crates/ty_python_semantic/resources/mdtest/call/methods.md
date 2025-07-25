# Methods

## Background: Functions as descriptors

> Note: See also this related section in the descriptor guide: [Functions and methods].

Say we have a simple class `C` with a function definition `f` inside its body:

```py
class C:
    def f(self, x: int) -> str:
        return "a"
```

Whenever we access the `f` attribute through the class object itself (`C.f`) or through an instance
(`C().f`), this access happens via the descriptor protocol. Functions are (non-data) descriptors
because they implement a `__get__` method. This is crucial in making sure that method calls work as
expected. In general, the signature of the `__get__` method in the descriptor protocol is
`__get__(self, instance, owner)`. The `self` argument is the descriptor object itself (`f`). The
passed value for the `instance` argument depends on whether the attribute is accessed from the class
object (in which case it is `None`), or from an instance (in which case it is the instance of type
`C`). The `owner` argument is the class itself (`C` of type `Literal[C]`). To summarize:

- `C.f` is equivalent to `getattr_static(C, "f").__get__(None, C)`
- `C().f` is equivalent to `getattr_static(C, "f").__get__(C(), C)`

Here, `inspect.getattr_static` is used to bypass the descriptor protocol and directly access the
function attribute. The way the special `__get__` method *on functions* works is as follows. In the
former case, if the `instance` argument is `None`, `__get__` simply returns the function itself. In
the latter case, it returns a *bound method* object:

```py
from inspect import getattr_static

reveal_type(getattr_static(C, "f"))  # revealed: def f(self, x: int) -> str

reveal_type(getattr_static(C, "f").__get__)  # revealed: <method-wrapper `__get__` of `f`>

reveal_type(getattr_static(C, "f").__get__(None, C))  # revealed: def f(self, x: int) -> str
reveal_type(getattr_static(C, "f").__get__(C(), C))  # revealed: bound method C.f(x: int) -> str
```

In conclusion, this is why we see the following two types when accessing the `f` attribute on the
class object `C` and on an instance `C()`:

```py
reveal_type(C.f)  # revealed: def f(self, x: int) -> str
reveal_type(C().f)  # revealed: bound method C.f(x: int) -> str
```

A bound method is a callable object that contains a reference to the `instance` that it was called
on (can be inspected via `__self__`), and the function object that it refers to (can be inspected
via `__func__`):

```py
bound_method = C().f

reveal_type(bound_method.__self__)  # revealed: C
reveal_type(bound_method.__func__)  # revealed: def f(self, x: int) -> str
```

When we call the bound method, the `instance` is implicitly passed as the first argument (`self`):

```py
reveal_type(C().f(1))  # revealed: str
reveal_type(bound_method(1))  # revealed: str
```

When we call the function object itself, we need to pass the `instance` explicitly:

```py
C.f(1)  # error: [missing-argument]

reveal_type(C.f(C(), 1))  # revealed: str
```

When we access methods from derived classes, they will be bound to instances of the derived class:

```py
class D(C):
    pass

reveal_type(D().f)  # revealed: bound method D.f(x: int) -> str
```

If we access an attribute on a bound method object itself, it will defer to `types.MethodType`:

```py
reveal_type(bound_method.__hash__)  # revealed: bound method MethodType.__hash__() -> int
```

If an attribute is not available on the bound method object, it will be looked up on the underlying
function object. We model this explicitly, which means that we can access `__kwdefaults__` on bound
methods, even though it is not available on `types.MethodType`:

```py
reveal_type(bound_method.__kwdefaults__)  # revealed: dict[str, Any] | None
```

## Basic method calls on class objects and instances

```py
class Base:
    def method_on_base(self, x: int | None) -> str:
        return "a"

class Derived(Base):
    def method_on_derived(self, x: bytes) -> tuple[int, str]:
        return (1, "a")

reveal_type(Base().method_on_base(1))  # revealed: str
reveal_type(Base.method_on_base(Base(), 1))  # revealed: str

Base().method_on_base("incorrect")  # error: [invalid-argument-type]
Base().method_on_base()  # error: [missing-argument]
Base().method_on_base(1, 2)  # error: [too-many-positional-arguments]

reveal_type(Derived().method_on_base(1))  # revealed: str
reveal_type(Derived().method_on_derived(b"abc"))  # revealed: tuple[int, str]
reveal_type(Derived.method_on_base(Derived(), 1))  # revealed: str
reveal_type(Derived.method_on_derived(Derived(), b"abc"))  # revealed: tuple[int, str]
```

## Method calls on literals

### Boolean literals

```py
reveal_type(True.bit_length())  # revealed: int
reveal_type(True.as_integer_ratio())  # revealed: tuple[int, Literal[1]]
```

### Integer literals

```py
reveal_type((42).bit_length())  # revealed: int
```

### String literals

```py
reveal_type("abcde".find("abc"))  # revealed: int
reveal_type("foo".encode(encoding="utf-8"))  # revealed: bytes

"abcde".find(123)  # error: [invalid-argument-type]
```

### Bytes literals

```py
reveal_type(b"abcde".startswith(b"abc"))  # revealed: bool
```

## Method calls on `LiteralString`

```py
from typing_extensions import LiteralString

def f(s: LiteralString) -> None:
    reveal_type(s.find("a"))  # revealed: int
```

## Method calls on `tuple`

```py
def f(t: tuple[int, str]) -> None:
    reveal_type(t.index("a"))  # revealed: int
```

## Method calls on unions

```py
from typing import Any

class A:
    def f(self) -> int:
        return 1

class B:
    def f(self) -> str:
        return "a"

def f(a_or_b: A | B, any_or_a: Any | A):
    reveal_type(a_or_b.f)  # revealed: (bound method A.f() -> int) | (bound method B.f() -> str)
    reveal_type(a_or_b.f())  # revealed: int | str

    reveal_type(any_or_a.f)  # revealed: Any | (bound method A.f() -> int)
    reveal_type(any_or_a.f())  # revealed: Any | int
```

## Method calls on `KnownInstance` types

```toml
[environment]
python-version = "3.12"
```

```py
type IntOrStr = int | str

reveal_type(IntOrStr.__or__)  # revealed: bound method typing.TypeAliasType.__or__(right: Any) -> _SpecialForm
```

## Method calls on types not disjoint from `None`

Very few methods are defined on `object`, `None`, and other types not disjoint from `None`. However,
descriptor-binding behavior works on these types in exactly the same way as descriptor binding on
other types. This is despite the fact that `None` is used as a sentinel internally by the descriptor
protocol to indicate that a method was accessed on the class itself rather than an instance of the
class:

```py
from typing import Protocol, Literal
from ty_extensions import AlwaysFalsy

class Foo: ...

class SupportsStr(Protocol):
    def __str__(self) -> str: ...

class Falsy(Protocol):
    def __bool__(self) -> Literal[False]: ...

def _(a: object, b: SupportsStr, c: Falsy, d: AlwaysFalsy, e: None, f: Foo | None):
    a.__str__()
    b.__str__()
    c.__str__()
    d.__str__()
    # TODO: these should not error
    e.__str__()  # error: [missing-argument]
    f.__str__()  # error: [missing-argument]
```

## Error cases: Calling `__get__` for methods

The `__get__` method on `types.FunctionType` has the following overloaded signature in typeshed:

```pyi
from types import FunctionType, MethodType
from typing import overload

@overload
def __get__(self, instance: None, owner: type, /) -> FunctionType: ...
@overload
def __get__(self, instance: object, owner: type | None = None, /) -> MethodType: ...
```

Here, we test that this signature is enforced correctly:

```py
from inspect import getattr_static

class C:
    def f(self, x: int) -> str:
        return "a"

method_wrapper = getattr_static(C, "f").__get__

reveal_type(method_wrapper)  # revealed: <method-wrapper `__get__` of `f`>

# All of these are fine:
method_wrapper(C(), C)
method_wrapper(C())
method_wrapper(C(), None)
method_wrapper(None, C)

reveal_type(object.__str__.__get__(object(), None)())  # revealed: str

# TODO: passing `None` without an `owner` argument fails at runtime.
# Ideally we would emit a diagnostic here:
method_wrapper(None)

# Passing something that is not assignable to `type` as the `owner` argument is an
# error: [no-matching-overload] "No overload of method wrapper `__get__` of function `f` matches arguments"
method_wrapper(None, 1)

# TODO: passing `None` as the `owner` argument when `instance` is `None` fails at runtime.
# Ideally we would emit a diagnostic here.
method_wrapper(None, None)

# Calling `__get__` without any arguments is an
# error: [no-matching-overload] "No overload of method wrapper `__get__` of function `f` matches arguments"
method_wrapper()

# Calling `__get__` with too many positional arguments is an
# error: [no-matching-overload] "No overload of method wrapper `__get__` of function `f` matches arguments"
method_wrapper(C(), C, "one too many")
```

## Fallback to metaclass

When a method is accessed on a class object, it is looked up on the metaclass if it is not found on
the class itself. This also creates a bound method that is bound to the class object itself:

```py
from __future__ import annotations

class Meta(type):
    def f(cls, arg: int) -> str:
        return "a"

class C(metaclass=Meta):
    pass

reveal_type(C.f)  # revealed: bound method <class 'C'>.f(arg: int) -> str
reveal_type(C.f(1))  # revealed: str
```

The method `f` can not be accessed from an instance of the class:

```py
# error: [unresolved-attribute] "Type `C` has no attribute `f`"
C().f
```

A metaclass function can be shadowed by a method on the class:

```py
from typing import Any, Literal

class D(metaclass=Meta):
    def f(arg: int) -> Literal["a"]:
        return "a"

reveal_type(D.f(1))  # revealed: Literal["a"]
```

If the class method is possibly unbound, we union the return types:

```py
def flag() -> bool:
    return True

class E(metaclass=Meta):
    if flag():
        def f(arg: int) -> Any:
            return "a"

reveal_type(E.f(1))  # revealed: str | Any
```

## `@classmethod`

### Basic

When a `@classmethod` attribute is accessed, it returns a bound method object, even when accessed on
the class object itself:

```py
from __future__ import annotations

class C:
    @classmethod
    def f(cls: type[C], x: int) -> str:
        return "a"

reveal_type(C.f)  # revealed: bound method <class 'C'>.f(x: int) -> str
reveal_type(C().f)  # revealed: bound method type[C].f(x: int) -> str
```

The `cls` method argument is then implicitly passed as the first argument when calling the method:

```py
reveal_type(C.f(1))  # revealed: str
reveal_type(C().f(1))  # revealed: str
```

When the class method is called incorrectly, we detect it:

```py
C.f("incorrect")  # error: [invalid-argument-type]
C.f()  # error: [missing-argument]
C.f(1, 2)  # error: [too-many-positional-arguments]
```

If the `cls` parameter is wrongly annotated, we emit an error at the call site:

```py
class D:
    @classmethod
    def f(cls: D):
        # This function is wrongly annotated, it should be `type[D]` instead of `D`
        pass

# error: [invalid-argument-type] "Argument to bound method `f` is incorrect: Expected `D`, found `<class 'D'>`"
D.f()
```

When a class method is accessed on a derived class, it is bound to that derived class:

```py
class Derived(C):
    pass

reveal_type(Derived.f)  # revealed: bound method <class 'Derived'>.f(x: int) -> str
reveal_type(Derived().f)  # revealed: bound method type[Derived].f(x: int) -> str

reveal_type(Derived.f(1))  # revealed: str
reveal_type(Derived().f(1))  # revealed: str
```

### Accessing the classmethod as a static member

Accessing a `@classmethod`-decorated function at runtime returns a `classmethod` object. We
currently don't model this explicitly:

```py
from inspect import getattr_static

class C:
    @classmethod
    def f(cls): ...

reveal_type(getattr_static(C, "f"))  # revealed: def f(cls) -> Unknown
reveal_type(getattr_static(C, "f").__get__)  # revealed: <method-wrapper `__get__` of `f`>
```

But we correctly model how the `classmethod` descriptor works:

```py
reveal_type(getattr_static(C, "f").__get__(None, C))  # revealed: bound method <class 'C'>.f() -> Unknown
reveal_type(getattr_static(C, "f").__get__(C(), C))  # revealed: bound method <class 'C'>.f() -> Unknown
reveal_type(getattr_static(C, "f").__get__(C()))  # revealed: bound method type[C].f() -> Unknown
```

The `owner` argument takes precedence over the `instance` argument:

```py
reveal_type(getattr_static(C, "f").__get__("dummy", C))  # revealed: bound method <class 'C'>.f() -> Unknown
```

### Classmethods mixed with other decorators

```toml
[environment]
python-version = "3.12"
```

When a `@classmethod` is additionally decorated with another decorator, it is still treated as a
class method:

```py
from __future__ import annotations

def does_nothing[T](f: T) -> T:
    return f

class C:
    @classmethod
    @does_nothing
    def f1(cls: type[C], x: int) -> str:
        return "a"

    @does_nothing
    @classmethod
    def f2(cls: type[C], x: int) -> str:
        return "a"

reveal_type(C.f1(1))  # revealed: str
reveal_type(C().f1(1))  # revealed: str
reveal_type(C.f2(1))  # revealed: str
reveal_type(C().f2(1))  # revealed: str
```

## `@staticmethod`

### Basic

When a `@staticmethod` attribute is accessed, it returns the underlying function object. This is
true whether it's accessed on the class or on an instance of the class.

```py
from __future__ import annotations

class C:
    @staticmethod
    def f(x: int) -> str:
        return "a"

reveal_type(C.f)  # revealed: def f(x: int) -> str
reveal_type(C().f)  # revealed: def f(x: int) -> str
```

The method can then be called like a regular function from either the class or an instance, with no
implicit first argument passed.

```py
reveal_type(C.f(1))  # revealed: str
reveal_type(C().f(1))  # revealed: str
```

When the static method is called incorrectly, we detect it:

```py
C.f("incorrect")  # error: [invalid-argument-type]
C.f()  # error: [missing-argument]
C.f(1, 2)  # error: [too-many-positional-arguments]
```

When a static method is accessed on a derived class, it behaves identically:

```py
class Derived(C):
    pass

reveal_type(Derived.f)  # revealed: def f(x: int) -> str
reveal_type(Derived().f)  # revealed: def f(x: int) -> str

reveal_type(Derived.f(1))  # revealed: str
reveal_type(Derived().f(1))  # revealed: str
```

### Accessing the staticmethod as a static member

```py
from inspect import getattr_static

class C:
    @staticmethod
    def f(): ...
```

Accessing the staticmethod as a static member. This will reveal the raw function, as `staticmethod`
is transparent when accessed via `getattr_static`.

```py
reveal_type(getattr_static(C, "f"))  # revealed: def f() -> Unknown
```

The `__get__` of a `staticmethod` object simply returns the underlying function. It ignores both the
instance and owner arguments.

```py
reveal_type(getattr_static(C, "f").__get__(None, C))  # revealed: def f() -> Unknown
reveal_type(getattr_static(C, "f").__get__(C(), C))  # revealed: def f() -> Unknown
reveal_type(getattr_static(C, "f").__get__(C()))  # revealed: def f() -> Unknown
reveal_type(getattr_static(C, "f").__get__("dummy", C))  # revealed: def f() -> Unknown
```

### Staticmethods mixed with other decorators

```toml
[environment]
python-version = "3.12"
```

When a `@staticmethod` is additionally decorated with another decorator, it is still treated as a
static method:

```py
from __future__ import annotations

def does_nothing[T](f: T) -> T:
    return f

class C:
    @staticmethod
    @does_nothing
    def f1(x: int) -> str:
        return "a"

    @does_nothing
    @staticmethod
    def f2(x: int) -> str:
        return "a"

reveal_type(C.f1(1))  # revealed: str
reveal_type(C().f1(1))  # revealed: str
reveal_type(C.f2(1))  # revealed: str
reveal_type(C().f2(1))  # revealed: str
```

[functions and methods]: https://docs.python.org/3/howto/descriptor.html#functions-and-methods
