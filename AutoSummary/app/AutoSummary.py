import sqlite3 as sqllite
import sys

from flask import Flask, request, jsonify
from Assignment import Assignment

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.edmundson import EdmundsonSummarizer
from sumy.summarizers.kl import KLSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.sum_basic import SumBasicSummarizer
from sumy.summarizers.random import RandomSummarizer

from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words


app = Flask(__name__)
assignments = []

LANGUAGE = "english"
SENTENCES_COUNT = 10
con = None
cur = None


def setup_SqlLite_DB():
    try:
        global con
        con = sqllite.connect('comments.db')
        global cur
        cur = con.cursor()
        #cur.execute('DROP TABLE IF EXISTS Comment')
        sql = "CREATE TABLE IF NOT EXISTS Comment (id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER, rubric_id INTEGER, reviewer_id INTEGER, grade FLOAT, content VARCHAR)"
        cur.execute(sql)
        con.commit()

    except sqllite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)

setup_SqlLite_DB()

@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/assignment/<aid>/rubric/<rid>/comments', methods=['POST'])
def add_comments(aid, rid):
    if aid.isdigit and rid.isdigit:
         if int(aid) >= 0 and int(rid) >= 0:
            obj=request.get_json()

            tuples = [(int(aid), int(rid), int(item["reviewer"]), float(item["grade"]), item["content"]) for item in obj["comments"]]

            cur.executemany("INSERT INTO Comment VALUES(NULL, ?, ?, ?, ?, ?)", tuples)
            con.commit()
            cur.execute("SELECT COUNT(id) FROM Comment WHERE assignment_id=" + aid + " AND rubric_id=" + rid)
            row = cur.fetchone()
            return jsonify(Id=row[0])
         else:
            return jsonify(Exception="Assignment ID and Rubric ID cannot be negative")
    else:
        return jsonify(Exception="Assignment ID and Rubric ID must be a number")


@app.route('/assignment/<aid>/rubric/<rid>/comments', methods=['GET'])
def get_comments(aid, rid):
    if aid.isdigit and rid.isdigit:
         if int(aid) >= 0 and int(rid) >= 0:
            cur.execute("SELECT reviewer_id, grade, content FROM Comment WHERE assignment_id=" + aid + " AND rubric_id=" + rid)
            row = cur.fetchall()
            if len(row) == 0 :
                return jsonify(Comments="Empty")
            else:
                comments= [{"reviewer":item[0], "grade":item[1], "content":item[2]} for item in row]
                return jsonify(Comments=comments)
         else:
            return jsonify(Exception="Assignment ID and Rubric ID cannot be negative")
    else:
        return jsonify(Exception="Assignment ID and Rubric ID must be a number")

@app.route('/assignment/<aid>/rubric/<rid>/comments/summary', methods=['GET'])
def get_summary_default(aid, rid):
    return get_summary_base(aid, rid)

@app.route('/assignment/<aid>/rubric/<rid>/comments/summary/<length>', methods=['GET'])
def get_summary_len(aid, rid, length):
    return get_summary_base(aid, rid, length)

@app.route('/assignment/<aid>/rubric/<rid>/comments/summary/<length>/<algorithm>', methods=['GET'])
def get_summary_len_alg(aid, rid, length, algorithm):
    return get_summary_base(aid, rid, length, algorithm)

@app.route('/summary', methods=['POST'])
def get_summary_generic():
    try:
        obj=request.get_json()
        corpus =  ". ".join([ sentence["sentence"] for sentence in obj['sentences']])
        return jsonify(Summary=summarize(corpus, obj['length'], obj['algorithm']))
    except Exception as e:
        return jsonify(Exception="The input format is incorrect. It should be {\"length\": 1, \"algorithm\":\"Lsa\", \"sentences\":[{\"sentence\":\"....\"}, {\"sentence\":\"....\"}] }")

def get_summary_base(aid, rid, length=10, algorithm="TextRank"):
    if aid.isdigit and rid.isdigit:
         if int(aid) >= 0 and int(rid) >= 0:
            cur.execute("SELECT reviewer_id, grade, content FROM Comment WHERE assignment_id=" + aid + " AND rubric_id=" + rid)
            row = cur.fetchall()
            if len(row) == 0 :
                return jsonify(Summary="Empty")
            else:
                # comments= [{"reviewer":item[0], "grade":item[1], "content":item[2]} for item in row]
                corpus = ". ".join([item[2] for item in row])
                summary = summarize(corpus, length, algorithm)
                return jsonify(Summary=summary)
         else:
            return jsonify(Exception="Assignment ID and Rubric ID cannot be negative")
    else:
        return jsonify(Exception="Assignment ID and Rubric ID must be a number")

def summarize(corpus, length, algorithm):
    parser = PlaintextParser.from_string(corpus,Tokenizer(LANGUAGE))

    if algorithm == "TextRank":
        summarizer = TextRankSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "LexRank":
        summarizer = LexRankSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "Luhn":
        summarizer = LuhnSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "Edmundson":
        summarizer = EdmundsonSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "Kl":
        summarizer = KLSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "Lsa":
        summarizer = LsaSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "SumBasic":
        summarizer = SumBasicSummarizer(Stemmer(LANGUAGE))
    elif algorithm == "Random":
        summarizer = RandomSummarizer(Stemmer(LANGUAGE))

    summarizer.stop_words = get_stop_words(LANGUAGE)
    summary = " ".join([obj._text for obj in summarizer(parser.document, length)])

    return summary

if __name__ == '__main__':
    app.run()
