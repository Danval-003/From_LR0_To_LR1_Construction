from Machines_gen_usage import import_module, simulator
from YaPar_reader.SLR_simulater import SLR_simulate
# Importo pickle
import pickle

class YxReader:
    def __init__(self, path):
        self.path = path
        self.data = ''
        self.variables = {}

    def read(self):
        with open(self.path, 'r') as file:
            self.data = file.read()

    def preProcess(self):
        YxParts = {
            'RCURLY': ['\}'],
            'LCURLY': ['\{'],
            'ASSIGMENT': ['let [a-zA-Z][a-zA-Z0-9]* *= *([^ \n\t]|\'[ \n\t]\')+'],
            'EXPRESSION': ['([^ \n\t]|\'[ \n\t]\')+'],
            'RULE': ['rule +[a-zA-Z][a-zA-Z0-9]* *='],
            'WHITESPACE': ['[ \n\t]+'],
            'COM': ['\(\*'],
            'ENDCOM': ['\*\)'],
            'OR': ['\|']
        }

        machineLector = import_module('machineLector.py', YxParts)
        result = simulator(machineLector, self.data)
        print(result)
        toEval = ' '.join([x[1] for x in result])
        print(result)
        print(toEval)

        # Se obtiene la tabla de SLR(Almacenado en un pandas) con pickle
        with open('./out/yalexSLR.pkl', 'rb') as file:
            slr_table = pickle.load(file)

        # Se simula el analizador SLR
        SLR_simulate(toEval, slr_table)


if __name__ == '__main__':
    reader = YxReader('examples/slr-1.yal')
    reader.read()
    reader.preProcess()
