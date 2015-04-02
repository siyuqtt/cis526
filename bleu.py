import math
from collections import Counter

# Collect BLEU-relevant statistics from four reference
# Return vaue is a generator yielding:
# (c, r, numerator1, denominator1, ..., numerator4, denominator4)
# Summing the columns across calls to this function on an entire corpus will
# produce a vector of statistics that can be used to compute BLEU

def bleu_stats(hypothesis, reference):
	yield len(hypothesis)
	closestgap = 500
	efflenref = 0
	for i in reference:
		if abs(len(i) - len(hypothesis)) < closestgap:
			closestgap = abs(len(i) - len(hypothesis))
			efflenref = len(i)
	yield efflenref
	for n in xrange(1,5):
		s_ngrams = Counter([tuple(hypothesis[i:i+n]) for i in xrange(len(hypothesis)+1-n)])
		r_ngramlist = []
		for refitem in reference:
			r_ngramlist.append(Counter([tuple(refitem[i:i+n]) for i in xrange(len(refitem)+1-n)]))
		r_ngrams = r_ngramlist[0]
		for j in xrange(1, len(r_ngramlist)):
			r_ngrams = r_ngrams|r_ngramlist[j]
		yield max([sum((s_ngrams & r_ngrams).values()), 0])
		yield max([len(hypothesis)+1-n, 0])


#Compute BLEU
def bleu(stats):
	if len(filter(lambda x: x==0, stats)) > 0:
		# exist one or more item in stats that is equal to 0
		# in case of devide by 0
		return 0
	(c, r) = stats[:2]
	# brevity penalty
	log_bleu_prec = sum([math.log(float(x)/y) for x,y in zip(stats[2::2],stats[3::2])]) / 4.
	return math.exp(min([0, 1-float(r)/c]) + log_bleu_prec)
