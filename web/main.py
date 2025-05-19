""" Stretch Goal - Access and control device remotely via simple web app """
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<div><h2> Astroflo - Sky Navigation Tool </h2> <p> Active - Unsolved/no results. </p> </div>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)