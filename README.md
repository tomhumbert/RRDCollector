# RRDCollector

PRAW Reddit scraper with some useful functions for feature extraction.

scraper.py contains the main logic. It is preset to collect the contents of 'platformsV3.txt' and 'subredditsV1.txt'.
The Reddit authentication credentials need to be specified in 'creds.txt' first.

Smart wordlist for stopword removal from:
Lewis, D. D.; Yang, Y.; Rose, T.; and Li, F. RCV1: A New Benchmark Collection for Text Categorization Research. Journal of Machine Learning Research, 5:361-397, 2004. http://www.jmlr.org/papers/volume5/lewis04a/lewis04a.pdf. 

For now, tasks have to be defined manually before execution.
