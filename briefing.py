import os
import feedparser
from datetime import date
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. RICORRENZE DI OGGI ---
oggi = date.today()
giorno_oggi = oggi.day
mese_oggi = oggi.month

print(f"Cerco le ricorrenze per il {giorno_oggi}/{mese_oggi}...")
risposta = supabase.table("ricorrenze").select("*").eq("giorno", giorno_oggi).eq("mese", mese_oggi).execute()
ricorrenze_oggi = risposta.data

if ricorrenze_oggi:
    print(f"Trovate {len(ricorrenze_oggi)} ricorrenze per oggi.")
else:
    print("Nessuna ricorrenza trovata per oggi.")

# --- 2. NOTIZIE DAI FEED RSS ---
# Elenco delle fonti da controllare: (nome fonte, indirizzo feed)
FONTI_RSS = [
    ("Il Libraio", "https://www.illibraio.it/feed/"),
    ("ANSA Cultura", "https://www.ansa.it/sito/notizie/cultura/cultura_rss.xml"),
    ("Rai News Spettacolo", "https://www.rainews.it/rss/spettacolo"),
]

# Parole chiave che ci interessano (in minuscolo)
PAROLE_CHIAVE = [
    "libro", "libri", "scrittore", "scrittrice", "autore", "autrice",
    "editoria", "editore", "premio letterario", "narrativa", "romanzo",
    "musica", "musicista", "cantante", "album", "concerto",
    "cinema", "film", "regista", "attore", "attrice", "festival del cinema",
    "morto", "morta", "scomparso", "scomparsa", "anniversario"
]

notizie_rilevanti = []

for nome_fonte, url_feed in FONTI_RSS:
    print(f"Leggo il feed: {nome_fonte}...")
    feed = feedparser.parse(url_feed)

    for articolo in feed.entries[:15]:  # controlliamo solo i 15 articoli più recenti
        titolo = articolo.get("title", "")
        riassunto = articolo.get("summary", "")
        testo_completo = (titolo + " " + riassunto).lower()

        # controlliamo se almeno una parola chiave è presente
        if any(parola in testo_completo for parola in PAROLE_CHIAVE):
            notizie_rilevanti.append({
                "fonte": nome_fonte,
                "titolo": titolo,
                "link": articolo.get("link", "")
            })

print(f"Trovate {len(notizie_rilevanti)} notizie potenzialmente rilevanti.")
for n in notizie_rilevanti:
    print(f"- [{n['fonte']}] {n['titolo']}")
