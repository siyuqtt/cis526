
# Implement the CKY algorithm for decoding SCFGs


The task is to translate from Urdu to English using existing grammar rules and language models. 


##Getting Started

To begin, download the starter kit. You may either choose to develop locally or on Penn servers. For the latter, we recommend using the Biglab machines, whose memory and runtime restrictions are much less stringent than those on Eniac. The Biglab servers can be accessed directly using the command ssh PENNKEY@biglab.seas.upenn.edu, or from Eniac using the command ssh biglab.

You can run the default system using the command:

```python
./default > 1-best.en
```

The default system uses a very simple method to generate a translation based on word-to-word translation and ignores complex grammars and language models. 
	
	word_e = argmax_P(word_e|word_f) word_e

To test the result, use the command:

```python
	./grade < 1-best.en
```
The program will evaluate the translation using BLEU score, and print the BLEU stats features as well as the BLEU score.
the BLEU score is counted using the formula:
	
	score = exp(min(0,(1 - refcount/hypcount))+ln(grammatch_1...grammatch_4/gramcount_1..gramcount_4)

Your task is to improve the score as much as possible.

_The './data' includes the data you may use:_

1. grammar

  * The format of grammar is as follows:
  
      [S] ||| [X,1] ||| [X,1] ||| features ||| alignment

      for example
  
      [X] ||| " " جالبین " بھی ||| " " jalibeen " " also ||| 8.93287 6.92926 1 1.00000 0 0 ||| 0-0 1-1 2-2 4-5

  * The features are:
  
      p(e|f) p(f|e) Lex(e|f) Lex(f|e) rarity phrase-penalty

  * Alignment is:
  
      source_word-target_word

2. lm

  lm contains 1-grams, 2-grams and 3-grams language model. 

3. train data, tune data

  tune data are for students to tune the CKY model. 
  You may want to train your grammar model by yourself. Then you can use the train data to extract the SCFG rules.
  test data includes the test sentences you need to translate.

_The './test-data' including the sentence to be translated:_


