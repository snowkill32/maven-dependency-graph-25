"""Порядок подготовки пакетов: зависимости раньше использующего их пакета."""


def dependency_order(root: str, graph: dict[str, list[str]]) -> list[str]:
    """Пройти зависимости до родителей, отклонить цикл и сохранить порядок."""
    order, done, active = [], set(), {root}
    stack = [(root, iter(graph[root]))]
    while stack:
        package, children = stack[-1]
        dependency = next(children, None)
        if dependency is None:
            stack.pop()
            active.remove(package)
            done.add(package)
            order.append(package)
        elif dependency in active:
            path = [name for name, _ in stack]
            path = path[path.index(dependency):] + [dependency]
            raise ValueError("невозможен порядок загрузки: цикл "
                             + " -> ".join(path))
        elif dependency not in done:
            active.add(dependency)
            stack.append((dependency, iter(graph[dependency])))
    return order


def format_load_order(root: str, graph: dict[str, list[str]]) -> str:
    """Вывести последовательность подготовки с исходным пакетом в конце."""
    order = dependency_order(root, graph)
    return "Порядок загрузки: " + " -> ".join(order)
