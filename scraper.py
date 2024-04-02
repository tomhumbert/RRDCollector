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
    def __init__(self, cred_file, title=""):
        """Initialize praw with personal credentials and collect new datasets"""
        creds = open(cred_file,'r').read().replace("\n", " ").split()
        super().__init__(client_id= creds[0], client_secret= creds[1], user_agent= creds[2])

        self.posts = pd.DataFrame(columns=['query','subreddit', 'post_id', 'link', 'date', 'author', 'title', 'body', 'n_comments', 'up_ratio', 'distinguished', 'is_nsfw', 'external_links'])
        self.comments = pd.DataFrame(columns=['post_id','comment_id','author','body'])
        self.description = pd.DataFrame(columns=['subreddit','n_posts','n_comments','external_links'])
        self.title = title

    def load_stored_data(self, subs, posts):
        """
        in:
        does:
        out:
        """
        # Load previously collected posts
        self.title = posts.split('_')[0]
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
                mentions.append(self.collect_sub_mentions(sub))
                ngrams.append(self.find_frequent_ngrams(sub))
                print(f"{sub}.. done computing mentions and ngrams")
            self.description['sub_mentions'] = mentions
            self.description['ngrams'] = ngrams
            self.description.to_csv(subs, sep=';', encoding='utf-8-sig')

        return self.posts, self.description

    def build_queries(self, words, query_mode):
        query = ""
        if query_mode == 'bundled':
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
            else:
                query = ' OR '.join(words)

        elif query_mode == 'singles':
            query = words

        return query


    def prepare_collection(self, subs, keywords, query_mode='bundled'):
        """BUILDING THE QUERY
        The type of the search keywords is string, thus a single word to search for or the path to a file with multiple keywords.
        """
        query = False
        subreddits = False

        ## PREPARE TARGET SUBREDDIT(S)
        if type(subs) == None:
            subreddits = ['all']
        elif len(subs) == 0:
            subreddits = ['all']
        # subreddit parameter is a string:
        elif type(subs) == str:
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
                    words = ['"'+b.replace("\n", "")+'"' for b in keywords]
                    query = self.build_queries(words, query_mode)

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
            query = self.build_queries(words, query_mode)
        else:
            print("The keyword list is not in the right format, please check the documentation of this function.")
        
        return subreddits, query


    def collect_posts(self, subs, keywords='', mode='search', lim=1000, query_mode='bundled', post_order="new"):
        """Fetch all posts resulting from a query on given keywords.
        Takes parameters;  
        sub (either a single <string> name of a subreddit, a <list> of strings of subreddit names or a name of a text file containing subreddit names) and
        keywords (single <string>, <list> of strings or a name of a file, containing keywords)
        Returns pandas dataframe of all results."""
        subreddits, query = self.prepare_collection(subs, keywords, query_mode)
        print("====================================\n")
        print(bcolors.HEADER + "Data collection process has been prepared.\n Looking for:" + bcolors.ENDC)
        print(query)
        print(bcolors.HEADER + "In the list of subs:" + bcolors.ENDC)
        print(subreddits)
        print("====================================\n")
        time.sleep(3)
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
                        matched_posts = self.subreddit(subreddit).search(q, sort=post_order, limit=lim)
                    except RedditAPIException as e:
                        Print(bcolors.WARNING+f"Encountered an error. It reads: {e}, The program will now sleep for 5 min, then try again. All progress is saved"+ bcolors.ENDC)
                        self.safe_all()
                        time.sleep(300)
                        matched_posts = self.subreddit(subreddit).search(q, sort=post_order, limit=lim)
                    finally:
                        for post in matched_posts:
                            data, ext_links = self.extract_data(post, subreddit, ext_links)
                            self.posts.loc[len(self.posts)] = [q] + data
                            npost += 1

                    dslen = len(self.posts)
                    print(f"The dataset now contains {dslen} posts.\n\n")

            elif mode == 'top':
                # IGNORES QUERY
                print("Fetching the top posts of the past year.")
                try:
                    matched_posts = self.subreddit(subreddit).top(time_filter="year", limit=None)
                    for post in matched_posts:
                        data, ext_links = self.extract_data(post, subreddit, ext_links)
                        self.posts.loc[len(self.posts)] = [q] + data
                        npost += 1
                except:
                    print("THERE IS A PROBLEM WITH THIS SUB. Check the spelling.")

            if(nsub % 500 == 0):
                print(bcolors.BOLD+"Reached 500 Subreddits mile stone. Auto-save collection. Waiting 5 minutes to appease server."+ bcolors.ENDC)
                self.safe_all()
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
        self.safe_all()
        return self.posts

