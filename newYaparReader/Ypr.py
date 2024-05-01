import graphviz
import tabulate

from Machines_gen_usage import import_module, simulator
import pickle
from typing import *
from classes import *
import pandas as pd

from YaPar_reader.SLR_simulater import SLR_simulate


# Create a class named YpReader
def drawDiagramAndSave(initState, explicit, expression='Dinamo'):
    dot: 'graphviz.graphs.Digraph' = graphviz.Digraph(comment='LR0')
    dot.attr(rankdir='LR')
    setStates = set()
    dot.attr(label='Hola')

    def draw_state(state: 'LRO_State'):
        nonlocal explicit
        setStates.add(state)
        name = str(state.number) if explicit else str(state)
        dot.node(str(state.number), label=name,
                 shape='doublecircle' if state.finalState else 'circle')
        for transition in state.transitions:
            destiny = state.transitions[transition]
            if destiny not in setStates:
                draw_state(destiny)
            dot.edge(str(state.number), str(destiny.number), label=transition.value)

    draw_state(initState)

    typeGraph = 'explicit' if explicit else 'implicit'

    dot.render('LR0_' + typeGraph + '.gv', view=True, directory='./LR0/' + expression)


class YpReader:
    def __init__(self, path):
        # Reader content of archive
        with open(path, 'r') as file:
            self.content: str = file.read()

        if self.content == '':
            raise Exception('File is empty')

        self.tokens: Dict[str, GrammarElement] = {}
        self.productions: Dict[Production, Production] = {}
        self.LR0States: Dict[LRO_State, LRO_State] = {}

    def analyzeContent(self):
        # Define the parts of the Yapar language
        YpParts = {
            'COMMENT': ['/\*', '\*/'],
            'TOKEN': ['%token [A-Z]+( [A-Z]+)*', 'IGNORE [A-Z]+( [A-Z]+)*'],
            'PRODUCTION': ['[a-z]+:([a-zA-Z]| |\n|\|)+;']
        }

        # Import the machineLector module
        machineLector = import_module('machineLector.py', YpParts, directory='./')

        # Simulate the machineLector
        result = simulator(machineLector, self.content)
        temPrs = {}
        inComment = False
        initProd = ''
        for message, token in result:
            if token == 'COMMENT':
                inComment = message == '/*'
                continue

            if inComment or token == 0:
                continue

            if token == 'TOKEN':
                if '%token' in message:
                    message = message.replace('%token', '').strip()
                    tokens = [x.strip() for x in message.split(' ') if x != '' or x != ' ']
                    for tk in tokens:
                        self.tokens[tk] = GrammarElement(tk)
                    continue
                elif 'IGNORE' in message:
                    message = message.replace('IGNORE', '').strip()
                    tokens = [x.strip() for x in message.split(' ') if x != '' or x != ' ']
                    for tk in tokens:
                        self.tokens[tk].forIgnore = True

            if token == 'PRODUCTION':
                message = message.split(':')
                prodName = message[0]
                self.tokens[prodName] = GrammarElement(prodName, isTerminal=False)
                initProd = prodName if initProd == '' else initProd
                prod = message[1].replace(';', '').strip()
                temPrs[prodName] = prod

        self.tokens['$'] = GrammarElement('$')
        self.tokens[initProd + '\''] = GrammarElement(initProd + '\'')
        initProduction = Production(self.tokens[initProd + '\''], [self.tokens[initProd], self.tokens['$']], 1)
        self.productions[initProduction] = initProduction
        countProd = 2
        for prName, prsL in temPrs.items():
            prs = prsL.split('|')
            for pr in prs:
                pr = [x.strip() for x in pr.split(' ') if x != '' or x != ' ']
                productionResult = []
                for p in pr:
                    if p == '':
                        continue
                    if p in self.tokens:
                        productionResult.append(self.tokens[p])
                    else:
                        raise Exception('Token not found in definition to production', prName, p)

                newProd = Production(self.tokens[prName], productionResult, countProd)

                if newProd in self.productions:
                    newProd = self.productions[newProd]
                else:
                    self.productions[newProd] = newProd
                    countProd += 1

                self.tokens[prName].addProduction(newProd)

        initLR0 = LRO_State(initProduction.closure(), 0)
        self.LR0States[initLR0] = initLR0
        countLR0 = 1
        toEval = [initLR0]
        while len(toEval) > 0:
            lr0 = toEval.pop(0)
            for symbol in self.tokens.values():
                newListState = lr0.passPoint(symbol)
                if len(newListState) == 0:
                    continue
                newLR0State = LRO_State(newListState, countLR0)
                if newLR0State in self.LR0States:
                    newLR0State = self.LR0States[newLR0State]
                else:
                    self.LR0States[newLR0State] = newLR0State
                    countLR0 += 1
                    toEval.append(newLR0State)

                lr0.addTransition(symbol, newLR0State)
        drawDiagramAndSave(initLR0, False)
        drawDiagramAndSave(initLR0, True)

    def calcs(self):
        for tk in self.tokens.values():
            tk.calcFirst()
        for pr in self.productions.values():
            pr.calcFollow()
        for tk in self.tokens.values():
            print(tk.value, '-> Follow:', {x.value for x in tk.follow})

        print('-------------------')

    def createSLRTable(self):
        slrTable = pd.DataFrame(columns=[x.value for x in self.tokens.values()], index=[x.number for x in self.LR0States.values()])
        toPrintTable = slrTable.copy()
        for pr in self.productions.values():
            print(pr.number,'. ',str(pr))
        for state in self.LR0States.values():
            for symbol, nextState in state.transitions.items():
                if symbol.isTerminal:
                    if symbol.value == '$':
                        slrTable.loc[state.number, symbol.value] = ('A', nextState.number)
                        toPrintTable.loc[state.number, symbol.value] = 'A'
                        continue
                    # Verificar si el espacio esta vacio
                    if pd.isna(slrTable.loc[state.number, symbol.value]):
                        slrTable.loc[state.number, symbol.value] = []
                        toPrintTable.loc[state.number, symbol.value] = ' '
                    slrTable.loc[state.number, symbol.value].append(('S', nextState.number))
                    toPrintTable.loc[state.number, symbol.value] += f'S{nextState.number} '
                else:
                    slrTable.loc[state.number, symbol.value] = ('G', nextState.number)
                    toPrintTable.loc[state.number, symbol.value] = f'G{nextState.number}'
            for pr in state.itemsPointNone:
                for symbol in pr.fromNonTerminal.follow:
                    if pd.isna(slrTable.loc[state.number, symbol.value]):
                        slrTable.loc[state.number, symbol.value] = []
                        toPrintTable.loc[state.number, symbol.value] = ' '
                    slrTable.loc[state.number, symbol.value].append( ('R', pr.fromNonTerminal.value, len(pr.toResult)))
                    toPrintTable.loc[state.number, symbol.value] += f'R{pr.number} {pr.fromNonTerminal.value}{len(pr.toResult)} '

        print(toPrintTable)
        print(tabulate.tabulate(toPrintTable, headers='keys', tablefmt='psql'))


if __name__ == '__main__':
    reader = YpReader('../examples/yalex.yalp')
    reader.analyzeContent()
    reader.calcs()
    reader.createSLRTable()
