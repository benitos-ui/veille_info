import urllib.request as u, time
urls = {
    "Google Actualités EN": "https://news.google.com/rss/search?q=%22artificial+intelligence%22+architecture+construction+when:7d&hl=en-US&gl=US&ceid=US:en",
    "Google Actualités FR": "https://news.google.com/rss/search?q=intelligence+artificielle+BTP+when:7d&hl=fr&gl=FR&ceid=FR:fr",
    "AEC Magazine": "https://aecmag.com/feed/",
    "Construction Dive": "https://www.constructiondive.com/feeds/news/",
    "Archinect": "https://archinect.com/feed",
}
for nom, url in urls.items():
    try:
        req = u.Request(url, headers={"User-Agent": "Mozilla/5.0 (veille-ifri-groupe6)"})
        debut = u.urlopen(req, timeout=25).read()[:300].decode("utf-8", "ignore").lower()
        print("OK   " if ("<rss" in debut or "<feed" in debut) else "HTML ", nom)
    except Exception as e:
        print("ERREUR", nom, e)
    time.sleep(3)