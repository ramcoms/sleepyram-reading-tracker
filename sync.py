
import json
import os
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.hardcover.app/v1/graphql"
TOKEN = os.environ["HARDCOVER_API_TOKEN"]

QUERY = """

query {
  me {
    user_books(
      where: {
        status_id: { _in: [2, 3] }
      }
      limit: 500
      order_by: { updated_at: desc }
    ) {
      status_id
      rating
      book {
        id
        title
        pages
        image {
          url
        }
        contributions {
          author {
            name
          }
        }
      }
      user_book_reads(
        order_by: { id: desc }
        limit: 1
      ) {
        progress_pages
      }
    }
  }
}
"""

request = urllib.request.Request(
    API_URL,
    data=json.dumps({"query": QUERY}).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    },
    method="POST"
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read())

if "errors" in result:
    raise RuntimeError(json.dumps(result["errors"], indent=2))
users = result.get("data", {}).get("me") or []

if not users:
    raise RuntimeError("Hardcover API returned no user.")

entries = users[0].get("user_books") or []


books = []

for entry in entries:
    book = entry.get("book")
    if not book:
        continue

    status = entry.get("status_id")
    reads = entry.get("user_book_reads") or []

    progress = (
        (reads[0].get("progress_pages") or 0)
        if reads else 0
    )

    total_pages = book.get("pages") or 0

    authors = [
        item.get("author", {}).get("name")
        for item in (book.get("contributions") or [])
        if item.get("author")
    ]

    percentage = None
    if total_pages > 0:
        percentage = round(progress / total_pages * 100)

    books.append({
        "id": book.get("id"),
        "title": book.get("title"),
        "author": ", ".join(authors) or "Unknown author",
        "cover": (book.get("image") or {}).get("url"),
        "pages": total_pages,
        "progress": progress,
        "percentage": percentage,
        "rating": entry.get("rating"),
        "status": (
            "currently-reading"
            if status == 2 else "read"
        )
    })


data = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "currently_reading": [
        b for b in books if b["status"] == "currently-reading"
    ],
    "read": [
        b for b in books if b["status"] == "read"
    ]
}

with open("books.json", "w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

print(
    f"Synced {len(data['currently_reading'])} currently reading "
    f"and {len(data['read'])} finished books."
)
