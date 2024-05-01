from typing import List, Dict, Set, Tuple


class GrammarElement:
    def __init__(self, value: str, isTerminal: bool = True, forIgnore: bool = False):
        self.value: str = value
        self.isTerminal: bool = isTerminal
        self.forIgnore: bool = forIgnore
        self.follow: Set['GrammarElement'] = set()
        if isTerminal:
            self.first: Set['GrammarElement'] = {self}
        else:
            self.first = set()

        self.productions: List['Production'] = []

    def addProduction(self, production: 'Production'):
        if production not in self.productions:
            self.productions.append(production)
            self.productions = sorted(self.productions)

    def calcFirst(self):
        grammarsFirst = set()
        toEval = list(self.productions)
        while len(toEval) > 0:
            pr = toEval.pop(0)
            pointElement = pr.pointElement()

            if pointElement:
                if pointElement == self:
                    continue
                if pointElement.isTerminal:
                    self.first.add(pointElement)
                if pointElement in grammarsFirst:
                    continue
                grammarsFirst.add(pointElement)
                toEval += list(pointElement.productions)

    def __eq__(self, other):
        if isinstance(other, GrammarElement):
            return self.value == other.value
        return False

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return self.value

    def __lt__(self, other):
        return self.value < other.value


class Production:
    def __init__(self, fromNonTerminal: 'GrammarElement',
                 toResult: List['GrammarElement'] or Tuple['GrammarElement'] or Set['GrammarElement'],
                 number: int,
                 point: int = 0):
        self.fromNonTerminal: GrammarElement = fromNonTerminal
        self.toResult: Tuple['GrammarElement'] = tuple(toResult)
        self.number: int = number
        self.point: int = point
        self.calcFollow()

    def passPoint(self, symbol: GrammarElement):
        if self.point < len(self.toResult):
            if self.toResult[self.point] == symbol:
                return Production(self.fromNonTerminal, self.toResult, self.number, self.point + 1)
        return None

    def pointElement(self):
        if self.point < len(self.toResult):
            return self.toResult[self.point]
        return None

    def closure(self):
        closureSet = {self}

        while True:
            temClosure = set()
            for pr in closureSet:
                pointElement = pr.pointElement()
                if pointElement and not pointElement.isTerminal:
                    for pr2 in pointElement.productions:
                        newPr = Production(pr2.fromNonTerminal, pr2.toResult, pr2.number)
                        if newPr not in closureSet:
                            temClosure.add(newPr)
            if len(temClosure) > 0:
                closureSet = closureSet.union(temClosure)
            else:
                break

        return closureSet

    def calcFollow(self):
        actual = 0
        while actual < len(self.toResult):
            actSt = self.toResult[actual]
            nextSt = None
            if actual + 1 < len(self.toResult):
                nextSt = self.toResult[actual + 1]

            if not actSt.isTerminal:
                if nextSt:
                    if nextSt.isTerminal:
                        actSt.follow.add(nextSt)
                    else:
                        for first in nextSt.first:
                            if first != actSt:
                                actSt.follow.add(first)
                else:
                    for follow in self.fromNonTerminal.follow:
                        actSt.follow.add(follow)

            actual += 1

    def __lt__(self, other):
        return self.number < other.number

    def __eq__(self, other):
        if isinstance(other, Production):
            return ((self.fromNonTerminal, self.toResult, self.point) ==
                    (other.fromNonTerminal, other.toResult, other.point))
        return False

    def __hash__(self):
        return hash((self.fromNonTerminal, self.toResult, self.point))

    def __str__(self):
        return (f"{self.fromNonTerminal} -> "
                f"{' '.join([str(x) for x in self.toResult[:self.point] + ('.',) + self.toResult[self.point:]])}")


class LRO_State:
    def __init__(self, items: List[Production] or Tuple[Production] or Set[Production],
                 number: int):
        self.items: Tuple[Production] = tuple(items)
        self.items: Tuple[Production, ...] = tuple(sorted(self.items))
        self.number: int = number
        self.transitions: Dict[GrammarElement, 'LRO_State'] = {}
        self.finalState: bool = False
        itemsPointTerminal = []
        itemsPointNonTerminal = []
        itemsPointNone = []
        for item in self.items:
            if item.pointElement() is None:
                itemsPointNone.append(item)
                continue
            if item.pointElement().isTerminal:
                itemsPointTerminal.append(item)
                continue
            itemsPointNonTerminal.append(item)

        self.itemsPointTerminal = tuple(sorted(itemsPointTerminal))
        self.itemsPointNonTerminal = tuple(sorted(itemsPointNonTerminal))
        self.itemsPointNone = tuple(sorted(itemsPointNone))

    def passPoint(self, symbol: GrammarElement):
        newItems = set()
        for item in self.items:
            passItem = item.passPoint(symbol)
            if passItem:
                closureNewItem = passItem.closure()
                newItems = newItems.union(closureNewItem)

        if len(newItems) != 0 and symbol.value == '$':
            self.finalState = True
            return tuple()

        return tuple(sorted(newItems))

    def addTransition(self, symbol: GrammarElement, state: 'LRO_State'):
        self.transitions[symbol] = state

    def __hash__(self):
        return hash(self.items)

    def __eq__(self, other):
        if isinstance(other, LRO_State):
            return self.items == other.items
        return False

    def __str__(self):
        return f"State {self.number}\n" + '\n'.join([str(x) for x in self.items])
