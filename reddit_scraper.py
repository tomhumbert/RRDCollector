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
        self.posts = pd.DataFrame(columns=['id', 'title', 'body', 'author', 'is_nsfw', 'n_comments', 'up_ratio', 'date', 'link', 'subreddit', 'contained_links'])
        self.description = pd.DataFrame(columns=['subreddit','n_posts','n_comments','domain_counts'])

    def fetch_posts(self, sub, platform, fetchlim):
        """Fetch all posts resulting from a query on given platforms and given keywords.
        Takes parameters;  
        sub (either a single <string> name of a subreddit, a <list> of strings of subreddit names or a name of a text file containing subreddit names) and
        platform (single <string>, <list> of strings or a name of a file, containing names of platforms)
        Returns pandas dataframe of all results."""
        subreddits = False
        query = False

        # param of subreddits is a string
        if type(sub) == str:
            # The string is a path
            if sub in os.listdir(os.path.curdir):
                with open(sub, 'r') as s:
                    subreddits = s.readlines()
                    subreddits = [z.replace("\n", "") for z in subreddits]
            # The string is a subreddit name
            else:
                subreddits = [sub]
        # The param is a list of strings
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
                query = platform
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
            domain_count = dict()
            tdomain, tlinks, bdomain, tlinks = False,False,False,False
            for post in matched_posts:
                postid = post.id
                title = post.title
                title, tdomain, tlinks = self.clean_links(title)
                body = post.selftext
                body = body.replace("\n"," <newline> ").replace(";", ":")
                body, bdomain, blinks = self.clean_links(body)
                author = post.author
                nsfw = post.over_18
                ncomm = post.num_comments
                uprat = post.upvote_ratio
                date = datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
                link = post.permalink
                contained_links = tlinks + blinks
                npost += 1
                domain_counts = self.dict_add(domain_count,tdomain,bdomain)
                self.posts.loc[len(self.posts)] = [postid, title, body, author, nsfw, ncomm, uprat, date, link, subreddit, contained_links]
            
            self.description.loc[len(self.description)] = [subreddit, npost, 0, domain_count]
        return self.posts

    def dict_add(self,dc,dict1,dict2):
        dc=dc
        for i,c in dict1.items():
            if i in dc.keys():
                dc[i] = dc[i]+c
            else:
                dc[i] = c
        for i,c in dict2.items():
            if i in dc.keys():
                dc[i] = dc[i]+c
            else:
                dc[i] = c
        return dc

    def rm_dups(self):
        """Removes duplicate posts"""
        return None

    def clean_links(self, text):
        """Removes links from text, returns clean text and list of removed links"""
        ntext = text
        # url regex
        linkRegex = r"([http:\/\/|ftp:\/\/|https:\/\/]*[www\.]*(?P<dom>[\w_-]+)\.[\w_-]{2,3}[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"
        # collect all links
        links = re.findall(linkRegex, ntext)
        # replace all reddit style markup links with only text
        ntext = re.sub(r"(\[(?P<txt>[\s]*[\S]*)\]\([\s]*[\S]*\))", "\g<txt>", ntext)
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
        if stringlist == True:
            corpus = []
            if sub == False:
                for row in self.posts.iterrows():
                    txt = ""
                    txt += row[1]['title'] + " "
                    txt += row[1]['body']+ " "
                    txt = txt.replace("<newline>", " ")
                    txt = (re.sub(' +', ' ',(txt.replace('\t',' ')))).strip()
                    corpus.append(txt)
            else:
                for row in self.posts.loc[self.posts['subreddit'] == sub].iterrows():
                    txt = ""
                    txt += str(row[1]['title'])+ " "
                    txt += str(row[1]['body'])+ " "
                    txt = txt.replace("<newline>", " ")
                    txt = (re.sub(' +', ' ',(txt.replace('\t',' ')))).strip()
                    corpus.append(txt)
        else:
            if sub == False:
                for row in self.posts.iterrows():
                    corpus += row[1]['title']+ " "
                    corpus += row[1]['body']+ " "
            else:
                for row in self.posts.loc[self.posts['subreddit'] == sub].iterrows():
                    corpus += str(row[1]['title'])+ " "
                    corpus += str(row[1]['body'])+ " "
            corpus = corpus.replace("<newline>", " ")
            corpus = (re.sub(' +', ' ',(corpus.replace('\t',' ')))).strip()
        return corpus

    def nlp_prep(self, txt):
        # remove stopwords, new lines and punctuation
        stop_words = open('smart.txt','r').read().replace("\n", " ")
        punct  = r"[.?!,;:\-\\\(\)_']"
        text = re.sub(punct," ", txt)
        tokens = word_tokenize(text)
        clean_tokens = [word for word in tokens if not word in stop_words.split()]
        # lemmatize
        lemmat = WordNetLemmatizer()
        clean_tokens = [lemmat.lemmatize(w) for w in clean_tokens]

        # stemmer (not always desirable)
        #stmmer = PorterStemmer()
        #clean_tokens = [stmmer.stem(w) for w in clean_tokens]

        ntext = (" ").join(clean_tokens)
        return ntext

    def freqNgrams(self, sub, lim = 7):
        freq_ngrams = []
        c_vec = CountVectorizer(ngram_range=(3,5))
        corpus = self.gen_corpus(sub=sub, stringlist=True)
        corpus = [self.nlp_prep(c) for c in corpus]
        if len(corpus) > 0:
            ngrams = c_vec.fit_transform(corpus)
            vocab = c_vec.vocabulary_
            count_values = ngrams.toarray().sum(axis=0)
            for ng_count, ng_text in sorted([(count_values[i],k) for k,i in vocab.items()], reverse=True):
                if ng_count >= lim:
                    freq_ngrams.append((ng_text, ng_count))
        return dict(freq_ngrams)

    def sub_mentions(self, sub='all'):
        mentioned_subs = False
        if sub == 'all':
            mentioned_subs = pd.DataFrame(columns=["sub", "mentions"])
            subs = list(self.description['subreddit'])
            for s in subs:
                text = self.gen_corpus(s)
                ment_list = [t for t in s.split() if t.startswith('r/')]
                ments = Counter(ment_list)
                mentioned_subs.loc[len(mentioned_subs)] = [s, dict(ments)]
        else:
            text = self.nlp_prep(self.gen_corpus(sub)).split()
            ment_list = [t for t in text if t.startswith('r/')]
            ments = Counter(ment_list)
            mentioned_subs = dict(ments)

        return mentioned_subs

    def summary(self):
        if not 'all' in list(self.description['subreddit']):
            total = self.description['n_posts'].sum()
            self.description.loc[len(self.description)] = ['all', total, 0]
        return self.description

    def safe_all_to_csvs(self):
        # Save pandas dataframes to file
        now = datetime.now()
        now = str(now)[:-7].replace(" ", "_").replace(":", "_")
        fname = f"posts_{now}.csv"
        dname = f"subreddits_{now}.csv"
        self.posts.to_csv(fname, sep=";",encoding='utf-8-sig')
        self.description.to_csv(dname, sep=";",encoding='utf-8-sig')
        return None

    def load(self, subs, posts):
        # Load previously collected posts
        self.description = pd.read_csv(subs, delimiter=';', encoding='utf-8-sig', index_col='Unnamed: 0')
        self.posts = pd.read_csv(posts, sep=';', index_col='Unnamed: 0')

        if not 'n_posts' in list(self.description.columns):
            counted = self.posts.groupby('subreddit')['subreddit'].count()
            subredds = list(counted.index)
            counts = list(counted)
            counted = pd.DataFrame({'subreddit':subredds, 'n_posts':counts}, index=None)
            self.description = pd.merge(self.description,counted,how='left',on='subreddit').fillna(0)
            self.description['n_comments'] = 0
            self.description.to_csv(subs, sep=';', encoding='utf-8-sig')

        if not 'ngrams' in list(self.description.columns) and not 'sub_mention' in list(self.description.columns):
            mentions = []
            ngrams = []
            for sub in list(self.description['subreddit']):
                mentions.append(self.sub_mentions(sub))
                ngrams.append(self.freqNgrams(sub))
                print(f"{sub}.. done computing mentions and ngrams")
            self.description['sub_mentions'] = mentions
            self.description['ngrams'] = ngrams
            self.description.to_csv(subs, sep=';', encoding='utf-8-sig')

        return self.posts, self.description

    def get_window(self,text, platformlist):
        windows = []
        for p in platformlist:
            splittext = text.split(p)
            if len(splittext) > 1:
                w1,w2="",""
                for i in range(len(splittext)):
                    if i == 0:
                        w1 = " ".join(splittext[i].split()[-6:])
                    elif i == len(splittext)-1:
                        w2 = " ".join(splittext[i].split()[:6])
                        window = f"{w1} {p} {w2}"
                        windows.append(window)
                    else:
                        w2 = " ".join(splittext[i].split()[:6])
                        window = f"{w1} {p} {w2}"
                        windows.append(window)
                        w1 = " ".join(splittext[i].split()[-6:])
        return windows

    def add_windows(self, platformlist):
        platforms = []
        self.posts['window'] = pd.NA
        with open(platformlist, 'r') as p:
            platforms = p.read().replace("\n", " ").split()
        for i in range(len(self.posts)):
            text = str(self.posts.iloc[i]['body']).lower() 
            if len(text) > 0:
                w_text = self.get_window(text, platforms)
                self.posts.iat[i,11] = w_text
                
        return None

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
    # Pandas print setting
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)

    # Input files
    subs = "subredditsV1.txt"
    plats = "platformsV1.txt"

    # Scraper init
    scraper = RScraper("reddit-credentials.txt")

    #Load previous collection
    #posts, description = scraper.load("subredditsV1_2.csv", "postsV1_2.csv")
    posts, description = scraper.load("subreddits_vu.csv", "posts_vu.csv")

    # Add windows
    scraper.add_windows(plats)
    scraper.posts.to_csv("postsV1_3.csv", sep=";",encoding='utf-8-sig')



    # Collect new data
    #data = scraper.fetch_posts(subs,plats, 1000)
    #print(data.head())
    #print(scraper.summary())
    #input("Save this collection? Else, abort.")
    #scraper.safe_all_to_csvs()

    #input()




