import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

st.set_page_config(page_title="🔥 PC Hardware Deal Scanner", layout="wide", page_icon="💻")
st.title("🔥 Mein PC & Hardware Deal Scanner")
st.markdown("**Persönlicher Kleinanzeigen Deal-Bot** – mit Preis- & Ortsfilter")

SEARCHES = [
    {"name": "Gaming PC Komplettsysteme", "url": "https://www.kleinanzeigen.de/s-gaming-pc/k0?sort=preis_auf"},
    {"name": "Grafikkarten (RTX & Co.)", "url": "https://www.kleinanzeigen.de/s-grafikkarte/k0?sort=preis_auf"},
    {"name": "CPUs / Prozessoren", "url": "https://www.kleinanzeigen.de/s-cpu-prozessor/k0?sort=preis_auf"},
    {"name": "PC Hardware allgemein", "url": "https://www.kleinanzeigen.de/s-pc-hardware/k0?sort=preis_auf"},
]

def extract_price(price_text):
    if not price_text or "Preis auf Anfrage" in price_text:
        return None
    cleaned = re.sub(r'[^0-9.,]', '', price_text)
    match = re.search(r'(\d{1,6})', cleaned.replace(',', '.'))
    return float(match.group(1)) if match else None

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
            
            if not title_tag or not link_tag: 
                continue
                
            title = title_tag.get_text(strip=True)
            link = "https://www.kleinanzeigen.de" + link_tag["href"]
            price_text = price_tag.get_text(strip=True) if price_tag else "Preis auf Anfrage"
            price = extract_price(price_text)
            location = location_tag.get_text(strip=True) if location_tag else ""
            
            deals.append({
                "Kategorie": "Aktuell",
                "Titel": title,
                "Preis_Text": price_text,
                "Preis_Zahl": price,
                "Link": link,
                "Ort": location
            })
        return deals
    except Exception as e:
        st.error(f"Fehler beim Scannen: {e}")
        return []

st.sidebar.header("🔍 Filter & Steuerung")

if st.sidebar.button("🔄 Jetzt scannen & neue Deals laden", type="primary"):
    all_deals = []
    with st.spinner("Scanne Kleinanzeigen..."):
        for s in SEARCHES:
            st.info(f"Suche: {s['name']}")
            new_deals = get_deals(s["url"])
            all_deals.extend(new_deals)
            time.sleep(2)
    
    if all_deals:
        df = pd.DataFrame(all_deals)
        st.session_state.deals_df = df
        st.success(f"{len(all_deals)} Deals gefunden!")
    else:
        st.info("Keine Deals gefunden.")

if "deals_df" in st.session_state and not st.session_state.deals_df.empty:
    df = st.session_state.deals_df.copy()
    
    st.sidebar.subheader("💰 Preisfilter")
    min_price = st.sidebar.number_input("Mindestpreis (€)", min_value=0, value=0, step=50)
    max_price = st.sidebar.number_input("Maximalpreis (€)", min_value=0, value=1500, step=50)
    show_no_price = st.sidebar.checkbox("Auch 'Preis auf Anfrage' und VB anzeigen", value=True)
    
    st.sidebar.subheader("📍 Ortsfilter")
    ort = st.sidebar.text_input("Ort / PLZ (z.B. Eutin, Berlin, 23701)", value="")
    
    search_term = st.text_input("🔍 Titel durchsuchen", value="")
    
    # Filter anwenden
    filtered_df = df.copy()
    if not show_no_price:
        filtered_df = filtered_df[filtered_df["Preis_Zahl"].notna()]
    
    if min_price > 0 or max_price < 2000:
        filtered_df = filtered_df[
            (filtered_df["Preis_Zahl"].isna()) | 
            ((filtered_df["Preis_Zahl"] >= min_price) & (filtered_df["Preis_Zahl"] <= max_price))
        ]
    
    if ort:
        filtered_df = filtered_df[
            filtered_df["Ort"].str.contains(ort, case=False, na=False) | 
            filtered_df["Titel"].str.contains(ort, case=False, na=False)
        ]
    
    if search_term:
        filtered_df = filtered_df[filtered_df["Titel"].str.contains(search_term, case=False)]
    
    st.success(f"{len(filtered_df)} Deals nach Filterung angezeigt")
    
    display_df = filtered_df[["Kategorie", "Titel", "Preis_Text", "Ort", "Link"]].copy()
    display_df = display_df.rename(columns={"Preis_Text": "Preis"})
    
    st.dataframe(
        display_df,
        column_config={"Link": st.column_config.LinkColumn("Zur Anzeige")},
        use_container_width=True,
        hide_index=True
    )
    
    csv = filtered_df.to_csv(index=False).encode()
    st.download_button("📥 Gefilterte Deals als CSV herunterladen", csv, "pc_deals.csv", "text/csv")
else:
    st.info("Klicke auf den roten Button oben, um Deals zu laden.")

st.caption("Stabile Version – Maximalpreis startet bei 1500 €")
