from google.cloud import firestore

db = firestore.Client()


def like_news_item(request):
    request_json = request.get_json()
    if request.args and "item_id" in request.args:
        item_id = request.args.get("item_id")
    elif request_json and "item_id" in request_json:
        item_id = request_json["item_id"]
    else:
        return "Missing item_id"

    news_item_ref = db.collection("news_feed_items").document(item_id)

    news_item_ref.update({"likes": firestore.Increment(1)})

    return "News item liked.", 200
