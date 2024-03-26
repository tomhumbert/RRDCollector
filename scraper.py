from praw import Reddit
import time, os, csv, re, sys, math
from datetime import datetime
import pandas as pd
from nltk import ngrams
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'



class RScraper(Reddit):
    def __init__(self, cred_file):
        """Initialize praw with personal credentials and create empty datasets"""
        creds = open(cred_file,'r').read().replace("\n", " ").split()
        super().__init__(client_id= creds[0], client_secret= creds[1], user_agent= creds[2])

        self.posts = pd.DataFrame(columns=['subreddit', 'post_id', 'link', 'date', 'author', 'title', 'body', 'n_comments', 'up_ratio', 'distinguished', 'is_nsfw', 'external_links'])
        self.comments = pd.DataFrame(columns=['post_id','comment_id','author','body'])
        self.description = pd.DataFrame(columns=['subreddit','n_posts','n_comments','external_links'])

    def load(self, subs, posts):
        # Load previously collected posts
        self.description = pd.read_csv(subs, delimiter=';', encoding='utf-8-sig')
        self.posts = pd.read_csv(posts, sep=';', encoding='cp1252')

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

    def summary(self):
        if not 'all' in list(self.description['subreddit']):
            total = self.description['n_posts'].sum()
            self.description.loc[len(self.description)] = ['all', total, 0, ""]
        return self.description

    def get_all(self, sub, keywords, lim):
        """
        Fetch all posts and comments
        """
        return None

    def prep_search(self, subs, keywords):
        ## BUILDING THE QUERY
        # The type of the search keywords is string, thus a single word to search for or the path to a file with multiple keywords.
        query = False
        subreddits = False

        ## PREPARE TARGET SUBREDDIT(S)
        # subreddit parameter is a string:
        if type(subs) == str:
            # The string is a path
            if subs in os.listdir(os.path.curdir):
                with open(subs, 'r') as s:
                    subreddits = s.readlines()
                    subreddits = [z.replace("\n", "") for z in subreddits]

            # The string is a subreddit name
            else:
                subreddits = [subs]

        # The subreddit parameter is a list of strings.
        elif type(subs) == list:
            subreddits = subs
        else:
            print("The input given for subs is not in the right format, please check the documentation of this function.")
            

        if type(keywords) == str:
            if keywords in os.listdir(os.path.curdir):
                print("Reading list of keywords from file.")
                with open(keywords, 'r') as p:
                    words = p.readlines()
                    words = ['"'+b.replace("\n", "")+'"' for b in words]
                    query = ' OR '.join(words)
                    query = [query]

                    ## PRAW sullies its pants if you give too long queries, its something around 30, 25 to be safe.
                    if len(words)>25:
                        print(f"There are more than 25 words. They are split into {pd.ceil(len(words)/25)} groups of 25.")
                        query = []
                        qs = math.ceil(len(words)/25)
                        for i in range(qs):
                            words_p = words[i*25:i*25+25]
                            query.append(' OR '.join(words_p))
                        rem = len(words)%25
                        query.append(' OR '.join(words[qs*25+25:qs*25+25+rem]))

            # Empty query.
            elif keywords == "" or keywords == " ":
                query = ['']
            
            # Query consists of single keyword.
            else:
                print(f"Looking for one keyword: {keywords}")
                query = [keywords]

        # The type of the search keywords is a list
        elif type(keywords) == list:
            print(f"A list of {len(keywords)} keywords has been given.")
            words = ['"'+b+'"' for b in keywords]
            query = ' OR '.join(words)
            query = [query]
        else:
            print("The keyword list is not in the right format, please check the documentation of this function.")
        
        return subreddits, query

    def get_posts(self, subs, mode='top', keywords="", lim=1000):
        """Fetch all posts resulting from a query on given keywords.
        Takes parameters;  
        sub (either a single <string> name of a subreddit, a <list> of strings of subreddit names or a name of a text file containing subreddit names) and
        keywords (single <string>, <list> of strings or a name of a file, containing keywords)
        Returns pandas dataframe of all results."""
        subreddits, query = self.prep_search(subs, keywords)
        nsub = 0

        for subreddit in subreddits:
            nsub += 1
            os.system('cls' if os.name == 'nt' else 'clear')
            print(bcolors.HEADER + f"Sub N.{nsub} - accessing r/{subreddit}" + bcolors.ENDC)
            print("====================================\n")
            npost = 0
            ext_links = dict()

            if mode == 'search':
                for q in query:
                    print(bcolors.OKBLUE+f"Executing the query:\n{q}"+ bcolors.ENDC)
                    try:
                        matched_posts = self.subreddit(subreddit).search(q, sort='new', limit=lim)
                    except RedditAPIException as e:
                        Print(bcolors.WARNING+f"Encountered an error. It reads: {e}, The program will now sleep for 5 min, then try again. All progress is saved"+ bcolors.ENDC)
                        self.safe_all_to_csv()
                        time.sleep(300)
                        matched_posts = self.subreddit(subreddit).search(q, sort='new', limit=lim)
                    finally:
                        for post in matched_posts:
                            data, ext_links = self.data_extraction(post, subreddit, ext_links)
                            self.posts.loc[len(self.posts)] = data
                            npost += 1

            if mode == 'top':
                print("Fetching the top posts of the past year.")
                try:
                    matched_posts = self.subreddit(subreddit).top(time_filter="year", limit=None)
                    for post in matched_posts:
                        data, ext_links = self.data_extraction(post, subreddit, ext_links)
                        self.posts.loc[len(self.posts)] = data
                        npost += 1
                except:
                    print("THERE IS A PROBLEM WITH THIS SUB. Check the spelling.")
            
            if(nsub % 500 == 0):
                print(bcolors.BOLD+"Reached 500 Subreddits mile stone. Auto-save collection. Waiting 5 minutes to appease server."+ bcolors.ENDC)
                self.safe_all_to_csv()
                time.sleep(60)
                print(bcolors.OKGREEN+"X" +bcolors.FAIL+ "XXXX")
                time.sleep(60)
                print(bcolors.OKGREEN+"XX" +bcolors.FAIL+ "XXX")
                time.sleep(60)
                print(bcolors.OKGREEN+"XXX" +bcolors.FAIL+ "XX")
                time.sleep(60)
                print(bcolors.OKGREEN+"XXXX" +bcolors.FAIL+ "X")
                time.sleep(60)
                print(bcolors.OKGREEN+"XXXXX" +bcolors.ENDC)
                time.sleep(2)

            # Add information about subreddits in description file.
            self.description.loc[len(self.description)] = [subreddit, npost, 0, ext_links]
            print(f"Found {npost} posts.\n")
            dslen = len(self.posts)
            print(f"The dataset now contains {dslen} posts.\n\n")
            time.sleep(1)
            print(bcolors.BOLD+".",end="", flush=True)
            time.sleep(1)
            print(".",end="", flush=True)
            time.sleep(1)
            print("."+bcolors.ENDC)
        return self.posts

