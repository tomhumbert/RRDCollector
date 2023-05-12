from praw import Reddit
import time, os, csv, re, sys
from datetime import datetime
import pandas as pd
from nltk import ngrams
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer


class RScraper(Reddit):
    def __init__(self, cred_file):
        """Initialize praw with personal credentials"""
        creds = open(cred_file,'r').read().replace("\n", " ").split()
        super().__init__(client_id= creds[0], client_secret= creds[1], user_agent= creds[2])
        self.posts = pd.DataFrame(columns=['id', 'title', 'body', 'author', 'is_nsfw', 'n_comments', 'up_ratio', 'date', 'link', 'sub'])
        self.description = pd.DataFrame(columns=['sub','n_posts','n_comments'])

    def fetch_posts(self, sub, platform, fetchlim):
        """Fetch all posts resulting from a query on given platforms and given keywords.
        Takes parameters;  
        sub (either a single <string> name of a subreddit, a <list> of strings of subreddit names or a name of a text file containing subreddit names) and
        platform (single <string>, <list> of strings or a name of a file, containing names of platforms)
        Returns pandas dataframe of all results."""
        subreddits = False
        query = False

        if type(sub) == str:
            if sub in os.listdir(os.path.curdir):
                with open(sub, 'r') as s:
                    subreddits = s.readlines()
                    subreddits = [z.replace("\n", "") for z in subreddits]
            else:
                subreddits = [sub]
        elif type(sub) == list:
            subreddits = sub
        else:
            print("The input given for sub is not in the right format, please check the documentation of this function.")
            return False

        if type(platform) == str:
            if platform in os.listdir(os.path.curdir):
                with open(platform, 'r') as p:
                    platforms = p.readlines()
                    platforms = ['"'+b.replace("\n", "")+'"' for b in platforms]
                    query = ' OR '.join(platforms)
            elif platform == "" or platform == " ":
                query = "r/"
            else:
                query = '"'+platform+'"'
        elif type(platform) == list:
            platforms = ['"'+b+'"' for b in platform]
            query = ' OR '.join(platforms)
        else:
            print("The input given for platform is not in the right format, please check the documentation of this function.")
            return False

        for subreddit in subreddits:
            print(f"Now accessing {subreddit}")
            matched_posts = self.subreddit(subreddit).search(query, sort='new', limit=fetchlim)
            npost = 0
            for post in matched_posts:
                postid = post.id
                title = post.title
                body = post.selftext
                body = body.replace("\n"," <newline> ").replace(";", ":")
                body, doms, full_links = self.clean_links(body)
                author = post.author
                nsfw = post.over_18
                ncomm = post.num_comments
                uprat = post.upvote_ratio
                date = datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
                link = post.permalink
                self.posts.loc[len(self.posts)] = [postid, title, body, author, nsfw, ncomm, uprat, date, link, subreddit]
                npost += 1
            self.description.loc[len(self.description)] = [subreddit, npost, 0]
        return self.posts

    def clean_links(self, text):
        ntext = text
        # url regex
        linkRegex = r"([http|ftp|https]+:\/\/[\w_-]+(?:(?:\.(?P<dom>[\w_-]+)\.[\w_-]+)+)[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"
        # collect all links
        links = re.findall(linkRegex, ntext)
        # replace all reddit style markup links with only text
        ntext = re.sub(r"(\[(?P<txt>[\s]*)\]\([\s]*\))", "\g<txt>", ntext)
        # replace all remaining links with main part of address
        ntext = re.sub(linkRegex, "LinkTO\g<dom>", ntext)

        ####debugging
        #print(ntext)
        #occs = re.findall(r"(\[(?P<txt>[\s\w.,@?^=%&:\/~+#-]*)\]\([\s\w.,@?^=%&:\/~+#-]*\))", ntext)
        #if len(occs)>0:
        #    print("occ:")
        #    print(occs[0][1])
        #    print()
        ############
        linkdoms = [l[1] for l in links]
        fulllinks = [l[0] for l in links]
        linkdict = dict()
        for l in linkdoms:
            if l in linkdict.keys():
                linkdict[l] = linkdict[l]+1
            else:
                linkdict[l] = 1

        return ntext, linkdict, fulllinks

    def gen_corpus(self, sub = False, stringlist = False):
        corpus = ""
        links = list()
        doms = dict()
        
        if stringlist == True:
            corpus = []
            if sub == False:
                for row in self.posts.iterrows():
                    txt = ""
                    txt += row[1]['title'] + " "
                    txt += row[1]['body']
                    txt = txt.replace("<newline>", " ")
                    txt = (re.sub(' +', ' ',(txt.replace('\t',' ')))).strip()
                    #txt, ls = self.clean_links(txt)
                    corpus.append(txt)
                    if ls != []:
                        links.append(ls)
            else:
                for row in self.posts.loc[self.posts['sub'] == sub].iterrows():
                    txt = ""
                    txt += str(row[1]['title'])
                    txt += str(row[1]['body'])
                    txt = txt.replace("<newline>", " ")
                    txt = (re.sub(' +', ' ',(txt.replace('\t',' ')))).strip()
                    txt, ds, ls = self.clean_links(txt)
                    corpus.append(txt)
                    if ls != []:
                        links.append(ls)
                    for it in ds.keys():
                        if it in doms.keys() :
                            doms[it] = doms[it]+ds[it]
                        else:
                            doms[it] = ds[it]
        else:
            if sub == False:
                for row in self.posts.iterrows():
                    corpus += row[1]['title']
                    corpus += row[1]['body']
            else:
                for row in self.posts.loc[self.posts['sub'] == sub].iterrows():
                    corpus += str(row[1]['title'])
                    corpus += str(row[1]['body'])
            corpus = corpus.replace("<newline>", " ")
            corpus = (re.sub(' +', ' ',(corpus.replace('\t',' ')))).strip()
            # corpus, links = self.clean_links(corpus)
        return corpus, doms, links

    def nlp_prep(self, txt):
        # remove stopwords, new lines and other 
        tokens = word_tokenize(txt)
        stop_words = open('smart.txt','r').read().replace("\n", " ").split()
        clean_tokens = [word for word in tokens if not word in stop_words]
        # lemmatize
        lemmat = WordNetLemmatizer()
        clean_tokens = [lemmat.lemmatize(w) for w in clean_tokens]

        # stemmer (not always desirable)
        #stmmer = PorterStemmer()
        #clean_tokens = [stmmer.stem(w) for w in clean_tokens]

        ntext = (" ").join(clean_tokens)
        return ntext

    def freqNgrams(self, sub, lim = 3):
        freq_ngrams = []
        c_vec = CountVectorizer(ngram_range=(3,5))
        corpus, doms, links = self.gen_corpus(sub=sub, stringlist=True)
        corpus = [self.nlp_prep(c) for c in corpus]
        ngrams = c_vec.fit_transform(corpus)
        vocab = c_vec.vocabulary_
        count_values = ngrams.toarray().sum(axis=0)
        for ng_count, ng_text in sorted([(count_values[i],k) for k,i in vocab.items()], reverse=True):
            if ng_count >= lim:
                freq_ngrams.append((ng_text, ng_count))
        return freq_ngrams, doms, links

    def sub_mentions(self):
        mentioned_subs = pd.DataFrame(columns=["sub", "mentions"])
        subs = list(self.description['sub'])
        mentions = dict()
        
        for s in subs:
            text, d, links = self.gen_corpus(s)
            ment_list = [t for t in s.split() if t.startswith('r/')]
            ments = Counter(ment_list)
            mentioned_subs.loc[len(mentioned_subs)] = [s, dict(ments)]

        return mentioned_subs

    def summary(self):
        if not 'all' in list(self.description['sub']):
            total = self.description['n_posts'].sum()
            self.description.loc[len(self.description)] = ['all', total, 0]
        return self.description

    def safe_all_to_csvs(self):
        # Save pandas dataframes to file
        now = datetime.now()
        now = str(now)[:-7].replace(" ", "_").replace(":", "_")
        with open(f"posts_{now}.csv", "w", encoding="utf-8") as f:
            self.posts.to_csv(f, sep=";")
        return None

    def load(self, file):
        self.posts = pd.read_csv(file, sep=';', index_col='Unnamed: 0')
        counts = self.posts.groupby('sub')['sub'].count()
        nms = list(counts.index)
        n = list(counts)
        self.description['sub'] = nms
        self.description['n_posts'] = n
        self.description['n_comments'] = 0

    def fetch_comments_of_post(self, posts):
        """post.comments.replace_more(limit=None)
       	    for top_level_comment in post.comments:
                text = top_level_comment.body
                print(f"Comment: {text}")
            print()"""
        return None


