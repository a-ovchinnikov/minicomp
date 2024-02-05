"""A collection of decorators to be used in the emulator"""
from itertools import takewhile
from functools import wraps
import inspect
from inspect import getfullargspec as gfa


help_reg_attr =  "_registered_for_help"


def morph(arg, transform, error_msg):
    """Applies transform to argument with name arg"""
    # NOTE: assumes that decorated function returns a string.
    def decorator(f):
        fargs = gfa(f)
        argindex = fargs.args.index(arg)
        @wraps(f)
        def wrapper(*a, **k):
            try:
                val = a[argindex]
            except IndexError:  # Fallback for default arguments which you don't morph
                return f(*a)
            try:
                newval = transform(a[0], val)  # Passes self along, just in case
            except ValueError as e:
                return error_msg
            except Exception as e:
                # morph() should not raise: it gets arguments to morph direclty
                # from the user an thus must inform them of any unexpected errors.
                return "E: " + str(e)
            newargs = list(a)
            newargs[argindex] = newval
            return f(*newargs)
        # To make @morph reapplicable signature must be also preserved. @wraps
        # does not do this, so must do this manually.
        # Won't work with Python < 3.3
        wrapper.__signature__ = inspect.signature(f)
        return wrapper
    return decorator


def register_help(msg=""):
    """A helper to ensure that user-facing commands could be added to help subsystem

    >>> help_msg = "Do foo"
    >>> @register_help(help_msg)
    ... def foo():
    ...     pass
    >>> getattr(foo, help_reg_attr) == help_msg
    True
    """
    def decorator(f):
        setattr(f,  help_reg_attr, msg if msg else f.__doc__)
        @wraps(f)
        def wrapper(*a, **k):
            return f(*a, **k)
        wrapper.__signature__ = inspect.signature(f)
        return wrapper
    return decorator


# -- missing_args predicates -----
def arg_lacks_default_value(arg):
    return arg.default == arg.empty

def arg_has_default_value(arg):
    return not arg_lacks_default_value(arg)

def funarg(arg, signature):
    return signature.parameters[arg]

def funargs(func):
    """Returns paramter objects of all function arguments

    >>> def foo(bar, baz):
    ...     pass
    >>> funargs(foo)
    [<Parameter "bar">, <Parameter "baz">]
    """
    signature = inspect.signature(func)
    return [funarg(x, signature) for x in signature.parameters.keys()]
# -- End prediactes for missing_args -----------------


def missing_args(msg):
    def decorator(f):
        need_num_args = len(list(takewhile(arg_lacks_default_value, funargs(f))))
        @wraps(f)
        def wrapper(*a, **k):
            # TODO: a smarter check for self?
            if len(a) >= need_num_args:
                return f(*a)
            return msg
        return wrapper
    return decorator


