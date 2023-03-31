import psycopg


def new_user_handler(payload: dict):
    print("payload=", payload)

    with psycopg.connect(
        "username=admin password=admin database=postgres unix_sock=/cloudsql/development-380917:us-central1:customers/.s.PGSQL.5432"
    ) as conn:
        print("connection", conn)