#subreddit','n_posts','n_comments','external_links'

    def collect_authors_posts(self, authors):
        """
        Authors must be a list type. Returns the maximum of recent posts for each author.
        """
        q=''
        for author in authors:
            print("========================================================")
            print(f"Fetching all recent posts for {author}")
            npost = 0
            ext_links = dict()

            try:
                matched_posts = self.redditor(author).submissions.new(limit=1000)
                for post in matched_posts:
                    subreddit = post.subreddit.display_name
                    data, ext_links = self.extract_data(post, subreddit, ext_links)
                    self.posts.loc[len(self.posts)] = [q] + data
                    npost += 1
            except:
                print("THERE IS A PROBLEM WITH THIS AUTHOR. Account likely suspended.")

            # Add information about subreddits in description file.
            self.description.loc[len(self.description)] = [author, npost, 0, ext_links]
            print(f"Found {npost} posts.\n")
            dslen = len(self.posts)
            print(f"The dataset now contains {dslen} posts.\n\n")

        return self.posts

    def collect_comments(self):
        """
        in:
        does:
        out:
        """
        for ids in self.posts['post_id'].tolist():
            print(f"Collecting comments from post with ID {ids}")
            self.get_post_comments(ids)
        return None

    def get_post_comments(self, post_id):
        post = self.submission(post_id)
        post.comments.replace_more(limit=None)
        for top_level_comment in post.comments:
            text = top_level_comment.body
            author = top_level_comment.author
            cid = top_level_comment.id
            if not text == "[deleted]" and cid not in self.comments['comment_id']:
                self.comments.loc[len(self.comments)] = [post_id, cid, author, text]
        return None
   
    def summarise_data(self):
        """
        in:
        does:
        out:
        """
        if not 'all' in list(self.description['subreddit']):
            total = self.description['n_posts'].sum()
            self.description.loc[len(self.description)] = ['all', total, 0, ""]
        return self.description

    def remove_duplicates(self):
        """Removes duplicate posts"""
        return None
        
    def detect_bots(self):
        """Detect bot posts"""
        return None

    def extract_data(self, post, sub, ext_links):
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
        ext_links = self.add_to_dict(ext_links,tdomain,bdomain)
        data = [subreddit, postid, link, date, author, title, body, ncomm, uprat, dist, nsfw, external_links]
        return data, ext_links


    def clean_links(self, text):
        """finds links in text, returns text and list of links"""
        ntext = text
        # url regex
        linkRegex = r"([http:\/\/|ftp:\/\/|https:\/\/]*[www\.]*(?P<dom>[\w_-]+)\.[de|com|net|org|nl|ca|co\.uk|co|ly|le|in|es][\w?=%&/#]*[\w@?^=%&\/~+#-])"
        # collect all links
        links = re.findall(linkRegex, ntext)
        # replace all reddit style markup links with only text
        #ntext = re.sub(r"(\[(?P<txt>[\s]*[\S]*)\]\([\s]*[\S]*\))", "\g<txt>", ntext)
        # replace all remaining links with main part of address
        #ntext = re.sub(linkRegex, "\g<dom>hyperlink", ntext)

        linkdoms = [l[1] for l in links]
        fulllinks = [l[0] for l in links]
        linkdict = dict()
        for l in linkdoms:
            if l in linkdict.keys():
                linkdict[l] = linkdict[l]+1
            else:
                linkdict[l] = 1

        return ntext, linkdict, fulllinks

    def generate_corpus(self, sub = False, stringlist = False):
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

    def prepare_text_for_nlp(self, txt):
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

    def find_frequent_ngrams(self, sub, lim = 7):
        freq_ngrams = []
        c_vec = CountVectorizer(ngram_range=(3,5))
        corpus = self.generate_corpus(sub=sub, stringlist=True)
        corpus = [self.prepare_text_for_nlp(c) for c in corpus]
        if len(corpus) > 2:
            ngrams = c_vec.fit_transform(corpus)
            vocab = c_vec.vocabulary_
            count_values = ngrams.toarray().sum(axis=0)
            for ng_count, ng_text in sorted([(count_values[i],k) for k,i in vocab.items()], reverse=True):
                if ng_count >= lim:
                    freq_ngrams.append((ng_text, ng_count))
        return dict(freq_ngrams)

    def collect_sub_mentions(self, sub='all'):
        mentioned_subs = False
        if sub == 'all':
            mentioned_subs = pd.DataFrame(columns=["sub", "mentions"])
            subs = list(self.description['subreddit'])
            for s in subs:
                text = self.generate_corpus(s)
                ment_list = [t for t in s.split() if t.startswith('r/')]
                ments = Counter(ment_list)
                mentioned_subs.loc[len(mentioned_subs)] = [s, dict(ments)]
        else:
            text = self.prepare_text_for_nlp(self.generate_corpus(sub)).split()
            ment_list = [t for t in text if t.startswith('r/')]
            ments = Counter(ment_list)
            mentioned_subs = dict(ments)

        return mentioned_subs

    def add_to_dict(self,dc,dict1,dict2):
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

    def safe_all(self, mode='csv'):
        self.check_data_folder()
        # Save pandas dataframes to file
        now = datetime.now()
        now = str(now)[:-7].replace(" ", "_").replace(":", "_")
        fname = os.path.join('data', f"{self.title}_posts_{now}.csv")
        dname = os.path.join('data', f"{self.title}_subreddits_{now}.csv")
        cname = os.path.join('data', f"{self.title}_comments_{now}.csv")

        if mode == 'csv':
            self.posts.to_csv(fname, sep=";",encoding='utf-8-sig')
            self.description.to_csv(dname, sep=";",encoding='utf-8-sig')
            self.comments.to_csv(cname, sep=";",encoding='utf-8-sig')
            print("All data has been saved to CSV files.\n>{fname}\n>{cname}\n>{dname}")

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

    def add_window_to_keyword_in_text(self, keywords):
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

    def check_data_folder(self):
        # Get the current working directory
        current_dir = os.getcwd()
        # Check if the 'data' folder exists
        data_folder = os.path.join(current_dir, 'data')
        if not os.path.exists(data_folder):
            # If 'data' folder doesn't exist, create it
            os.makedirs(data_folder)
            print("Created 'data' folder in the current working directory.")
            

        