def main():
    while True:
        com = input("Enter command, or type h for help")
        if com == 'h':
            print("h - help with commands")
            print("subs - list of subs")
            print("subm <sub> - mentions of subs, can specify only single sub in <>, otherwise list for all subs")
            print("links <sub> - links found in subs, can specify only single sub in <>, otherwise list for all subs")
            print("ngram <sub> - links found in subs, can specify only single sub in <>, otherwise list for all subs")
            print("exit - exit the program")

        if com == 'exit' or com == 'x' or com == 'quit':
            break
        
        if com == 'subs':
            print(12*'-')
            print(scraper.summary())
            print(12*'-', end="\n")

        if com == 'subm':
            print("Subreddits mentionned in given list of subs.")
            print()


if __name__ == "__main__":
    # Input files
    subs = "subreddits.txt"
    plats = "platforms.txt"
    pd.set_option('display.max_colwidth', None)

    scraper = RScraper("reddit-credentials.txt")
    data = scraper.load("posts_2023-05-01_15_28_31.csv")
    #data = scraper.fetch_posts(subs,plats, 1000)
    #data = scraper.fetch_posts(subs,"", 1000)
    #scraper.safe_all_to_csvs()

    # INSTEAD OF PRINTING OUT, NOW THE PROGRAM SHOULD JUST BUILD THE APPROPRIATE DATAFRAME !!!
    # THE LINKS SHOULD BE CLEANED FROM TEXT BEFORE IT IS STORED IN DF
    # THUS THE GEN_CORPUS FUNC NEEDS TO BE CHANGED
    

    
    mentions = scraper.sub_mentions()
    for row in mentions.iterrows():
        sub = row[1]['sub']
        if sub != 'all':
            print(sub)
            print(row[1]['mentions'])
            ngs, doms, links = scraper.freqNgrams(sub)
            print(ngs)
            print(links)
            print(doms)
            print()