def precondition(condition, error_msg):
    """Intended to check if condition holds for user-supplied values

    Does not raise exceptions, returns a message that is forwarded to a user.
    See _extended_docs() below for further examples.
    """
    def _extended_docs():
        """
        This is a temporary storage place for smaller and simpler tests mixed
        with documentation. There are too many of them to put in the main
        docstring and my syntactic folding is acting funny after the most recent
        update. The tests will sit here until I get back to fixing my folds.

        >>> error_msg = "E: argument too small"

        When decorating a function 'precondition' checks if a precondition is
        satisfied.  This is how a precondition could be set up for a function:
        >>> @precondition("x > 0", error_msg=error_msg)
        ... def echo_positive_number(x):
        ...     return x

        Note that it is passed a string which will be evaluated in the context
        of a decorated function call.

        A correct call to a function does not manifest itself in any way:
        >>> echo_positive_number(42)
        42

        Calling a function with an argument that does not match the
        precondition results in error message being returned to the calling
        process.
        >>> echo_positive_number(-1) == error_msg
        True

        Note, that this interface is use-case specific: the decorator is
        intended to be used with functions that **always** return strings.

        Preconditions could be stacked:
        >>> error_msg_too_big = "E: argument too big"
        >>> @precondition("x > 0", error_msg=error_msg)
        ... @precondition("x < 43", error_msg=error_msg_too_big)
        ... def echo_positive_number(x):
        ...     return x
        >>> echo_positive_number(42)
        42
        >>> echo_positive_number(-1) == error_msg
        True
        >>> echo_positive_number(43) == error_msg_too_big
        True

        Ordering of stacking does not matter, the code below is identical to
        the code above:
        >>> @precondition("x < 43", error_msg=error_msg_too_big)
        ... @precondition("x > 0", error_msg=error_msg)
        ... def echo_capped_positive_number(x):
        ...     return x
        >>> echo_capped_positive_number(42)
        42
        >>> echo_capped_positive_number(-1) == error_msg
        True
        >>> echo_capped_positive_number(43) == error_msg_too_big
        True

        The decorator works the same even if a named value is provided. This
        should not happen here directly, at least at the moment since there is
        no concept of named parameters to minicomp operations, however the
        decorator respects named arguments to reduce the number of surprises in
        the future.
        >>> @precondition("x < 43", error_msg=error_msg_too_big)
        ... @precondition("x > 0", error_msg=error_msg)
        ... def echo_capped_positive_number(x):
        ...     return x
        >>> echo_capped_positive_number(x=42)
        42
        >>> echo_capped_positive_number(x=-1) == error_msg
        True
        >>> echo_capped_positive_number(x=43) == error_msg_too_big
        True

        When a default value is provided preconditions must also be checked:
        >>> @precondition("x < 43", error_msg=error_msg_too_big)
        ... @precondition("x > 0", error_msg=error_msg)
        ... def echo_capped_positive_number(x=20):
        ...     return x
        >>> echo_capped_positive_number(42)
        42
        >>> echo_capped_positive_number()
        20
        >>> echo_capped_positive_number(-1) == error_msg
        True
        >>> echo_capped_positive_number(43) == error_msg_too_big
        True

        Finally, preconditions must hold for all possible combinations of arguments
        with default and non-default parameters.
        >>> @precondition("x < 43", error_msg=error_msg_too_big)
        ... @precondition("x > 0", error_msg=error_msg)
        ... def echo_capped_positive_numbers(x=20, y=20, z=20):
        ...     return x, y, z
        >>> echo_capped_positive_numbers(42, 15, z=10)
        (42, 15, 10)
        >>> echo_capped_positive_numbers(42, y=15, z=10)
        (42, 15, 10)
        >>> echo_capped_positive_numbers(x=42, y=15, z=10)
        (42, 15, 10)
        >>> echo_capped_positive_numbers()
        (20, 20, 20)
        >>> echo_capped_positive_numbers(-1) == error_msg
        True
        >>> echo_capped_positive_numbers(43) == error_msg_too_big
        True

        Here is another session:
        >>> error_message_y_too_big = "E: second argument is too big"
        >>> error_message_y_too_small = "E: second argument is too small"
        >>> error_message_x_too_big = "E: first argument is too big"
        >>> error_message_x_too_small = "E: first argument is too small"
        >>> @precondition("x < 43", error_msg=error_message_x_too_big)
        ... @precondition("x > 0", error_msg=error_message_x_too_small)
        ... @precondition("y > 5", error_msg=error_message_y_too_small)
        ... @precondition("y < 30", error_msg=error_message_y_too_big)
        ... def echo_capped_positive_numbers2(x=20, y=20):
        ...     return x, y
        >>> echo_capped_positive_numbers2(42, 15)
        (42, 15)
        >>> echo_capped_positive_numbers2(42, y=15)
        (42, 15)
        >>> echo_capped_positive_numbers2(x=42, y=15)
        (42, 15)
        >>> echo_capped_positive_numbers2()
        (20, 20)
        >>> echo_capped_positive_numbers2(-1) == error_message_x_too_small
        True
        >>> echo_capped_positive_numbers2(1, 1) == error_message_y_too_small
        True
        >>> echo_capped_positive_numbers2(1, y=1) == error_message_y_too_small
        True
        >>> echo_capped_positive_numbers2(x=1, y=1) == error_message_y_too_small
        True
        >>> echo_capped_positive_numbers2(43) == error_message_x_too_big
        True
        >>> echo_capped_positive_numbers2(x=43) == error_message_x_too_big
        True
        >>> echo_capped_positive_numbers2(43, 31) == error_message_x_too_big
        True
        >>> echo_capped_positive_numbers2(43, y=31) == error_message_x_too_big
        True
        >>> echo_capped_positive_numbers2(x=43, y=31) == error_message_x_too_big
        True
        >>> echo_capped_positive_numbers2(41, 31) == error_message_y_too_big
        True
        >>> echo_capped_positive_numbers2(41, y=31) == error_message_y_too_big
        True
        >>> echo_capped_positive_numbers2(x=41, y=31) == error_message_y_too_big
        True

        """
    def decorator(f):
        @wraps(f)
        def wrapper(*a, **k):
            # Zipping this way is safe since positional arguments cannot follow
            # named arguments.
            from utils import file_accessible
            supplied_args = dict(zip([arg.name for arg in funargs(f)], a))
            # Could also get some keyword arguments.
            supplied_args.update(k)
            # Environment must contain default arguments in case something was not passed
            env = dict((arg.name, arg.default)
                       for arg in filter(arg_has_default_value, funargs(f))
                       if arg.name not in supplied_args)
            # ...and also everything that was passed.
            env.update(supplied_args)
            env["file_accessible"] = file_accessible
            if isinstance(condition, str):
                result = eval(condition, env)
            else:
                return ("IE: this call caused core meltdown. Please record it and pass to "
                        "the maintainer.")
            if result:
                return f(*a, **k)
            return error_msg
        # TODO: make them all belong to stackable class?
        wrapper.__signature__ = inspect.signature(f)
        return wrapper
    return decorator

# TODO: merge it with precondition.
def strict_precond(condition, exception, emsg):
    """Checks internal integrity and raises if a function is passed wrong argument
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*a, **k):
            # Zipping this way is safe since positional arguments cannot follow
            # named arguments.
            supplied_args = dict(zip([arg.name for arg in funargs(f)], a))
            # Could also get some keyword arguments.
            supplied_args.update(k)
            # Environment must contain default arguments in case something was not passed
            env = dict((arg.name, arg.default)
                       for arg in filter(arg_has_default_value, funargs(f))
                       if arg.name not in supplied_args)
            # ...and also everything that was passed.
            env.update(supplied_args)
            if isinstance(condition, str):
                result = eval(condition, env)
            else:
                return ("IE: core meltdown. Please report circumstances to the maintainer.")
            if result:
                return f(*a, **k)
            raise exception(emsg.format(**env))
        # TODO: make them all belong to stackable class?
        wrapper.__signature__ = inspect.signature(f)
        return wrapper
    return decorator
