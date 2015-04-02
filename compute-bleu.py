#!/usr/bin/env python

import optparse
import sys
import bleu

optparser = optparse.OptionParser()
optparser.add_option("-r", "--reference", dest="reference", default="data/devtest.en", help="Target language reference sentences")
optparser.add_option("-n", "--ref_num", dest="ref_num", default=3, type="int", help="number of reference")

(opts, _) = optparser.parse_args()

#single reference
if opts.ref_num <= 0:
	ref = [[line.strip().split()] for line in open(opts.reference)]	

#multiple reference
else:
	ref = [[line.strip().split()] for line in open(opts.reference + ".0")]
	for i in range(1, opts.ref_num):
		for j, line in enumerate(open(opts.reference + "." + str(i))):
			ref[j].append(line.strip().split())

hyp = [line.strip().split() for line in sys.stdin]

stats = [0 for i in xrange(10)]
for (r, h) in zip(ref, hyp):
	stats = [sum(scores) for scores in zip(stats, bleu.bleu_stats(h, r))]

print stats
print bleu.bleu(stats)
