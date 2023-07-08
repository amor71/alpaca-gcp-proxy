from google.cloud import firestore

db = firestore.Client()


def get_news_items():
    news_items = (
        db.collection("news_feed_items")
        .order_by("likes", direction=firestore.Query.DESCENDING)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .stream()
    )

    for news_item in news_items:
        print(f"{news_item.id}: {news_item.to_dict()}")
