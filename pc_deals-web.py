import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sqlite3
from datetime import datetime
import hashlib

st.set_page_config(page_title="🔥 PC Hardware Deal Scanner", layout="wide", page_icon="💻")
st.title("🔥 Mein PC & Hardware Deal Scanner")
st.markdown("**Persönlicher Kleinanzeigen Deal-Bot** – nur neue gute Angebote für Gaming-PCs, Grafikkarten, CPUs etc.")

SEARCHES = [
    {"name": "Gaming PC Komplettsysteme", "url": "https://www.kleinanzeigen.de/s-gaming-pc/k0?sort=preis_auf"},
    {"name": "Grafikkarten (RTX & Co.)", "url": "https://www.kleinanzeigen.de/s-grafikkarte/k0?sort=preis_auf"},
    {"name": "CPUs / Prozessoren", "url": "https://www.kleinanzeigen.de/s-cpu-prozessor/k0?sort=preis_auf"},
    {"name": "PC Hardware allgemein", "url": "https://www.kleinanzeigen.de/s-pc-hardware/k0?sort=preis_auf"},
]

conn = sqlite3.connect("pc_deals.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS seen 
                (id TEXT PRIMARY KEY, title TEXT, price TEXT, link TEXT, timestamp TEXT)""")

def get_deals(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        deals = []
        for ad in soup.select("article.aditem"):
            title_tag = ad.select_one("h2 a")
            price_tag = ad.select_one(".aditem-main--middle--price")
            link_tag = ad.select_one("a")
            if not title_tag or not link_tag: continue
            title = title_tag.get_text(strip=True)
            link = "https://www.kleinanzeigen.de" + link_tag["href"]
            price = price_tag.get_text(strip=True) if price_tag else "Preis auf Anfrage"
            deal_id = hashlib.md5((title + link).encode()).hexdigest()
            
            if conn.execute("SELECT id FROM seen WHERE id=?", (deal_id,)).fetchone():
                continue
            deals.append({"Titel": title, "Preis": price, "Link": link, "Deal-ID": deal_id})
        return deals
    except:
        return []

st.sidebar.header("Steuerung")
if st.sidebar.button("🔄 Jetzt scannen & neue Deals laden", type="primary"):
    all_new = []
    with st.spinner("Scanne Kleinanzeigen..."):
        for s in SEARCHES:
            st.info(f"Suche: {s['name']}")
            new_deals = get_deals(s["url"])
            for d in new_deals:
                all_new.append({"Kategorie": s["name"], **d})
                conn.execute("INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?, ?)",
                            (d["Deal-ID"], d["Titel"], d["Preis"], d["Link"], datetime.now().isoformat()))
            time.sleep(2)
    
    if all_new:
        new_df = pd.DataFrame(all_new)
        if "deals_df" not in st.session_state:
            st.session_state.deals_df = new_df
        else:
            st.session_state.deals_df = pd.concat([st.session_state.deals_df, new_df]).drop_duplicates(subset=["Deal-ID"])
        st.success(f"{len(all_new)} neue Deals gefunden!")
    else:
        st.info("Keine neuen Deals seit dem letzten Scan.")

if "deals_df" in st.session_state and not st.session_state.deals_df.empty:
    df = st.session_state.deals_df.copy()
    search_term = st.text_input("🔍 Titel durchsuchen")
    if search_term:
        df = df[df["Titel"].str.contains(search_term, case=False)]
    
    st.dataframe(
        df[["Kategorie", "Titel", "Preis", "Link"]],
        column_config={"Link": st.column_config.LinkColumn("Zur Anzeige")},
        use_container_width=True,
        hide_index=True
    )
    
    csv = df.to_csv(index=False).encode()
    st.download_button("📥 Deals als CSV herunterladen", csv, "pc_deals.csv", "text/csv")
else:
    st.info("Klicke auf „Jetzt scannen“ um die ersten Deals zu laden.")

st.caption("Deine persönliche PC-Deals Website – nur neue Angebote von Kleinanzeigen")
