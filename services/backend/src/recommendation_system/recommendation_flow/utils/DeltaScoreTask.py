"""
Adds image scores to the database
"""

from src import create_app
from src import db
from sqlalchemy import MetaData, Table, create_engine

import csv

def add_image_scores(score_file):

    with open(score_file) as f:
        score_list = list(csv.reader(f))
        scores = list(map(lambda x: {'content_id': int(x[0]), 'score': float(x[1])},
                          score_list[1:]))

    with db.engine.connect() as con:

        con.execute("DROP TABLE IF EXISTS score;")
        con.execute("CREATE TABLE score (content_id int, score float);")

        metadata = MetaData()
        metadata.reflect(db.engine, only=['score'])

        table = Table('score', metadata, autoload=True, autoload_with=db.engine)

        db.engine.execute(table.insert(), scores)

    return

if __name__ == '__main__':
    app = create_app()
    print("Adding image scores")
    with app.app_context():
        score_file = "/usr/src/app/src/delta/image_quality.csv"
        add_image_scores(score_file)
    print("Finished adding image scores")