def main():
    return True


if __name__ == "__main__":
    # Pandas print setting
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)

    # Input files
    subs = ''

    words = ['FUD', 'MSM', 'actual news', 'astroturfing', 'bad information', 'bad journalism', 'blatant lies', 'blatant misinformation', 'bullshit propaganda', 'conspiracy theories', 'disinfo', 'disinformation', 'fake news', 'false facts', 'false info', 'false information', 'false propaganda', 'falsehoods', 'falsities', 'fear mongering', 'fear-mongering', 'fearmongering', 'government propaganda', 'half truths', 'half-truths', 'just propaganda', 'lies', 'main stream media', 'mainstream media', 'media outlets', 'mis-information', 'misinformation', 'misleading information', 'mistruths', 'mongering', 'news agencies', 'news media', 'news outlets', 'outright lies', 'paid shills', 'propaganda', 'propagandists', 'propoganda', 'real news', 'sensational headlines', 'sensationalism', 'sensationalist bullshit', 'sensationalizing', 'shitty journalism', 'yellow journalism', 'blowback', 'deception', 'betrayal', 'lying', 'myth']

    # Scraper init
    scraper = RScraper("reddit-credentials.txt",title='misinfo_project')

    #Load previous collection
    #posts, description = scraper.load("classified_description.csv", "classified_posts.csv")
    #posts, description = scraper.load("subreddits.csv", "posts.csv")

    # Add windows
    #scraper.add_windows(words)

    # Collect new data
    #data = scraper.collect_posts(subs, keywords=words, query_mode='singles')
    #print(data.head())
    #scraper = RScraper("reddit-credentials.txt",title='misinfo_project_topposts')
    #data = scraper.collect_posts(subs, keywords=words, query_mode='singles', post_order="top")
    #print(data.head())
    #scraper = RScraper("reddit-credentials.txt",title='misinfo_project_hotposts')
    #data = scraper.collect_posts(subs, keywords=words, query_mode='singles',post_order="hot")
    scraper = RScraper("reddit-credentials.txt",title='misinfo_project_risingposts')
    data = scraper.collect_posts(subs, keywords=words, query_mode='singles',post_order="rising")
    print(data.head())
    print()
    print(scraper.description)
    print()

    #input()




