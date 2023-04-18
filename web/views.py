from django.shortcuts import render
import re
import os
from ssl import Options
import nltk
import time
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from textblob import TextBlob
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from selenium.webdriver.chrome.options import Options
import mysql.connector as mysql
# Create your views here.
# nltk.download('stopwords')

def Welcome(request):
    return render(request, 'index.html')


def user(request):
    con = mysql.connect(host='localhost', user='root',password = "pRANITHA@21",database="youtube")
    cur1 = con.cursor()
    n = int(request.GET["num"])
    print(n)
    i=1
    c=""
    video_rating,video_title,video_subscribers,video_views,video_likes=[],[],[],[],[]
    while n>0:
        inp = "url"+str(i)
        url = request.GET[inp]
        print(url)
        n-=1
        c+=str(i-1)
        i+=1
        find = "select * from mainT where Video_URL=\"{0}\";".format(url)
        cur1.execute(find)
        out = cur1.fetchall()
        print(out)
        if len(out)!=0:
            video_rating.append(out[0][3])
            video_title.append(out[0][2])
            video_subscribers.append(out[0][4])
            video_views.append(out[0][5])
            video_likes.append(out[0][6])
        else:
            vr, vt, vs,vv, vl = project(url)
            video_rating.append(round(vr,5))
            video_title.append(vt)
            video_subscribers.append(vs)
            video_views.append(vv)
            video_likes.append(vl)
            insert = "insert into mainT (Video_URL, Video_Title,Rating,No_of_Subscribers,No_of_Views,No_of_Likes) values(\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\",\"{5}\");".format(url,vt,vr,vs,vv,vl)
            cur1.execute(insert)
            con.commit()

        
        resultArr = sortMax(video_rating,video_title,video_subscribers,video_views,video_likes)
    return render(request, "result.html", {'res':resultArr})
    #return render(request, "result.html", {'num':i,'rating': video_rating,'title': video_title,'subs':video_subscribers,'views':video_views,'likes':video_likes})

# ScrapComment extracts the comments from the given Youtube video.

def ScrapComment(url):
    option = webdriver.ChromeOptions()
    option.add_argument("--headless")
    driver = webdriver.Chrome(
        executable_path=ChromeDriverManager().install(), chrome_options=Options())
    driver.get(url)
    prev_h = 0
    while True:
        height = driver.execute_script("""
                function getActualHeight() {
                    return Math.max(
                        Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
                        Math.max(document.body.offsetHeight, document.documentElement.offsetHeight),
                        Math.max(document.body.clientHeight, document.documentElement.clientHeight)
                    );
                }
                return getActualHeight();
            """)
        driver.execute_script(f"window.scrollTo({prev_h},{prev_h + 200})")
        # fix the time sleep value according to your network connection
        time.sleep(1)
        prev_h += 200
        if prev_h >= height:
            break
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    title_text_div = soup.select_one('#container h1')
    title = title_text_div and title_text_div.text

    comment_div = soup.select("#content #content-text")
    comment_list = [x.text for x in comment_div]

    sub = soup.select("#content #owner-sub-count")
    subscriber = sub[0].text
    
    view = soup.select("#content #info-container")
    views = view[0].span.text

    like = soup.select("#content #segmented-like-button")
    likes = like[0].span.text

    return (title, comment_list,subscriber,views,likes)


# PreProcessing function pre-processes the comments extracted from Youtube video.

def PreProcessing(comments):
    processed_comments = []
    for i in range(len(comments)):
        processing_comments = re.sub("[^a-zA-Z]", " ", str(comments[i]))
        processing_comments = processing_comments.lower()
        processing_comments = processing_comments.split()
        ps = PorterStemmer()
        all_stopwords = stopwords.words('english')
        all_stopwords.remove('not')
        processing_comments = [
            ps.stem(word) for word in processing_comments if word not in all_stopwords]
        processing_comments = ' '.join(processing_comments)
        processed_comments.append(processing_comments)
    return (processed_comments)


# Labelling function labels the comments whether it is positive or negative or neutral

def Labelling(comments):
    labelled_comments = []
    for i in range(len(comments)):
        a = TextBlob(comments[i])
        if a.sentiment.polarity > 0.2 and a.sentiment.subjectivity >= 0.5:
            labelled_comments.append(1)
        elif a.sentiment.polarity > 0.2 and a.sentiment.subjectivity < 0.5:
            labelled_comments.append(0)
        elif a.sentiment.polarity < -0.2 and a.sentiment.subjectivity >= 0.5:
            labelled_comments.append(-1)
        elif a.sentiment.polarity < -0.2 and a.sentiment.subjectivity < 0.5:
            labelled_comments.append(0)
        else:
            labelled_comments.append(0)
    #print(labelled_comments.count(1),"/",len(labelled_comments),"out of",len(comments))
    return (labelled_comments)


# Rating function will rate the Youtube video according to the comments given to it.

def Rating(labelled_comment, total_comments):
    no_of_positive_comments = labelled_comment.count(1)
    no_of_negative_comments = labelled_comment.count(-1)
    no_of_neutral_comments = labelled_comment.count(0)
    total_no_of_comments = len(total_comments)
    positive_rating = (no_of_positive_comments/total_no_of_comments)*5
    negative_rating = (no_of_negative_comments/total_no_of_comments)*5
    neutral_rating = (no_of_neutral_comments/total_no_of_comments)*5
    # print(positive_rating,negative_rating,neutral_rating)
    #tr = (positive_rating+negative_rating+neutral_rating)/3
    return (positive_rating-negative_rating+(neutral_rating/2))


def project(url):
    video_title, video_comments = [], []
    video_title, video_comments, video_subscribers,video_views, video_likes = ScrapComment(url)
    processed_video_comments = PreProcessing(video_comments)
    labelled_video_comments = Labelling(processed_video_comments)
    video_rating = Rating(labelled_video_comments, processed_video_comments)
    #print("\nRATING THE VIDEO\n")
    #print("RATING FOR THE VIDEO :",video_title,"\n","{:.2f}".format(round(video_rating,2)))
    return (video_rating, video_title, video_subscribers,video_views, video_likes)


def sortMax(vr,vt,vs,vv,vl):
    dic = {}
    res = []
    for i in range(len(vr)):
        dic[vr[i]]=i
    vr.sort()
    for i in vr:
        a = dic[i]
        res.append([i,vt[a],vs[a],vv[a],vl[a]])
    return res