import os
import feedparser
import resend
from datetime import date
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
resend.api_key = os.environ["RESEND_API_KEY"]
EMAIL_DESTINATARIO = os.environ["EMAIL_DESTINATARIO"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 1. RICORRENZE DI OGGI ---
oggi = date.today()
giorno_oggi = oggi.day
mese_oggi = oggi.month
data_leggibile = oggi.strftime("%d/%m/%Y")

print(f"Cerco le ricorrenze per il {giorno_oggi}/{mese_oggi}...")
risposta = supabase.table("ricorrenze").select("*").eq("giorno", giorno_oggi).eq("mese", mese_oggi).execute()
ricorrenze_oggi = risposta.data
print(f"Trovate {len(ricorrenze_oggi)} ricorrenze per oggi.")

# --- 2. NOTIZIE DAI FEED RSS ---
FONTI_RSS = [
    ("Il Libraio", "https://www.illibraio.it/feed/"),
    ("ANSA Cultura", "https://www.ansa.it/sito/notizie/cultura/cultura_rss.xml"),
    ("Rai News Spettacolo", "https://www.rainews.it/rss/spettacolo"),
]

# Parole di "urgenza": quanto è importante/urgente la notizia (per il punteggio)
URGENZA = {
    "morto": 3, "morta": 3, "scomparso": 3, "scomparsa": 3, "lutto": 3,
    "premio strega": 3,"premio campiello": 3,"premio bancarella": 3, 
    "premio letterario": 3, "vince il premio": 3, "nobel": 3,
    "festival": 2, "salone del libro": 2, "fiera del libro": 2,
    "anniversario": 2, "uscita": 2, "presentazione": 2,
}

# Parole di "argomento generico": indicano solo il tema, peso basso
ARGOMENTO_GENERICO = {
    "libro": 1, "libri": 1, "scrittore": 1, "scrittrice": 1,
    "autore": 1, "autrice": 1, "editoria": 1, "editore": 1,
}

# Parole per assegnare la MACRO-SEZIONE (categoria libreria)
CATEGORIE = {
    "Narrativa": [
        "narrativa", "romanzo", "racconto", "poesia", "poeta", "poetessa",
        "teatro", "commedia", "dramma", "giallo", "thriller", "noir",
        "fantascienza", "fantasy", "classico", "classici", "letteratura latina",
        "letteratura greca", "epica", "romanzo storico", "romanzo rosa", "racconti",
        "narrativa straniera", "distopia", "post-apocalittico", "horror", "gotico",
        "spionaggio", "romanzo di formazione", "letteratura italiana", "letteratura straniera"
    ],
    "Saggistica": [
        "saggio", "saggistica", "storia antica", "storia medievale",
        "storia moderna", "storia contemporanea", "geopolitica", "attualità",
        "sociologia", "psicologia", "scienza", "scienze", "filosofia",
        "religione", "spiritualità", "crescita personale", "miglioramento personale",
        "filosofia orientale", "pedagogia", "educazione", "economia", "marketing", 
        "management", "finanza", "economia politica", "diritto", "giurisprudenza", 
        "politica", "teoria politica", "comunicazione", "antropologia", "etnografia", 
        "media", "giornalismo", "disinformazione", "ecologia", "intelligenza artificiale", 
        "informatica", "biografia", "autobiografia", "memorie", "diario", "epistolario", 
        "critica letteraria", "saggistica letteraria", "arte", "storia dell'arte", 
        "architettura", "scienze cognitive", "matematica", "astronomia", "neuroscienze"
    ],
    "Bambini": [
        "bambini", "bambino", "bambina", "ragazzi", "ragazzo", "ragazza",
        "young adult", "fiaba", "fiabe", "romance", "adolescenti", "adolescente",
        "albi illustrati", "albo illustrato", "prime letture", "letture graduate", 
        "libro illustrato", "picture book", "libro gioco", "libri giochi", "fumetto per ragazzi"
        "young adult fiction"
     ],
    "Manga e Comics": [
        "manga", "fumetto", "fumetti", "comic", "comics", "graphic novel",
        "romanzo grafico", "bande dessinée", "bd","albo", "spillato", "volume", "tankobon",
        "shonen", "shojo", "seinen", "josei", "kodomo","anime", "otaku", "mangaka",
        "supereroi", "superhero", "marvel", "dc comics","bonelli", "dylan dog", 
        "tex", "zagor", "webtoon", "manhwa", "manhua","strisce", "strip", "cartoon"
    ],
    "Varie": [
        "sport", "turismo", "viaggio", "viaggi", "cucina", "ricette", "ricetta",
        "alimentazione", "hobby", "hobbies", "tempo libero", "benessere",
        "mente e corpo", "wellness", "guide", "guida", "fai da te", "giardinaggio", 
        "orto", "animali", "pet", "salute", "fitness", "mindfulness", "meditazione",
        "fotografia", "enogastronomia", "fotografia", "moda", "design", "collezionismo"
    ],
    "Musica e Cinema": [
        "musica", "musicista", "cantante", "album", "concerto", "compositore",
        "cinema", "film", "regista", "attore", "attrice", "colonna sonora",
        "discografia", "teoria musicale", "storia della musica", "storia del cinema", 
        "cinematografia", "critica cinematografica", "sceneggiatura", "documentario", 
        "serie tv", "televisione", "soundtrack", "performing arts"
    ],
}

ORDINE_CATEGORIE = ["Narrativa", "Saggistica", "Bambini", "Manga e Comics", "Varie", "Musica e Cinema"]

notizie_rilevanti = []

for nome_fonte, url_feed in FONTI_RSS:
    print(f"Leggo il feed: {nome_fonte}...")
    feed = feedparser.parse(url_feed)
    for articolo in feed.entries[:15]:
        titolo = articolo.get("title", "")
        riassunto = articolo.get("summary", "")
        testo_completo = (titolo + " " + riassunto).lower()

        # punteggio di urgenza/importanza
        punteggio = 0
        for parola, peso in URGENZA.items():
            if parola in testo_completo:
                punteggio += peso
        for parola, peso in ARGOMENTO_GENERICO.items():
            if parola in testo_completo:
                punteggio += peso

        # capiamo a quale categoria appartiene: contiamo i match per categoria
        conteggio_categorie = {}
        for nome_categoria, parole in CATEGORIE.items():
            conteggio = sum(1 for p in parole if p in testo_completo)
            if conteggio > 0:
                conteggio_categorie[nome_categoria] = conteggio

        if conteggio_categorie:
            # prendiamo la categoria con più corrispondenze
            categoria_assegnata = max(conteggio_categorie, key=conteggio_categorie.get)
        elif punteggio > 0:
            # ha un punteggio di urgenza ma nessuna categoria specifica -> Varie
            categoria_assegnata = "Varie"
        else:
            categoria_assegnata = None

        if categoria_assegnata:
            notizie_rilevanti.append({
                "fonte": nome_fonte,
                "titolo": titolo,
                "link": articolo.get("link", ""),
                "punteggio": punteggio,
                "categoria": categoria_assegnata
            })

print(f"Trovate {len(notizie_rilevanti)} notizie rilevanti in totale.")

# --- 3. COSTRUZIONE DELL'EMAIL HTML ---

def etichetta_priorita(punteggio):
    if punteggio >= 5:
        return "🔴 ALTA"
    elif punteggio >= 2:
        return "🟡 media"
    else:
        return "⚪ bassa"

# blocco ricorrenze
html_ricorrenze = ""
if ricorrenze_oggi:
    for r in ricorrenze_oggi:
        html_ricorrenze += f"""
        <div style="margin-bottom:12px; padding:10px; background:#fff8e1; border-left:4px solid #f5a623;">
            <strong>{r['titolo']}</strong> <span style="color:#888;">({r['categoria']})</span><br>
            <span style="font-size:14px;">{r.get('descrizione') or ''}</span><br>
            <em style="font-size:13px; color:#555;">💡 Azione suggerita: {r.get('azione_suggerita') or '-'}</em>
        </div>
        """
else:
    html_ricorrenze = "<p style='color:#888;'>Nessuna ricorrenza registrata per oggi.</p>"

# blocco notizie, raggruppate per categoria
html_notizie = ""
for nome_categoria in ORDINE_CATEGORIE:
    notizie_categoria = [n for n in notizie_rilevanti if n["categoria"] == nome_categoria]
    if not notizie_categoria:
        continue
    # ordiniamo per priorità dentro la categoria
    notizie_categoria.sort(key=lambda n: n["punteggio"], reverse=True)
    # limitiamo a 8 notizie per sezione, per non rendere l'email troppo lunga
    notizie_categoria = notizie_categoria[:8]

    html_notizie += f"<h3 style='margin-top:24px;'>📖 {nome_categoria}</h3>"
    for n in notizie_categoria:
        html_notizie += f"""
        <div style="margin-bottom:10px; padding:8px; border-bottom:1px solid #eee;">
            {etichetta_priorita(n['punteggio'])} — <strong>{n['titolo']}</strong><br>
            <span style="font-size:13px; color:#888;">Fonte: {n['fonte']}</span><br>
            <a href="{n['link']}" style="font-size:13px;">Leggi l'articolo →</a>
        </div>
        """

if not notizie_rilevanti:
    html_notizie = "<p style='color:#888;'>Nessuna notizia rilevante trovata oggi.</p>"

corpo_email = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width:600px; margin:0 auto; color:#222;">
    <h2>📚 Briefing Libreria — {data_leggibile}</h2>

    <h3>📅 Ricorrenze di oggi</h3>
    {html_ricorrenze}

    <h3 style="margin-top:28px; border-top:2px solid #333; padding-top:10px;">📰 Notizie per sezione</h3>
    {html_notizie}

    <hr>
    <p style="font-size:12px; color:#aaa;">Briefing generato automaticamente ogni giorno.</p>
</body>
</html>
"""

# --- 4. INVIO EMAIL TRAMITE RESEND ---
params = {
    "from": "onboarding@resend.dev",
    "to": [EMAIL_DESTINATARIO],
    "subject": f"📚 Briefing Libreria - {data_leggibile}",
    "html": corpo_email,
}

email_inviata = resend.Emails.send(params)
print("Email inviata! ID:", email_inviata)