#subreddit','n_posts','n_comments','external_links'

    def get_authors_posts(self, authors):
        """
        Authors must be a list type. Returns the maximum of recent posts for each author.
        """
        for author in authors:
            print("========================================================")
            print(f"Fetching all recent posts for {author}")
            npost = 0
            ext_links = dict()

            try:
                matched_posts = self.redditor(author).submissions.new(limit=1000)
                for post in matched_posts:
                    subreddit = post.subreddit.display_name
                    data, ext_links = self.data_extraction(post, subreddit, ext_links)
                    self.posts.loc[len(self.posts)] = data
                    npost += 1
            except:
                print("THERE IS A PROBLEM WITH THIS AUTHOR. Account likely suspended.")

            # Add information about subreddits in description file.
            self.description.loc[len(self.description)] = [author, npost, 0, ext_links]
            print(f"Found {npost} posts.\n")
            dslen = len(self.posts)
            print(f"The dataset now contains {dslen} posts.\n\n")

        return self.posts

    def get_all_comments(self):
        for ids in self.posts['post_id'].tolist():
            print(f"Collecting comments from post with ID {ids}")
            self.get_comments(ids)
        return None

    def get_comments(self, post_id):
        post = self.submission(post_id)
        post.comments.replace_more(limit=None)
        for top_level_comment in post.comments:
            text = top_level_comment.body
            author = top_level_comment.author
            cid = top_level_comment.id
            if not text == "[deleted]" and cid not in self.comments['comment_id']:
                self.comments.loc[len(self.comments)] = [post_id, cid, author, text]
        return None

    def data_extraction(self, post,sub, ext_links):
        subreddit = sub
        postid = post.id
        title = post.title
        title, tdomain, tlinks = self.clean_links(title)
        body = post.selftext
        body = body.replace(";", ":")
        body, bdomain, blinks = self.clean_links(body)
        author = post.author
        nsfw = post.over_18
        ncomm = post.num_comments
        uprat = post.upvote_ratio
        dist = post.distinguished
        date = datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
        link = post.permalink
        external_links = tlinks + blinks
        ext_links = self.dict_add(ext_links,tdomain,bdomain)
        data = [subreddit, postid, link, date, author, title, body, ncomm, uprat, dist, nsfw, external_links]
        return data, ext_links

    def rm_dups_and_bots(self):
        """Removes duplicate posts"""
        return None

    def clean_links(self, text):
        """Removes links from text, returns clean text and list of removed links"""
        ntext = text
        # url regex
        linkRegex = r"([http:\/\/|ftp:\/\/|https:\/\/]*[www\.]*(?P<dom>[\w_-]+)\.[de|com|net|org|nl|ca|co\.uk|co|ly|le|in|es][\w?=%&/#]*[\w@?^=%&\/~+#-])"
        # collect all links
        links = re.findall(linkRegex, ntext)
        # replace all reddit style markup links with only text
        ntext = re.sub(r"(\[(?P<txt>[\s]*[\S]*)\]\([\s]*[\S]*\))", "\g<txt>", ntext)
        # replace all remaining links with main part of address
        ntext = re.sub(linkRegex, "\g<dom>hyperlink", ntext)

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
        tokens = word_tokenize(text.lower())
        clean_tokens = [word for word in tokens if not word in stop_words.split()]
        # lemmatize
        lemmat = WordNetLemmatizer()
        clean_tokens = [lemmat.lemmatize(w) for w in clean_tokens]

        # stemmer (not always desirable)
        #stmmer = PorterStemmer()
        #clean_tokens = [stmmer.stem(w) for w in clean_tokens]
        if len(clean_tokens) > 2:
            ntext = (" ").join(clean_tokens)
        else:
            ntext = ""
        return ntext

    def freqNgrams(self, sub, lim = 7):
        freq_ngrams = []
        c_vec = CountVectorizer(ngram_range=(3,5))
        corpus = self.gen_corpus(sub=sub, stringlist=True)
        corpus = [self.nlp_prep(c) for c in corpus]
        if len(corpus) > 2:
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

    def safe_all_to_csv(self):
        # Save pandas dataframes to file
        now = datetime.now()
        now = str(now)[:-7].replace(" ", "_").replace(":", "_")
        fname = f"posts_{now}.csv"
        dname = f"subreddits_{now}.csv"
        cname = f"comments_{now}.csv"
        self.posts.to_csv(fname, sep=";",encoding='utf-8-sig')
        self.description.to_csv(dname, sep=";",encoding='utf-8-sig')
        self.comments.to_csv(cname, sep=";",encoding='utf-8-sig')
        print("All data has been saved.")
        return None

    def windower(self,text, keywords):
        windows = []
        for p in keywords:
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

    def add_windows(self, keywords):
        words = []
        self.posts['window'] = pd.NA
        with open(keywords, 'r') as p:
            words = p.read().replace("\n", " ").split()
        for i in range(len(self.posts)):
            text = str(self.posts.iloc[i]['body']).lower() 
            if len(text) > 0:
                w_text = self.windower(text, words)
                self.posts.iat[i,11] = str(w_text)
                
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
    subs = "subreddits.txt"
    words = "keywords.txt"

    # Scraper init
    scraper = RScraper("reddit-credentials.txt")

    #Load previous collection
    #posts, description = scraper.load("classified_description.csv", "classified_posts.csv")
    #posts, description = scraper.load("subreddits_vu.csv", "posts_vu.csv")

    # Add windows
    #scraper.add_windows(words)
    #scraper.posts.to_csv("postsV2_1.csv", sep=";",encoding='utf-8-sig')

    # Collect posts
    #scraper.get_all_comments()
    #scraper.safe_all_to_csvs()

    # Collect new data
    data = scraper.get_posts(subs,words, 1000)
    print(data.head())
    print(scraper.summary())
    input("Save this collection? Else, abort.")
    scraper.safe_all_to_csv()

    #input()




