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


class CommitException:
    def __init__(self, id, message, fatal=True, field=None):
        self.id = id
        self.message = message
        self.fatal = fatal
        self.field = field
        self.mutation = None


class CommitWarning(CommitException):
    def __init__(self, id, message, dismiss_label=None, **kwargs):
        super().__init__(id, message, **kwargs)
        self.dismiss_label = dismiss_label


class CommitError(CommitException):
    def __init__(self, id, message, **kwargs):
        super().__init__(id, message, fatal=True, **kwargs)


class CommitExceptionPolicy:
    def ignore(self, exception):
        return False

    def is_fatal(self, exception):
        return exception.fatal


class FieldCommitContext:
    def __init__(self, ctx, field):
        self.parent_ctx = ctx
        self.field = field

    def error(self, *args, **kwargs):
        self.parent_ctx.error(*args, **kwargs, field=self.field)

    def warning(self, *args, **kwargs):
        self.parent_ctx.warning(*args, **kwargs, field=self.field)

    @property
    def resource(self):
        return self.parent_ctx.resource


class CommitMutationContext(FieldCommitContext):
    def __init__(self, ctx, mutation):
        super().__init__(ctx, mutation.field)
        self.mutation = mutation
        self.failed = False

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
        self.exceptions = []

        if self.exception_policy is None:
            self.exception_policy = CommitExceptionPolicy()

    def add(self, mutation, no_check=False):
        ctx = CommitMutationContext(self, mutation)
        self.mutations.append(ctx)

        if not no_check:
            ctx.check()

    def exception(self, exception):
        self.exceptions.append(exception)

        if not self.exception_policy.ignore(exception) and self.exception_policy.is_fatal(exception):
            self.failed = True

    def error(self, *args, **kwargs):
        self.exception(CommitError(*args, **kwargs))

    def warning(self, *args, **kwargs):
        self.exception(CommitWarning(*args, **kwargs))

    def field(self, field):
        if isinstance(field, str):
            field = self.resource.fields[field]

        return FieldCommitContext(self, field)

    def has_exceptions(self):
        return len(self.exceptions) > 0

    def validate(self):
        self.resource.validate(self)

    def commit(self):
        if self.failed:
            return self.exceptions

        #try:
        for ctx in self.mutations:
            ctx.commit()
        #except Exception as e:
        #    exceptions = list(self.exceptions())
        #    exceptions.append(MutationException(e.__class__.__name__, str(e), fatal=True))
        #    return exceptions
