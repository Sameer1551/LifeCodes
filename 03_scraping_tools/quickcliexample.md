# 1️⃣ Basic scrape – grab titles and paragraphs
python web_scraper.py basic https://news.ycombinator.com --selector "a.storylink"

# 2️⃣ Pagination (news site that uses ?page=)
python web_scraper.py paginate https://example.com/articles \
      --page-param page \
      --selector ".article-title" \
      --max-pages 5

# 3️⃣ Login‑scrape (POST login)
python web_scraper.py login https://example.com/login https://example.com/dashboard \
      --payload '{"username":"bob","password":"secret"}' \
      --selector ".welcome"

# 4️⃣ API collector
python web_scraper.py api https://api.github.com/repos/python/cpython \
      --headers '{"Accept":"application/vnd.github.v3+json"}'

# 5️⃣ Download all images from a gallery page
python web_scraper.py download-images https://unsplash.com/s/photos/cats \
      --out-dir ./cat_images

# 6️⃣ Download every PDF linked on a research‑page
python web_scraper.py download-pdfs https://arxiv.org/list/cs.AI/recent \
      --out-dir ./pdfs
      