import asyncio
from typing import TypeVar, Generic, Iterable

T = TypeVar('T')

class MulticastIntent(Generic[T]):
    def __init__(self, targets: Iterable[T]):
        self.targets = targets

    def to(self, targets: Iterable[T]):
        return MulticastIntent(targets)

    def excluding(self, target: T):
        return MulticastIntent(t for t in self.targets if t != target)

    def including(self, target: T):
        return MulticastIntent(t for t in (*self.targets, target))

    def __getattr__(self, item):
        def _(*args, **kwargs):
            coroutines = []
            for target in self.targets:
                ret = getattr(target, item)(*args, **kwargs)
                if asyncio.iscoroutine(ret):
                    coroutines.append(ret)

            async def _():
                for r in coroutines:
                    await r
            return _()
        return _
