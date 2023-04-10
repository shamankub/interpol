import json
import sqlite3

with open("result/yellow_notices_2023-04-07--21-10.json") as f:
    data = json.load(f)

data_list = [obj for obj in data]


def create_sql_table():
    conn = sqlite3.connect(f"yellow_notices_2023-04-07--21-10.db")
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE missing 
        (
            uuid CHAR(36) PRIMARY KEY,
            name VARCHAR(255),
            forename VARCHAR(255),
            birthday DATE,
            link VARCHAR(255),
            img VARCHAR(255),
            place VARCHAR(255),
            distinguishing_marks VARCHAR(255),
            date_of_event DATE
        );
    """
    )

    cur.execute(
        """
        CREATE TABLE nationalities 
        (
            criminal_id CHAR(36),
            nationality VARCHAR(255),
            FOREIGN KEY (criminal_id) REFERENCES missing(uuid)
        );
    """
    )

    conn.commit()
    conn.close()


def insert_values_into_table():
    conn = sqlite3.connect(f"yellow_notices_2023-04-07--21-10.db")
    cur = conn.cursor()

    params_list = [
        (
            el["uuid"],
            el["name"],
            el["forename"],
            el["birthday"],
            el["link"],
            el["img"],
            el["place"],
            el["distinguishing_marks"],
            el["date_of_event"],
        )
        for el in data_list
    ]

    cur.executemany(
        "INSERT INTO missing (uuid, name, forename, birthday, link, img, place, distinguishing_marks, date_of_event) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        params_list,
    )

    params_list = []
    for data in data_list:
        if data.get("nationalities"):
            for nationality in data.get("nationalities"):
                params_list.append((data["uuid"], nationality))
        else:
            params_list.append((data["uuid"], "null"))
    cur.executemany(
        "INSERT INTO nationalities (criminal_id, nationality) VALUES (?, ?)",
        params_list,
    )

    conn.commit()
    conn.close()


create_sql_table()
insert_values_into_table()
