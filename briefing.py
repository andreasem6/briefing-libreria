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
FONTI_RSS = [
    ("Il Libraio", "https://www.illibraio.it/feed/"),
    ("ANSA Cultura", "https://www.ansa.it/sito/notizie/cultura/cultura_rss.xml"),
    ("Rai News Spettacolo", "https://www.rainews.it/rss/spettacolo"),
]

# Parole chiave con un "peso": più alto = più importante/urgente
PAROLE_CHIAVE = {
    # eventi urgenti/rari -> peso alto
    "morto": 3, "morta": 3, "scomparso": 3, "scomparsa": 3, "lutto": 3,
    "premio strega": 3, "premio letterario": 3, "vince il premio": 3,
    "nobel": 3,
    # eventi importanti ma meno urgenti -> peso medio
    "festival": 2, "salone del libro": 2, "fiera del libro": 2,
    "anniversario": 2, "uscita": 2, "presentazione": 2,
    # argomento generico -> peso basso (serve solo a far capire il tema)
    "libro": 1, "libri": 1, "scrittore": 1, "scrittrice": 1,
    "autore": 1, "autrice": 1, "editoria": 1, "editore": 1,
    "narrativa": 1, "romanzo": 1,
    "musica": 1, "musicista": 1, "cantante": 1, "album": 1, "concerto": 1,
    "cinema": 1, "film": 1, "regista": 1, "attore": 1, "attrice": 1,
}

notizie_rilevanti = []

for nome_fonte, url_feed in FONTI_RSS:
    print(f"Leggo il feed: {nome_fonte}...")
    feed = feedparser.parse(url_feed)

    for articolo in feed.entries[:15]:
        titolo = articolo.get("title", "")
        riassunto = articolo.get("summary", "")
        testo_completo = (titolo + " " + riassunto).lower()

        # calcoliamo il punteggio sommando i pesi di ogni parola chiave trovata
        punteggio = 0
        parole_trovate = []
        for parola, peso in PAROLE_CHIAVE.items():
            if parola in testo_completo:
                punteggio += peso
                parole_trovate.append(parola)

        if punteggio > 0:
            notizie_rilevanti.append({
                "fonte": nome_fonte,
                "titolo": titolo,
                "link": articolo.get("link", ""),
                "punteggio": punteggio,
                "parole_trovate": parole_trovate
            })

# ordiniamo dal punteggio più alto al più basso
notizie_rilevanti.sort(key=lambda n: n["punteggio"], reverse=True)

print(f"Trovate {len(notizie_rilevanti)} notizie rilevanti, ordinate per priorità:")
for n in notizie_rilevanti:
    # etichetta visiva in base al punteggio
    if n["punteggio"] >= 5:
        etichetta = "🔴 ALTA priorità"
    elif n["punteggio"] >= 2:
        etichetta = "🟡 media priorità"
    else:
        etichetta = "⚪ bassa priorità"
    print(f"{etichetta} ({n['punteggio']} pt) - [{n['fonte']}] {n['titolo']}")
