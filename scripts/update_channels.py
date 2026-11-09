#!/usr/bin/env python3
"""
Kanalların güncel YouTube canlı yayın ID'lerini bulur ve channels.json'a yazar.
GitHub Actions tarafından haftalık çalıştırılır. API anahtarı gerektirmez:
her kanalın youtube.com/@kanal/live sayfası o anki canlı yayına yönlenir;
sayfadan video ID'si okunur. Bulunamazsa eski ID korunur.
"""
import json, re, sys, time, urllib.request, datetime, pathlib

# id -> YouTube kanal adresi (handle). index.html içindeki CATALOG id'leriyle aynı.
CHANNELS = {
    "ntv":         "NTV",
    "haberturk":   "haberturktv",
    "cnnturk":     "cnnturk",
    "trthaber":    "trthaber",
    "ahaber":      "ahaber",
    "halktv":      "Halktv-eu",
    "sozcu":       "Sozcutelevizyonu",
    "haberglobal": "haberglobal",
    "tv100":       "tv100",
    "tgrthaber":   "tgrthaber",
    "24tv":        "YirmidortTV",
    "krt":         "krtcanli",
    "ulusal":      "ulusalkanalTV",
    "tvnet":       "TVNET",
    "benguturk":   "tvbenguturk",
    "ulketv":      "ulketv",
    "akittv":      "akittv",
    "liderhaber":  "liderhabertv",
    "kozatv":      "KozaTv",
    "trtworld":    "trtworld",
    "bloomberght": "bloomberght",
    "cnbce":       "cnbce",
    "ekoturk":     "EKOTURKTV",
    "aspor":       "ASpor",
    "beinhaber":   "beINSPORTST%C3%BCrkiye",
    "htspor":      "htspor",
    "showmax":     "showtv",
}

OUT = pathlib.Path(__file__).resolve().parent.parent / "channels.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr,en;q=0.8",
}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.geturl(), r.read().decode("utf-8", "ignore")

def find_live_id(handle):
    """Kanalın /live sayfası canlı yayına yönleniyorsa o videonun ID'sini döndürür.
    Sayfa içindeki rastgele videoId'ler KULLANILMAZ (öneri listesi yanlış kanal verebilir)."""
    final_url, html = fetch(f"https://www.youtube.com/@{handle}/live")
    m = re.search(r"[?&]v=([\w-]{11})", final_url)
    if m: return m.group(1)
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([\w-]{11})"', html)
    if m: return m.group(1)
    return None

def video_details(html):
    i = html.find('"videoDetails":{')
    return html[i:i+4000] if i >= 0 else ""

def is_live(video_id):
    """Yalnız bu videonun kendi videoDetails bloğuna bakar."""
    try:
        _, html = fetch(f"https://www.youtube.com/watch?v={video_id}")
        vd = video_details(html)
        return f'"videoId":"{video_id}"' in vd and '"isLive":true' in vd
    except Exception:
        return False

def main():
    old = {}
    if OUT.exists():
        try: old = json.loads(OUT.read_text("utf-8")).get("channels", {})
        except Exception: old = {}
    result, changed = {}, 0
    for cid, handle in CHANNELS.items():
        vid = None
        for attempt in range(2):
            try:
                vid = find_live_id(handle); break
            except Exception as e:
                print(f"  {cid}: hata ({e}), tekrar deneniyor", file=sys.stderr); time.sleep(3)
        prev = old.get(cid, {}).get("yt")
        if vid and vid != prev and not is_live(vid):
            vid = None
        # Eski ID hâlâ canlıysa onu koru (24 saat yayınlar program yayınlarına tercih edilir)
        if prev and vid and vid != prev and is_live(prev):
            vid = prev
        if vid:
            result[cid] = {"yt": vid}
            if vid != prev: changed += 1
            print(f"✔ {cid:12s} {vid}" + ("" if vid == prev else f"  (eski: {prev})"))
        elif prev and is_live(prev):
            result[cid] = {"yt": prev}
            print(f"• {cid:12s} canlı yayın bulunamadı, eski ID korundu: {prev}")
        else:
            print(f"✖ {cid:12s} canlı yayın bulunamadı")
        time.sleep(1.5)
    data = {"updated": datetime.date.today().isoformat(), "channels": result}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"\n{len(result)} kanal yazıldı, {changed} değişti → {OUT}")

if __name__ == "__main__":
    main()
