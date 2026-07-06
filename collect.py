"""Entry point: run all collectors and store results.

Usage:
    python collect.py
"""
from src import db
from src.collectors.dart import collect_dart
from src.collectors.edgar import collect_edgar
from src.collectors.news import collect_news
from src.collectors.price import collect_prices


def main() -> None:
    db.init_db()

    articles = collect_news()
    n_articles = db.insert_articles(articles)

    disclosures = collect_dart() + collect_edgar()
    n_disclosures = db.insert_disclosures(disclosures)

    prices = collect_prices()
    n_prices = db.insert_prices(prices)

    print("\n=== summary ===")
    print(f"articles:    {len(articles):4d} fetched, {n_articles:4d} new")
    print(f"disclosures: {len(disclosures):4d} fetched, {n_disclosures:4d} new")
    print(f"prices:      {len(prices):4d} fetched, {n_prices:4d} new")


if __name__ == "__main__":
    main()
