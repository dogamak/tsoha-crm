from functools import wraps
import traceback


class MutationAttribute:
    def __init__(self, commit_func):
        self.name = commit_func.__name__
        self.commit_func = commit_func
        self.pre_commit_func = None
        self.describe_func = None
        self.field = None

    def pre_commit(self, func):
        self.pre_commit_func = func
        return func

    def describe(self, func):
        self.describe_func = func
        return func

    def __get__(self, instance, cls):
        self.field = instance
        return self

    def __call__(self, *args, **kwargs):
        return DecoratorMutation(self.field, self, args, kwargs)


class Mutation:
    def __init__(self, field):
        self.field = field

    @property
    def type(self):
        return self.__class__

    def check(self, ctx, *args, **kwargs):
        pass

    def commit(self, ctx, *args, **kwargs):
        pass

    def describe(self, *args, **kwargs):
        pass


class DecoratorMutation(Mutation):
    def __init__(self, field, attr, args, kwargs):
        super().__init__(field)
        self.attr = attr
        self.args = args
        self.kwargs = kwargs

    @property
    def type(self):
        return self.attr

    def check(self, ctx):
        if self.attr.pre_commit_func:
            self.attr.pre_commit_func(self.field, ctx, *self.args, **self.kwargs)

    def commit(self, ctx):
        self.attr.commit_func(self.field, ctx, *self.args, **self.kwargs)

    def describe(self):
        if self.attr.describe_func:
            return self.attr.describe_func(self.field, *self.args, **self.kwargs)


def mutation(func):
    return MutationAttribute(func)


class MutationException:
    def __init__(self, id, message, fatal=True):
        self.id = id
        self.message = message
        self.fatal = fatal
        self.mutation = None


class MutationWarning(MutationException):
    def __init__(self, id, message, dismiss_label=None):
        super().__init__(id, message)
        self.dismiss_label = dismiss_label


class MutationError(MutationException):
    def __init__(self, id, message):
        super().__init__(id, message, fatal=True)


class MutationExceptionPolicy:
    def ignore(self, mutation):
        return False

    def is_fatal(self, mutation):
        return mutation.fatal


class CommitMutationContext:
    def __init__(self, resource, mutation, exception_policy):
        self.resource = resource
        self.mutation = mutation
        self.exceptions = []
        self.failed = False
        self.policy = exception_policy

    def declare(self, exception):
        exception.mutation = self

        self.exceptions.append(exception)

        if self.policy.is_fatal(exception):
            self.failed = True

        return not self.policy.ignore(exception)

    def has_failed(self):
        return self.failed

    def has_exceptions(self):
        return len(self.exceptions) > 0

    def check(self):
        self.mutation.check(self)

    def commit(self):
        self.mutation.commit(self)


class CommitContext:
    def __init__(self, resource, exception_policy=None):
        self.resource = resource
        self.mutations = []
        self.failed = False
        self.exception_policy = exception_policy

        if self.exception_policy is None:
            self.exception_policy = MutationExceptionPolicy()

    def add(self, mutation):
        ctx = CommitMutationContext(self.resource, mutation, self.exception_policy)
        self.mutations.append(ctx)

        ctx.check()

        if ctx.has_failed():
            self.failed = True

    def exceptions(self):
        for ctx in self.mutations:
            yield from ctx.exceptions

    def has_exceptions(self):
        for ctx in self.mutations:
            if ctx.has_exceptions():
                return True

        return False

    def commit(self):
        if self.failed:
            return list(self.exceptions())

        print(self.mutations)

        #try:
        for ctx in self.mutations:
            ctx.commit()
        #except Exception as e:
        #    exceptions = list(self.exceptions())
        #    exceptions.append(MutationException(e.__class__.__name__, str(e), fatal=True))
        #    return exceptions
