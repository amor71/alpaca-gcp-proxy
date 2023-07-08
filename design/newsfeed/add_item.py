from google.cloud import firestore

db = firestore.Client()


def add_news_item(request):
    request_json = request.get_json()
    if request.args and "title" in request.args and "content" in request.args:
        title = request.args.get("title")
        content = request.args.get("content")
    elif (
        request_json and "title" in request_json and "content" in request_json
    ):
        title = request_json["title"]
        content = request_json["content"]
    else:
        return "Missing title or content"

    news_feed_item = {
        "title": title,
        "content": content,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "likes": 0,
    }

    db.collection("news_feed_items").add(news_feed_item)

    return "News item added.", 201
