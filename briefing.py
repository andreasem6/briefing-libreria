import os
from datetime import date
import feedparser
import resend
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
resend.api_key = os.environ["RESEND_API_KEY"]
EMAIL_DESTINATARIO = os.environ["EMAIL_DESTINATARIO"]
CRON_ATTIVO = os.environ.get("RUN_CRON", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

oggi = date.today()
giorno_oggi = oggi.day
mese_oggi = oggi.month
data_leggibile = oggi.strftime("%d/%m/%Y")

E_MATTINA = (CRON_ATTIVO == "0 5 * * *") or (CRON_ATTIVO == "")

# --- 1. RICORRENZE DI OGGI (solo nell'invio del mattino) ---
ricorrenze_oggi = []
if E_MATTINA:
    print(f"Cerco le ricorrenze per il {giorno_oggi}/{mese_oggi}...")
    risposta = supabase.table("ricorrenze").select("*").eq("giorno", giorno_oggi).eq("mese", mese_oggi).execute()
    ricorrenze_oggi = risposta.data
    print(f"Trovate {len(ricorrenze_oggi)} ricorrenze per oggi.")
else:
    print("Non e' l'invio del mattino: salto le ricorrenze (gia' inviate stamattina).")

# --- 2. NOTIZIE DAI FEED RSS ---
FONTI_RSS = [
    ("Il Libraio", "https://www.illibraio.it/feed/"),
    ("ANSA Cultura", "https://www.ansa.it/sito/notizie/cultura/cultura_rss.xml"),
    ("ANSA Cinema", "https://www.ansa.it/sito/notizie/cultura/cinema/cinema_rss.xml"),
    ("Rai News Spettacolo", "https://www.rainews.it/rss/spettacolo"),
    ("Corriere della Sera - Cultura", "https://xml2.corriereobjects.it/rss/cultura.xml"),
    ("La Repubblica - Cultura", "https://www.repubblica.it/rss/cultura/rss2.0.xml"),
    ("Il Sole 24 Ore - Cultura", "https://www.ilsole24ore.com/rss/cultura.xml"),
    ("Rolling Stone Italia", "https://www.rollingstone.it/feed/"),
    ("Ciak Magazine", "https://www.ciakmagazine.it/feed/"),
    ("Gruppo Mondadori (sperimentale)", "https://www.gruppomondadori.it/feed"),
    ("Internazionale", "http://www.internazionale.it/sitemaps/rss.xml"),
]

URGENZA = {
    "morto": 3, "morta": 3, "scomparso": 3, "scomparsa": 3, "lutto": 3,
    "premio strega": 3, "premio campiello": 3, "premio bancarella": 3,
    "premio letterario": 3, "vince il premio": 3, "nobel": 3,
    "festival": 2, "salone del libro": 2, "fiera del libro": 2,
    "anniversario": 2, "uscita": 2, "presentazione": 2,
}

ARGOMENTO_GENERICO = {
    "libro": 1, "libri": 1, "scrittore": 1, "scrittrice": 1,
    "autore": 1, "autrice": 1, "editoria": 1, "editore": 1,
}

# Ogni categoria ha parole "forti" (peso 2, molto specifiche di quella
# categoria) e parole "deboli" (peso 1, che possono comparire anche in
# articoli di altre categorie). Questo evita che parole generiche come
# "biografia" facciano vincere la categoria sbagliata.
CATEGORIE = {
    "Narrativa": {
        "romanzo": 2, "poesia": 2, "poeta": 2, "poetessa": 2, "teatro": 2,
        "commedia": 2, "dramma": 2, "giallo": 2, "thriller": 2, "noir": 2,
        "fantascienza": 2, "fantasy": 2, "romanzo storico": 2, "romanzo rosa": 2,
        "narrativa straniera": 2, "distopia": 2, "horror": 2, "gotico": 2,
        "spionaggio": 2, "romanzo di formazione": 2,
        "premio strega": 2, "premio campiello": 2, "premio bancarella": 2,
        "vincitore premio strega": 2, "finalista premio strega": 2,
        "vincitore premio nobel letteratura": 2, "vincitrice premio nobel letteratura": 2,
        "narrativa": 1, "racconto": 1, "classico": 1, "classici": 1,
        "letteratura latina": 1, "letteratura greca": 1, "epica": 1, "racconti": 1,
        "post-apocalittico": 1, "letteratura italiana": 1, "letteratura straniera": 1,
    },
    "Saggistica": {
        "saggio": 2, "saggistica": 2, "storia antica": 2, "storia medievale": 2,
        "storia moderna": 2, "storia contemporanea": 2, "geopolitica": 2,
        "sociologia": 2, "psicologia": 2, "filosofia": 2, "pedagogia": 2,
        "economia politica": 2, "giurisprudenza": 2, "teoria politica": 2,
        "antropologia": 2, "scienze cognitive": 2, "neuroscienze": 2,
        "critica letteraria": 2, "storia dell'arte": 2,
        "attualità": 1, "scienza": 1, "scienze": 1, "religione": 1,
        "spiritualità": 1, "crescita personale": 1, "miglioramento personale": 1,
        "filosofia orientale": 1, "educazione": 1, "economia": 1, "marketing": 1,
        "management": 1, "finanza": 1, "diritto": 1, "politica": 1,
        "comunicazione": 1, "etnografia": 1, "media": 1, "giornalismo": 1,
        "disinformazione": 1, "ecologia": 1, "intelligenza artificiale": 1,
        "informatica": 1, "biografia": 1, "autobiografia": 1, "memorie": 1,
        "diario": 1, "epistolario": 1, "saggistica letteraria": 1, "arte": 1,
        "architettura": 1, "matematica": 1, "astronomia": 1,
    },
    "Bambini": {
        "bambini": 2, "bambino": 2, "bambina": 2, "young adult": 2,
        "fiaba": 2, "fiabe": 2, "albo illustrato": 2, "albi illustrati": 2,
        "picture book": 2, "libro illustrato": 2, "young adult fiction": 2,
        "libri per ragazzi": 2, "letteratura per ragazzi": 2,
        "ragazzi": 1, "ragazzo": 1, "ragazza": 1, "romance": 1,
        "adolescenti": 1, "adolescente": 1, "prime letture": 1,
        "letture graduate": 1, "libro gioco": 1, "libri giochi": 1,
        "fumetto per ragazzi": 1,
    },
    "Manga e Comics": {
        "manga": 2, "fumetto": 2, "fumetti": 2, "comic": 2, "comics": 2,
        "graphic novel": 2, "romanzo grafico": 2, "tankobon": 2,
        "shonen": 2, "shojo": 2, "seinen": 2, "josei": 2, "mangaka": 2,
        "webtoon": 2, "manhwa": 2, "manhua": 2,
        "bande dessinée": 1, "bd": 1, "albo": 1, "spillato": 1, "volume": 1,
        "kodomo": 1, "anime": 1, "otaku": 1, "supereroi": 1, "superhero": 1,
        "marvel": 1, "dc comics": 1, "bonelli": 1, "dylan dog": 1, "tex": 1,
        "zagor": 1, "strisce": 1, "strip": 1, "cartoon": 1,
    },
    "Varie": {
        "sport": 2, "turismo": 2, "cucina": 2, "ricette": 2, "ricetta": 2,
        "giardinaggio": 2, "enogastronomia": 2, "collezionismo": 2,
        "viaggio": 1, "viaggi": 1, "alimentazione": 1, "hobby": 1,
        "hobbies": 1, "tempo libero": 1, "benessere": 1, "mente e corpo": 1,
        "wellness": 1, "guide": 1, "guida": 1, "fai da te": 1, "orto": 1,
        "animali": 1, "pet": 1, "salute": 1, "fitness": 1, "mindfulness": 1,
        "meditazione": 1, "fotografia": 1, "moda": 1, "design": 1,
    },
    "Musica e Cinema": {
        "musicista": 2, "cantante": 2, "regista": 2, "attore": 2, "attrice": 2,
        "colonna sonora": 2, "concerto": 2, "album": 2, "compositore": 2,
        "sceneggiatura": 2, "cinematografia": 2, "critica cinematografica": 2,
        "discografia": 2,
        "musica": 1, "cinema": 1, "film": 1, "storia della musica": 1,
        "storia del cinema": 1, "documentario": 1, "serie tv": 1,
        "televisione": 1, "soundtrack": 1, "performing arts": 1,
        "teoria musicale": 1,
    },
}

ORDINE_CATEGORIE = ["Narrativa", "Saggistica", "Bambini", "Manga e Comics", "Varie", "Musica e Cinema"]

FONTE_CATEGORIA_DEFAULT = {
    "Ciak Magazine": "Musica e Cinema",
    "Rolling Stone Italia": "Musica e Cinema",
    "ANSA Cinema": "Musica e Cinema",
    "Rai News Spettacolo": "Musica e Cinema",
}
BONUS_FONTE_SPECIALIZZATA = 3

gia_inviate_oggi = supabase.table("notizie_giornaliere").select("link").eq("data_pubblicazione", oggi.isoformat()).execute()
link_gia_inviati = set(r["link"] for r in gia_inviate_oggi.data if r["link"])
print(f"Notizie gia' inviate oggi in precedenti aggiornamenti: {len(link_gia_inviati)}")

notizie_rilevanti = []
link_visti_in_questo_giro = set()  # evita duplicati DENTRO lo stesso invio

for nome_fonte, url_feed in FONTI_RSS:
    print(f"Leggo il feed: {nome_fonte}...")
    feed = feedparser.parse(url_feed)
    for articolo in feed.entries[:20]:
        link = articolo.get("link", "")

        if link and link in link_gia_inviati:
            continue

        chiave_duplicato = link or articolo.get("title", "")
        if chiave_duplicato in link_visti_in_questo_giro:
            continue
        link_visti_in_questo_giro.add(chiave_duplicato)

        pubblicato_oggi = False
        if hasattr(articolo, "published_parsed") and articolo.published_parsed:
            data_articolo = date(*articolo.published_parsed[:3])
            pubblicato_oggi = (data_articolo == oggi)
        if not pubblicato_oggi:
            continue

        titolo = articolo.get("title", "")
        riassunto = articolo.get("summary", "")
        testo_completo = (titolo + " " + riassunto).lower()

        punteggio = 0
        for parola, peso in URGENZA.items():
            if parola in testo_completo:
                punteggio += peso
        for parola, peso in ARGOMENTO_GENERICO.items():
            if parola in testo_completo:
                punteggio += peso

        conteggio_categorie = {}
        for nome_categoria, parole_pesi in CATEGORIE.items():
            punti_categoria = sum(peso for parola, peso in parole_pesi.items() if parola in testo_completo)
            if punti_categoria > 0:
                conteggio_categorie[nome_categoria] = punti_categoria

        categoria_naturale = FONTE_CATEGORIA_DEFAULT.get(nome_fonte)
        if categoria_naturale:
            conteggio_categorie[categoria_naturale] = conteggio_categorie.get(categoria_naturale, 0) + BONUS_FONTE_SPECIALIZZATA

        if conteggio_categorie:
            categoria_assegnata = max(conteggio_categorie, key=conteggio_categorie.get)
        elif punteggio > 0:
            categoria_assegnata = "Varie"
        else:
            categoria_assegnata = None

        if categoria_assegnata:
            notizie_rilevanti.append({
                "fonte": nome_fonte,
                "titolo": titolo,
                "link": link,
                "punteggio": punteggio,
                "categoria": categoria_assegnata
            })

print(f"Trovate {len(notizie_rilevanti)} notizie NUOVE di oggi (non ancora inviate).")

c_e_qualcosa_da_mandare = bool(ricorrenze_oggi) or bool(notizie_rilevanti)

if not c_e_qualcosa_da_mandare:
    print("Nessuna ricorrenza e nessuna notizia nuova: non mando email in questo aggiornamento.")
else:
    def etichetta_priorita(punteggio):
        if punteggio >= 5:
            return "🔴 ALTA"
        elif punteggio >= 2:
            return "🟡 media"
        else:
            return "⚪ bassa"

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

    html_notizie = ""
    for nome_categoria in ORDINE_CATEGORIE:
        notizie_categoria = [n for n in notizie_rilevanti if n["categoria"] == nome_categoria]
        if not notizie_categoria:
            continue
        notizie_categoria.sort(key=lambda n: n["punteggio"], reverse=True)
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

    sezioni_html = ""
    if html_ricorrenze:
        sezioni_html += f"<h3>📅 Ricorrenze di oggi</h3>{html_ricorrenze}"
    if html_notizie:
        sezioni_html += f"<h3 style='margin-top:28px; border-top:2px solid #333; padding-top:10px;'>📰 Notizie nuove</h3>{html_notizie}"
    else:
        sezioni_html += "<p style='color:#888;'>Nessuna notizia nuova rispetto agli aggiornamenti precedenti di oggi.</p>"

    corpo_email = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width:600px; margin:0 auto; color:#222;">
        <h2>📚 Briefing Libreria — {data_leggibile}</h2>
        {sezioni_html}
        <hr>
        <p style="font-size:12px; color:#aaa;">Briefing generato automaticamente.</p>
    </body>
    </html>
    """

    params = {
        "from": "onboarding@resend.dev",
        "to": [EMAIL_DESTINATARIO],
        "subject": f"📚 Briefing Libreria - {data_leggibile}",
        "html": corpo_email,
    }
    email_inviata = resend.Emails.send(params)
    print("Email inviata! ID:", email_inviata)

if notizie_rilevanti:
    righe_da_salvare = [
        {
            "data_pubblicazione": oggi.isoformat(),
            "fonte": n["fonte"],
            "titolo": n["titolo"],
            "link": n["link"],
            "categoria": n["categoria"],
            "punteggio": n["punteggio"],
        }
        for n in notizie_rilevanti
    ]
    supabase.table("notizie_giornaliere").insert(righe_da_salvare).execute()
    print(f"Salvate {len(righe_da_salvare)} notizie nello storico Supabase.")
