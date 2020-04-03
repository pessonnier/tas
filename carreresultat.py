import pickle
import carre

with open('listecarre.dmp', 'rb') as f:
    solution = pickle.load(f)

print(len(solution))
carre.aff(solution[0])