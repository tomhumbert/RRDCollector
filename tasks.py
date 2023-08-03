# get upvote counts
from praw import Reddit
import time, os, csv, re, sys, math
import pandas as pd

posts = pd.read_csv("../Uni/Intersectionality_paper_rp/data/classified_posts_single_app.csv")
creds = open(("reddit-credentials.txt"),'r').read().replace("\n", " ").split()
scrape = Reddit(client_id=creds[0], client_secret=creds[1], user_agent=creds[2])
posts = posts.loc[:,['Date','ID', 'Subreddit','cluster','Author', 'Title', 'Post', 'genre.x','app_mention','pred_label']]

upvotes = []
up_ratio =[]
n_comments = []
distinguished = []

datalen = len(posts['ID'])
print("Start collecting some more post data")
for i in range(datalen):
    postid = posts.iloc[i,1]
    postgood = False
    post = scrape.submission(id=postid)

    try:
        score = post.score
        upvote_ratio=post.upvote_ratio
        num_comments=post.num_comments
        isdistinguished=post.distinguished
        postgood=True
    except Exception as e:
        print(e)
    if(postgood):
        upvotes.append(score)
        up_ratio.append(upvote_ratio)
        n_comments.append(num_comments)
        distinguished.append(isdistinguished)
    else:
        upvotes.append("NA")
        up_ratio.append("NA")
        n_comments.append("NA")
        distinguished.append("NA")

    if(i==datalen//2):
        print("Whe are past half the dataset")

print("Done collecting")
posts['upvotes']=upvotes
posts['up_ratio']=up_ratio
posts['n_comments']=n_comments
posts['distinguished']=distinguished
posts.to_csv("ext_class_posts.csv")
print("Saved")
