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
optparser.add_option("-k", "--translations-per-phrase", dest="k", default=10, type="int", help="Limit on number of translations to consider per phrase (default=1)")


opts = optparser.parse_args()[0]


"""
#grammar rules format
dict rules={rules in ur: [rule_prop1, rule_prop2]}
class rule_hyp:
	self.en = [word1, word2, ..., [X,1], ..wordn, [X,2]]
	self.pe_given_f = p(e|f) 
	self.pf_given_e = p(f|e) 

class chart_entry:
	self.prob
	self.en
"""
class rule_hyp:
	def __init__(self, en=[], pe_given_f=1, pf_given_e=1, align=[]):
		self.en=en
		self.pe_given_f=pe_given_f
		self.pf_given_e=pf_given_e
		self.align=align
		self.prob = self.pe_given_f+ self.pf_given_e

class chart_entry:
	def __init__(self, en=[], prob=1):
		self.prob=prob
		self.en=en
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
		lm_logprob -= word_logprob
	return lm_logprob
  
rules=defaultdict(list)
with open(opts.gm) as fin:
    for line in fin:
        parts = line.strip().split('|||')
        ori = parts[1].strip().split()
        hypo = parts[2].strip().split()
        pe_given_f=float(parts[3].strip().split()[0])
        pf_given_e=float(parts[3].strip().split()[1])
        align = parts[-1].strip().split()

        rules[tuple(ori)].append(rule_hyp(en=hypo, pe_given_f=pe_given_f, pf_given_e=pf_given_e, align=align))


rules[("'")].append(rule_hyp(en=[["'"]], pe_given_f=0, pf_given_e=0, align=[]))
rules[(".")].append(rule_hyp(en=[["."]], pe_given_f=0, pf_given_e=0, align=[]))
with open(opts.input) as fin:
	for line in fin:
		chart=dict()
		oris = line.strip().split()
		for span in range(1, len(oris)+1):
			for start in range(len(oris) - span +1):
				end = start + span;
				# the situation with only [X,1]
				if rules.has_key(tuple(oris[start:end])):
					min_rulehyp = min(rules[tuple(oris[start:end])], key=lambda x: x.prob)
					chart[(start,end)]=chart_entry(en=min_rulehyp.en, prob=(min_rulehyp.prob+lmscore(min_rulehyp.en)))
					#continue
				if span>1:
					for i1 in range(start, end):
						for j1 in range(i1+1, end+1):
							if chart.has_key((i1, j1)):
								seq = tuple(oris[start:i1]+['[X,1]']+oris[j1:end])
								if rules.has_key(seq):
									#print (' ').join(seq)
									for rulehyp in rules[seq]:
										en = rulehyp.en[:rulehyp.en.index('[X,1]')] + chart[(i1, j1)].en + rulehyp.en[rulehyp.en.index('[X,1]')+1:]
										en_lmscore = lmscore(en);
										prob = rulehyp.prob + chart[(i1,j1)].prob + en_lmscore
										if chart.has_key((start,end)):
											if chart[(start,end)].prob > prob:
												chart[(start,end)].prob = prob
												chart[(start,end)].en = en
										else:
											chart[(start,end)]=chart_entry(en=en, prob=prob)
				# the situation with [X,1] and [X,2]
				if span>2:
					for i1 in range(start, end):
						for j1 in range(i1+1, end):
							for i2 in range(j1, end):
								for j2 in range(i2+1, end+1):
									if chart.has_key((i1, j1)) and chart.has_key((i2, j2)):
										seq = tuple(oris[start:i1]+['[X,1]']+oris[j1:i2]+['[X,2]']+oris[j2:end])
										if rules.has_key(seq):
											#print (' ').join(seq)
											for rulehyp in rules[seq]:
												index1 = rulehyp.en.index('[X,1]')
												index2 = rulehyp.en.index('[X,2]')
												en = []
												if index1 < index2:
													en = rulehyp.en[:index1] + chart[(i1, j1)].en + rulehyp.en[index1+1:index2] + chart[(i2, j2)].en + rulehyp.en[index2+1:]
												else:
													en = rulehyp.en[:index2] + chart[(i2, j2)].en + rulehyp.en[index2+1:index1] + chart[(i1, j1)].en + rulehyp.en[index1+1:]
												en_lmscore=lmscore(en)
												prob=rulehyp.prob + chart[(i1,j1)].prob + chart[(i2, j2)].prob + en_lmscore
												if chart.has_key((start, end)):
													if chart[(start,end)].prob > prob:
					 									chart[(start,end)].prob = prob
					 									chart[(start,end)].en = en
												else:
													chart[(start,end)]=chart_entry(en=en, prob=prob)
											
										"""
										seq = tuple(oris[start:i1]+['[X,2]']+oris[j1:i2]+['[X,1]']+oris[j2:])
										if rules.has_key(seq):
											print (' ').join(seq)
											min_rulehyp = min(rules[seq], key=lambda x: x.pe_given_f)
											print min_rulehyp.en
											if chart.has_key((start, end)):
												if chart[(start,end)].prob> min_rulehyp.pe_given_f + chart[(i1,j1)].prob + chart[(i2, j2)].prob:
				 									chart[(start,end)].prob = min_rulehyp.pe_given_f + chart[(i1,j1)].prob + chart[(i2, j2)].prob
													index1 = min_rulehyp.en.index('[X,2]')
													index2 = min_rulehyp.en.index('[X,1]')
													chart[(start,end)].en = min_rulehyp.en[:index1] + chart[(i1, j1)].en + min_rulehyp.en[index1+1:index2] + chart[(i2, j2)].en + min_rulehyp.en[index2+1:]
											else:
												prob = min_rulehyp.pe_given_f + \
														chart[(i1,j1)].prob + chart[(i2, j2)].prob
												index1 = min_rulehyp.en.index('[X,2]')
												index2 = min_rulehyp.en.index('[X,1]')
												en = min_rulehyp.en[:index1] + \
														chart[(i1, j1)].en + min_rulehyp.en[index1+1:index2] + \
														chart[(i1, j1)].en + min_rulehyp.en[index2+1:]
												chart[(start, end)] = chart_entry(prob=prob, en=en)
										"""
				if span==1: #span==1
					if not rules.has_key(tuple(oris[start:end])):
						chart[(start,end)]=chart_entry(en=oris[start:end], prob=20)
				#if not chart.has_key((start, end)):
				for i in range(start+1, end):
						if chart.has_key((start, i)) and chart.has_key((i, end)):
							en = chart[(start, i)].en + chart[(i, end)].en
							en_lmscore = lmscore(en)
							prob = chart[(start, i)].prob + chart[(i, end)].prob + en_lmscore #as penalty
							if not chart.has_key((start, end)):
								chart[(start, end)] = chart_entry(en=en, prob=prob)
							elif chart[(start, end)].prob > prob:
								chart[(start, end)] = chart_entry(en=en, prob=prob)
				#print start, end, chart[(start, end)].prob
				#print (' ').join(chart[(start, end)].en)			
		print (' ').join(chart[(0, len(oris))].en)
		#_=raw_input("press any key to continue")
		

