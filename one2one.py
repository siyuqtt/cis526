from _collections import defaultdict
from itertools import islice
dic = defaultdict();
puncs= ['\'', ',']
with open('./data/grammar') as fin:
    for line in fin:
        parts = line.strip().split('|||')
        ori = parts[1].strip().split()
        hypo = parts[2].strip().split()
        algin = parts[-1].strip().split()
        for al in algin:
            match = al.strip().split('-')
            tmp1 = dic.get(ori[int(match[0])],{})
            tmp2 = tmp1.get(hypo[int(match[1])],0)
            tmp2 += 1
            tmp1[hypo[int(match[1])]] = tmp2
            dic[ori[int(match[0])]] = tmp1

topdic = defaultdict()
for k,v in dic.items():
    sortv = sorted(v.items(), key = lambda x : -x[1] )
    topdic[k] = sortv.pop(0)[0]
   # print k, topdic[k]

with open('./data/devtest.ur') as fin:
    for line in fin:
        oris = line.strip().split()
        trans = ""
        for o in oris:
            if o in puncs:
                trans += o
                trans += " "
            else:
                trans += topdic.get(o, "")+" "
        print trans

        
    
