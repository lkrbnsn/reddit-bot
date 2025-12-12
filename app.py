# from flask import Flask

# app = Flask(__name__)

# @app.route("/")
# def hello_world():
#     return "<p>Hello, World!</p>"

# Final Script

# TODO clean up the variable names here

from flask import Flask, render_template, request
import pickle, time, os
import pymongo
import yaml
from bson.objectid import ObjectId

# TODO figure out did I ever actually use mongoengine? Seems like it's deprecated
# from flask_mongoengine import MongoEngine

# TODO change flask_user to flask_security
# from flask_user import login_required, UserManager, UserMixin

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-MongoEngine settings
    # MONGODB_SETTINGS = {
    #     'db': 'redditapp',
    #     'host': 'mongodb://localhost:27017/redditapp'
    # }

    # Flask-User settings
    USER_APP_NAME = "LetMeKnow"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = True      # Enable email authentication
    USER_ENABLE_USERNAME = False    # Disable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = False    # Simplify register form
    USER_EMAIL_SENDER_EMAIL = "admin@letmeknow.co"

app = Flask(__name__)
app.config.from_object(__name__+'.ConfigClass')

# # Setup Flask-MongoEngine
# db = MongoEngine(app)

# # Define the User document.
# # NB: Make sure to add flask_user UserMixin !!!
# class User(db.Document, UserMixin):
#     active = db.BooleanField(default=True)

#     # User authentication information
#     username = db.StringField(default='')
#     password = db.StringField()

#     # User information
#     first_name = db.StringField(default='')
#     last_name = db.StringField(default='')

#     # Relationships
#     # roles = db.ListField(db.StringField(), default=[])

# # Setup Flask-User and specify the User data-model
# user_manager = UserManager(app, db, User)

config = yaml.safe_load(open("config.yml"))

# TODO once logins are working this should be taken from users email address
user_email = config["flask"]["user_email"]

# Homepage
@app.route("/")
def crud_page():
    return render_template("/choose_crud_command.html")

# Update Dictionary
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

    myclient = pymongo.MongoClient(config["flask"]["db_url"])
    mydb = myclient[config["flask"]["db_name"]]
    mycol = mydb["queries"]

    mydict = { "email": user_email, "subreddit": html_data_1, "search_terms": queries_list }

    x = mycol.insert_one(mydict)

    # TODO remove this entry from the subreddits collection when the last query that uses a particular subreddit is removed
    subreddits = mydb["subreddits"]
    x = subreddits.count_documents({"subreddit":html_data_1})
    print(x)
    if x == 0:
        print("empty")
        subreddits.insert_one({ "subreddit": html_data_1 })

    print("yay")

    time.sleep(1)

    mydict = mycol.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=mydict)
    # return render_template("/get_page.html")
    # return render_template("/success.html", html_data_1=html_data_1, html_data_2=html_data_2)

# GET
@app.route("/get_page")
# @login_required
def the_get_page():
    # TODO is there a plugin we can use here?
    myclient = pymongo.MongoClient(config["flask"]["db_url"])
    mydb = myclient[config["flask"]["db_name"]]
    mycol = mydb["queries"]
    mydict = mycol.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=mydict)


# DELETE
@app.route("/delete_page")
def the_delete_page():
    file = open('dictionary_file.pkl', 'rb')
    retrieve_dictionary = pickle.load(file)
    file.close()

    return render_template("/get_page.html", retrieve_dictionary=retrieve_dictionary)

@app.route("/delete_element", methods=['POST'])
def delete_element():
    key = request.form["entry1"]
    print("hello")
    print(key)

    myclient = pymongo.MongoClient(config["flask"]["db_url"])
    mydb = myclient[config["flask"]["db_name"]]
    queries = mydb["queries"]

    # Find what subreddit this query is for
    for y in queries.find({'_id': ObjectId(key)}):
        subreddit = y["subreddit"]

    # Delete the actual query
    queries.delete_one({'_id': ObjectId(key)})

    # If that was the last query for the subreddit, remove from subreddits collection
    subreddits = mydb["subreddits"]
    x = queries.count_documents({"subreddit":subreddit})
    print(x)
    if x == 0:
        print("empty")
        subreddits.delete_one({ "subreddit": subreddit })

    mydict = queries.find({"email":user_email})
    return render_template("/get_page.html", retrieve_dictionary=mydict)
    # return render_template("/delete_success.html")

if __name__== '__main__':
    # execute_clear_dictionary.add_job(id = 'Scheduled Task', func=clear_dictionary, trigger="interval", seconds=300)
    # execute_clear_dictionary.start()
    app.run(host="0.0.0.0", debug=True, port=5000)