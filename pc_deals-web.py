import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sqlite3
from datetime import datetime
import hashlib
import re

st.set_page_config(page_title="🔥 PC Hardware Deal Scanner", layout="wide", page_icon="💻")
st.title("🔥 Mein PC & Hardware Deal Scanner")
st.markdown("**Persönlicher Kleinanzeigen Deal-Bot** – nur neue gute Angebote mit Preis- & Ortsfilter")

SEARCHES = [
    {"name": "Gaming PC Komplettsysteme", "url": "https://www.kleinanzeigen.de/s-gaming-pc/k0?sort=preis_auf"},
    {"name": "Grafikkarten (RTX & Co.)", "url": "https://www.kleinanzeigen.de/s-grafikkarte/k0?sort=preis_auf"},
    {"name": "CPUs / Prozessoren", "url": "https://www.kleinanzeigen.de/s-cpu-prozessor/k0?sort=preis_auf"},
    {"name": "PC Hardware allgemein", "url": "https://www.kleinanzeigen.de/s-pc-hardware/k0?sort=preis_auf"},
]

conn = sqlite3.connect("pc_deals.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS seen 
                (id TEXT PRIMARY KEY, title TEXT, price TEXT, link TEXT, location TEXT, timestamp TEXT)""")

def extract_price(price_text):
    match = re.search(r'(\d{1,6})', price_text.replace('.', '').replace(',', ''))
    return int(match.group(1)) if match else None

def get_deals(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        deals = []
        for ad in soup.select("article.aditem"):
            title_tag = ad.select_one("h2 a")
            price_tag = ad.select_one(".aditem-main--middle--price")
            link_tag = ad.select_one("a")
            location_tag = ad.select_one(".aditem-main--top--left")
            
            if not title_tag or not link_tag: continue
                
            title = title_tag.get_text(strip=True)
            link = "https://www.kleinanzeigen.de" + link_tag["href"]
            price_text = price_tag.get_text(strip=True) if price_tag else "Preis auf Anfrage"
            price = extract_price(price_text)
            location = location_tag.get_text(strip=True) if location_tag else ""
            
            deal_id = hashlib.md5((title + link).encode()).hexdigest()
            
            if conn.execute("SELECT id FROM seen WHERE id=?", (deal_id,)).fetchone():
                continue
                
            deals.append({
                "Kategorie": "Aktuell",
                "Titel": title,
                "Preis": price_text,
                "Preis_Zahl": price,
                "Link": link,
                "Ort": location,
                "Deal-ID": deal_id
            })
        return deals
    except:
        return []

# Sidebar Steuerung
st.sidebar.header("🔍 Filter & Steuerung")

if st.sidebar.button("🔄 Jetzt scannen & neue Deals laden", type="primary"):
    all_new = []
    with st.spinner("Scanne Kleinanzeigen... (kann 20–40 Sekunden dauern)"):
        for s in SEARCHES:
            st.info(f"Suche: {s['name']}")
            new_deals = get_deals(s["url"])
            for d in new_deals:
                all_new.append(d)
                conn.execute("INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?, ?, ?)",
                            (d["Deal-ID"], d["Titel"], d["Preis"], d["Link"], d["Ort"], datetime.now().isoformat()))
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

# Filter (nach dem Scan)
if "deals_df" in st.session_state and not st.session_state.deals_df.empty:
    df = st.session_state.deals_df.copy()
    
    # Preisfilter
    st.sidebar.subheader("💰 Preisfilter")
    min_price = st.sidebar.number_input("Mindestpreis (€)", min_value=0, value=0, step=50)
    max_price = st.sidebar.number_input("Maximalpreis (€)", min_value=0, value=2000, step=50)
    
    # Ortsfilter
    st.sidebar.subheader("📍 Orts- / Entfernungsfilter")
    ort = st.sidebar.text_input("Ort / PLZ (z.B. Berlin, 50667, München)", "")
    entfernung = st.sidebar.number_input("Max. Entfernung in km (ca.-Filter)", min_value=0, value=100, step=10)
    
    # Titel-Suche
    search_term = st.text_input("🔍 Titel durchsuchen")
    
    # Anwenden der Filter
    if min_price > 0 or max_price > 0:
        df = df[(df["Preis_Zahl"].notna()) & 
                (df["Preis_Zahl"] >= min_price) & 
                (df["Preis_Zahl"] <= max_price)]
    
    if ort:
        df = df[df["Ort"].str.contains(ort, case=False, na=False)]
    
    if search_term:
        df = df[df["Titel"].str.contains(search_term, case=False)]
    
    st.success(f"{len(df)} Deals nach Filterung angezeigt")
    
    st.dataframe(
        df[["Kategorie", "Titel", "Preis", "Ort", "Link"]],
        column_config={"Link": st.column_config.LinkColumn("Zur Anzeige")},
        use_container_width=True,
        hide_index=True
    )
    
    csv = df.to_csv(index=False).encode()
    st.download_button("📥 Gefilterte Deals als CSV herunterladen", csv, "pc_deals_gefiltert.csv", "text/csv")
else:
    st.info("Klicke zuerst auf „Jetzt scannen“ um Deals zu laden.")

st.caption("Deine persönliche PC-Deals Website mit Preis- & Ortsfilter – nur neue Angebote von Kleinanzeigen")
