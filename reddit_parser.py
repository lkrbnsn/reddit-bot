import praw
import time
import pymongo
import smtplib, ssl
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# TODO replace all the print statements here with proper logging

def send_email(receiver_email, title, link):
    """
    Sends an email notification about a reddit post
    
    :param receiver_email: Email address to send to
    :param title: Title of post
    :param link: Link to post
    """
    print("Sending", link, "to", receiver_email)
    port = config["email"]["port"]
    smtp_server = config["email"]["smtp_server"]
    sender_email = config["email"]["sender_email"]
    password = config["email"]["password"]

    message = MIMEMultipart("alternative")
    message["Subject"] = "LetMeKnow Alert"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create the plain-text and HTML version of your message
    text = """\
    Dear user,
    A new post on Reddit is available here:""" + link
    html = """\
    <html>
    <body>
        <p>Dear user,<br>
        A new post on Reddit is available 
        <a href=\"""" + link + """\">here</a>.
        """ + title + """
        </p>
    </body>
    </html>
    """

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

def grab_posts(subreddit_name, posts_to_grab):
    """
    Gets a specified amount of posts from a subreddit, sorted by
    latest first.
    
    :param subreddit_name: Subreddit to get posts from
    :param posts_to_grab: Number of posts to get
    :return posts: List of posts
    """
    subreddit = reddit.subreddit(subreddit_name).new(limit=posts_to_grab)
    posts = []
    for post in subreddit:
        posts.append(post)
    return posts

def get_latest_posts(subreddit, lastpost_time):
    """
    Gets all posts from a subreddit back to lastpost_time.
    
    :param subreddit: Subreddit to get posts from
    :param lastpost_time: Only get posts newer than this time
    :return posts_list: List of posts, empty list if there are no new posts
    :return firstpost_time: Time of first post in list
    """
    print(lastpost_time)
    try:
        reddit.subreddits.search_by_name(subreddit, exact=True)
    except:
        print("Subreddit", subreddit, "not found")
        return

    # TODO there's something slightly screwy about this, extra posts are getting added in
    # TODO restrict searches on r/all
    posts_to_grab=10
    posts_list = grab_posts(subreddit, posts_to_grab)
    print(posts_list[-1].created_utc)
    print("OK! grabbed posts:", len(posts_list))
    while (posts_list[-1].created_utc > lastpost_time+1):
        print("Grabbing more posts")
        posts_to_grab = posts_to_grab+10
        posts_list = grab_posts(subreddit, posts_to_grab)
        print(posts_list[-1].created_utc)
    
    # Delete the posts from the list that were submitted before lastpost_time
    print()
    cut_from = 0
    for index, post in enumerate(posts_list):
        # print(post.created_utc)
        if post.created_utc <= lastpost_time:
            print(index, post.created_utc, "cut")
        else:
            print(index, post.created_utc)
            # posts_list.remove(post)
    print()

    for index, post in enumerate(posts_list):
        # print(post.created_utc)
        if post.created_utc <= lastpost_time:
            cut_from = index
            break
    print()

    firstpost_time = posts_list[0].created_utc
    # TODO slice the list so that we only return posts that are newer than lastpost_time
    # return empty list if there are no newer posts? How do we return the lastpost_time in this case?
    print("cutting from:", cut_from)
    posts_list = posts_list[:cut_from]
    for post in posts_list:
        print(post.created_utc)
    print()
    print("Number of posts retrieved:", len(posts_list))
    return posts_list, firstpost_time

def search_latest_posts(posts, queries, email):
    """
    Searches a list of posts for given strings and sends an email if strings are found
    
    :param posts: List of posts to search
    :param queries: List of strings to search for
    :param email: Email to send notifications to
    """
    for submission in posts:
        queries_found = True
        for query in queries:
            # if(submission.title.find(query) != -1):
            #     print(submission.title)
            if(query.lower() in submission.title.lower()):
                print(submission.title, submission.created_utc)
                print(submission.url) # TODO this sometimes redirects to another site, we don't always want it
                print()
            else:
                queries_found = False
        
        if(queries_found == True):
            # send email straight from here, we don't want to break the loop as there may be multiple posts in
            # the list of posts that match our queries
            print("Found!")
            send_email(email, submission.title, submission.url)

config = yaml.safe_load(open("config.yml"))

loop_time = config["loop_time"]

reddit = praw.Reddit(
    client_id=config["reddit"]["client_id"],
    client_secret=config["reddit"]["client_secret"],
    user_agent=config["reddit"]["user_agent"],
)

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
print(myclient.list_database_names())
mydb = myclient["redditapp"]
print(mydb.list_collection_names())
queries = mydb["queries"]
subreddits = mydb["subreddits"]

while True:
    start_time = time.time()

    for x in subreddits.find({}):
        print(x.get("subreddit"))
        lastpost_time = x.get("lastpost_time")
        if (lastpost_time == None):
            lastpost_time = time.time() - loop_time
        posts, firstpost_time = get_latest_posts(x.get("subreddit"), lastpost_time)
        # Update firstpost_time in the db
        subreddits.update_one(x, {"$set":{"lastpost_time":firstpost_time}})

        for y in queries.find({"subreddit":x.get("subreddit")}):
            print(y.get("subreddit"), y.get("search_terms"))
            search_latest_posts(posts, y.get("search_terms"), y.get("email"))
        print()

    stop_time = time.time()
    print("Query took", stop_time - start_time, "seconds")
    time.sleep(loop_time)