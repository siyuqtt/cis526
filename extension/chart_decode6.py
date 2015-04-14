#!/usr/bin/env python
import optparse
import sys
from collections import defaultdict, namedtuple
from math import exp, log, log10

optparser = optparse.OptionParser()
optparser.add_option("-i", "--input", dest="input", default="../data/devtest.ur", help="File containing sentences to translate (default=data/devtest.ur)")
optparser.add_option("-g", "--grammar-model", dest="gm", default="../data/grammar", help="File containing grammar (default=data/grammar)")
optparser.add_option("-l", "--language-model", dest="lm", default="../data/lm", help="File containing ARPA-format language model (default=data/lm)")
optparser.add_option("-n", "--num_sentences", dest="num_sents", default=sys.maxint, type="int", help="Number of sentences to decode (default=no limit)")
optparser.add_option("-k", "--translations-per-phrase", dest="k", default=3, type="int", help="Limit on number of translations to consider per phrase (default=1)")

opts = optparser.parse_args()[0]


#language model
ngram_stats = namedtuple("ngram_stats", "logprob, backoff")

class LM:
	def __init__(self, filename):
		sys.stderr.write("Reading language model from %s...\n" % (filename,))
		self.table = {}
		for line in open(filename):
			entry = line.strip().split("\t")
			if len(entry) > 1 and entry[0] != "ngram":
				(logprob, ngram, backoff) = (float(entry[0]), tuple(entry[1].split()), float(entry[2] if len(entry)==3 else 0.0))
				self.table[ngram] = ngram_stats(logprob, backoff)
	def begin(self):
		return ("<s>",)
	def score(self, state, word):
		ngram = state + (word,)
		score = 0.0
		while len(ngram)> 0:
			if ngram in self.table:
				return (ngram[-2:], score + self.table[ngram].logprob)
			else: #backoff
				score += self.table[ngram[:-1]].backoff if len(ngram) > 1 else 0.0 
				ngram = ngram[1:]
		return ((), score + self.table[("<unk>",)].logprob)    
	def end(self, state):
		return self.score(state, "</s>")[1]

lm = LM(opts.lm)

def lmscore(en):
	lm_state = lm.begin()
	lm_logprob = 0.0
	for word in tuple(en) + ("</s>",):
		(lm_state, word_logprob) = lm.score(lm_state, word)
		lm_logprob -= word_logprob #since the logprob in the lm file are negative. we need to convert it into positive
	return lm_logprob

def partlmscore(en):
	if len(en) > 1:
		lm_state = lm.begin()
		lm_logprob = 0.0
		for word in tuple(en):
			(lm_state, word_logprob) = lm.score(lm_state, word)
			lm_logprob -= word_logprob 
		return lm_logprob
	else:
		return 0

def connectlmscore(en1, en2):
	# compute the conjunction part lmscore of two phrases
	lm_state = tuple(en1[-2:])
	lm_logprob = 0.0
	for word in tuple(en2[:2]):
		(lm_state, word_logprob) = lm.score(lm_state, word)
		lm_logprob -= word_logprob
	return lm_logprob	
		
# grammar rule read in
class rule_hyp:
	def __init__(self, en=[], weight = [1,1,1,1,0,0], pe_given_f=1, pf_given_e=1, pe_given_f_lex = 1, pf_given_e_lex = 1, rarity=0, phrase_penalty = 0):
		self.en=en
		self.pe_given_f=pe_given_f
		self.pf_given_e=pf_given_e
		self.pe_given_f_lex = pe_given_f_lex
		self.pf_given_e_lex = pf_given_e_lex
		self.rarity = rarity
		self.phrase_penalty = phrase_penalty
		w = weight
		self.prob = w[0]*self.pe_given_f + w[1]*self.pf_given_e + w[2]*self.pe_given_f_lex + w[3]*self.pf_given_e_lex + w[4]*self.rarity + w[5]*self.phrase_penalty

rules=defaultdict(list)
weight = [0.12817156400888038, 0.3544745566666286, 0.3391146050127749, 0.24257143336186784, 0.402106143732073, -0.1452664461926249]
with open(opts.gm) as fin:
	for line in fin:
		parts = line.strip().split('|||')
		ori = parts[1].strip().split()
		hypo = parts[2].strip().split()
		features = parts[3].strip().split()
		pe_given_f=float(features[0])
		pf_given_e=float(features[1])
		pe_given_f_lex=float(features[2])
		pf_given_e_lex=float(features[3])
		rarity=float(features[4])
		phrase_penalty=float(features[5])
		#align = parts[-1].strip().split()

		rules[tuple(ori)].append(rule_hyp(en=hypo,weight = weight, pe_given_f=pe_given_f, pf_given_e=pf_given_e, \
					pe_given_f_lex=pe_given_f_lex, pf_given_e_lex=pf_given_e_lex, \
					rarity=rarity, phrase_penalty=phrase_penalty))

rules[("'")].append(rule_hyp(en=[["'"]], pe_given_f=0, pf_given_e=0, pe_given_f_lex = 0, pf_given_e_lex = 0))
rules[(".")].append(rule_hyp(en=[["."]], pe_given_f=0, pf_given_e=0, pe_given_f_lex = 0, pf_given_e_lex = 0))

#decode chart entry
class chart_entry:
	def __init__(self, en=[], tmprob=1, lmprob = 1):
		self.tmprob=tmprob
		self.lmprob=lmprob
		self.prob=tmprob+lmprob
		self.en=en

