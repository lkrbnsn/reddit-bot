from flask import Flask, render_template, request, Blueprint
import time
import pymongo
import yaml
from bson.objectid import ObjectId

main = Blueprint('main', __name__)

config = yaml.safe_load(open("config.yml"))

# TODO once logins are working this should be taken from users email address
user_email = config["flask"]["user_email"]

# Homepage
@main.route("/")
def home_page():
    return render_template("/home.html")

@main.route("/success", methods=['POST'])
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
@main.route("/get_page")
def the_get_page():
    client = pymongo.MongoClient(config["flask"]["db_url"])
    db = client[config["flask"]["db_name"]]
    queries = db["queries"]
    dict = queries.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=dict)


# DELETE
@main.route("/delete_element", methods=['POST'])
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
    main.run(host="0.0.0.0", debug=True, port=5000)