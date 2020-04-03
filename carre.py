import itertools
x=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]

def verif(carre):
    for i in range(4):
        # if (carre[i * 4] +
        # carre[i * 4 +1] +
        # carre[i * 4 +2] +
        # carre[i * 4 +3]) != 34:
        #     return False
        if (carre[i] +
        carre[i +4] +
        carre[i +8] +
        carre[i +12]) != 34:
            return False
    if (carre[0] +
        carre[5] +
        carre[10] +
        carre[15]) != 34:
        return False
    if (carre[3] +
        carre[6] +
        carre[9] +
        carre[12]) != 34:
        return False
    return True

def aff(l):
    print('_'*(4*3+1))
    for ligne in range(4):
        p = '|'
        for col in range(4):
            p=p+f"{l[ligne*4+col]:2}|"
        print(p)
    print('-'*(4*3+1))

possible = []
for l in itertools.permutations(x,4):
    if (l[0]+l[1]+l[2]+l[3]) == 34:
        possible.append(l)
nbpossible = len(possible)

def pasdouble(l, p):
    return (l[0] not in p) and (l[1] not in p) and (l[2] not in p) and (l[3] not in p)

def touslescarre(trace = False):
    solution = []
    for i, l1 in enumerate(possible):
        if trace:
            print (f'{i} / {nbpossible}')
        #print (f'{i} / {nbpossible} - {j} / {nbp1}')
        poss1 = [p for p in possible if pasdouble(l1, p)]
        nbp1 = len(poss1)
        for l2 in poss1:
            poss2 = [p for p in poss1 if pasdouble(l2, p)]
            for l3 in poss2:
                poss3 = [p for p in poss2 if pasdouble(l3, p)]
                for l4 in poss3:
                    l = []
                    l.extend(l1)
                    l.extend(l2)
                    l.extend(l3)
                    l.extend(l4)
                    if verif(l):
                        if trace:
                            aff(l)
                        solution.append(l)
    return solution

if __name__ == "__main__":
    solution = touslescarre(trace = True)
    for l in solution:
        aff(l)

    print(len(solution))

    import pickle
    with open('listecarre.dmp', 'wb') as f:
        pickle.dump(solution,f)

    aff(solution[0])