sys.stderr.write("start decoding")
#start decoding
for line in open(opts.input).readlines()[:opts.num_sents]:
	chart=defaultdict(list)
	oris = line.strip().split()
	for span in range(1, len(oris)+1):
		for start in range(len(oris) - span +1):
			end = start + span;
			if rules.has_key(tuple(oris[start:end])):
				for rulehyp in rules[tuple(oris[start:end])]:
					en = rulehyp.en
					en_lmscore = 0
					if start == 0 and end == len(oris):
						en_lmscore = lmscore(en)
					else:
						en_lmscore = partlmscore(en)
					chart[(start,end)].append(chart_entry(en=en, tmprob=rulehyp.prob, lmprob=en_lmscore))
				chart[(start,end)] = sorted(chart[(start,end)])[:opts.k]
			# the situation with [X,1]
			if span>1:
				for i1 in range(start, end):
					for j1 in range(i1+1, end+1):
						if chart.has_key((i1, j1)):
							seq = tuple(oris[start:i1]+['[X,1]']+oris[j1:end])
							if rules.has_key(seq):
								for rulehyp in rules[seq]:
									for charthyp in chart[(i1, j1)]:
										en = rulehyp.en[:rulehyp.en.index('[X,1]')] + charthyp.en + rulehyp.en[rulehyp.en.index('[X,1]')+1:]
										en_lmscore = 0
										if start == 0 and end == len(oris):
											en_lmscore = lmscore(en)
										else:
											en_lmscore = partlmscore(en)
										tmprob = rulehyp.prob + charthyp.tmprob
										if chart.has_key((start,end)):
											if len(chart[(start,end)]) >= opts.k and chart[(start,end)][-1].prob > tmprob + en_lmscore:
												del chart[(start,end)][-1]
											if len(chart[(start,end)]) < opts.k:
												if chart[(start,end)][-1].prob <= tmprob + en_lmscore:
													chart[(start, end)].append(chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
												else:
													for (ii, _) in enumerate(chart[(start,end)]):
														if _.prob > tmprob + en_lmscore:
															chart[(start,end)].insert(ii, chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
															break
										else:
											chart[(start,end)].append(chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
			# the situation with [X,1] and [X,2]
			if span>2:
				for i1 in range(start, end):
					for j1 in range(i1+1, end):
						for i2 in range(j1, end):
							for j2 in range(i2+1, end+1):
								if chart.has_key((i1, j1)) and chart.has_key((i2, j2)):
									seq = tuple(oris[start:i1]+['[X,1]']+oris[j1:i2]+['[X,2]']+oris[j2:end])
									if rules.has_key(seq):
										for rulehyp in rules[seq]:
											index1 = rulehyp.en.index('[X,1]')
											index2 = rulehyp.en.index('[X,2]')
											for chart1hyp in chart[(i1,j1)]:
												for chart2hyp in chart[(i2, j2)]:
													if index1 < index2:
														en = rulehyp.en[:index1] + chart1hyp.en + rulehyp.en[index1+1:index2] + chart2hyp.en + rulehyp.en[index2+1:]
													else:
														en = rulehyp.en[:index2] + chart2hyp.en + rulehyp.en[index2+1:index1] + chart1hyp.en + rulehyp.en[index1+1:]
													en_lmscore = 0
													if start == 0 and end == len(oris):
														en_lmscore = lmscore(en)
													else:
														en_lmscore = partlmscore(en)
													tmprob=rulehyp.prob + chart1hyp.tmprob + chart2hyp.tmprob
													if chart.has_key((start, end)):
														if len(chart[(start,end)]) >= opts.k and chart[(start,end)][-1].prob > tmprob + en_lmscore:
						 									del chart[(start,end)][-1]
														if len(chart[(start,end)]) < opts.k:
															if chart[(start,end)][-1].prob <= tmprob + en_lmscore:
																chart[(start, end)].append(chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
															else:
																for (ii, _) in enumerate(chart[(start,end)]):
																	if _.prob > tmprob + en_lmscore:
																		chart[(start,end)].insert(ii, chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
																		break
													else:
														chart[(start,end)].append(chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
			if span==1: #span==1
				if not rules.has_key(tuple(oris[start:end])):
					chart[(start,end)].append(chart_entry(en=oris[start:end], tmprob=20, lmprob=0))
			#if not chart.has_key((start, end)):
			for i in range(start+1, end):
					if chart.has_key((start, i)) and chart.has_key((i, end)):
						for chart1hyp in chart[(start, i)]:
							for chart2hyp in chart[(i, end)]:
								en = chart1hyp.en + chart2hyp.en
								if start == 0 and end == len(oris):
									en_lmscore = lmscore(en)
								else:
									en_lmscore = partlmscore(en)
								tmprob = chart1hyp.tmprob + chart2hyp.tmprob + 3 #as penalty
								if not chart.has_key((start, end)):
									chart[(start, end)].append(chart_entry(en=en, tmprob=tmprob, lmprob=en_lmscore))
								else:
								 	if len(chart[(start,end)]) >= opts.k and chart[(start, end)][-1].prob > tmprob + en_lmscore:
										del chart[(start, end)][-1]
									if len(chart[(start,end)]) < opts.k:
										if chart[(start,end)][-1].prob <= tmprob + en_lmscore:
											chart[(start, end)].append(chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
										else:
											for (ii, _) in enumerate(chart[(start,end)]):
												if _.prob > tmprob + en_lmscore:
													chart[(start,end)].insert(ii, chart_entry(en=en, tmprob = tmprob, lmprob = en_lmscore))
													break
			#print start, end, chart[(start, end)].prob
			#print (' ').join(chart[(start, end)].en)			
	print (' ').join(chart[(0, len(oris))][0].en)
	sys.stderr.write(".")
		#_=raw_input("press any key to continue")
		

