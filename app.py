from flask import Flask, render_template, request
import time
import pymongo
import yaml
from bson.objectid import ObjectId

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-User settings
    USER_APP_NAME = "LetMeKnow"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = True      # Enable email authentication
    USER_ENABLE_USERNAME = False    # Disable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = False    # Simplify register form
    USER_EMAIL_SENDER_EMAIL = "admin@letmeknow.co"

app = Flask(__name__)
app.config.from_object(__name__+'.ConfigClass')

config = yaml.safe_load(open("config.yml"))

# TODO once logins are working this should be taken from users email address
user_email = config["flask"]["user_email"]

# Homepage
@app.route("/")
def home_page():
    return render_template("/home.html")

@app.route("/success", methods=['POST'])
def success():
    html_data_1 = request.form["subreddit_text"]
    html_data_2 = request.form["queries_text"]

    # TODO fail gracefully here
    assert html_data_1 != ""
    assert html_data_2.find("(") == -1
    assert html_data_2.find(")") == -1
    assert html_data_2.find("\"") == -1
    assert html_data_2.find("\'") == -1

    queries_list = html_data_2.split(",")
    print(queries_list)

    client = pymongo.MongoClient(config["flask"]["db_url"])
    db = client[config["flask"]["db_name"]]
    queries = db["queries"]

    dict = { "email": user_email, "subreddit": html_data_1, "search_terms": queries_list }

    x = queries.insert_one(dict)

    subreddits = db["subreddits"]
    x = subreddits.count_documents({"subreddit":html_data_1})
    print(x)
    if x == 0:
        print("empty")
        subreddits.insert_one({ "subreddit": html_data_1 })

    time.sleep(1)

    dict = queries.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=dict)

# GET
@app.route("/get_page")
def the_get_page():
    client = pymongo.MongoClient(config["flask"]["db_url"])
    db = client[config["flask"]["db_name"]]
    queries = db["queries"]
    dict = queries.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=dict)


# DELETE
@app.route("/delete_element", methods=['POST'])
def delete_element():
    key = request.form["entry1"]
    print(key)

    client = pymongo.MongoClient(config["flask"]["db_url"])
    db = client[config["flask"]["db_name"]]
    queries = db["queries"]

    # Find what subreddit this query is for
    for y in queries.find({'_id': ObjectId(key)}):
        subreddit = y["subreddit"]

    # Delete the actual query
    queries.delete_one({'_id': ObjectId(key)})

    # If that was the last query for the subreddit, remove from subreddits collection
    subreddits = db["subreddits"]
    x = queries.count_documents({"subreddit":subreddit})
    print(x)
    if x == 0:
        print("empty")
        subreddits.delete_one({ "subreddit": subreddit })

    time.sleep(1)

    dict = queries.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=dict)

if __name__== '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)