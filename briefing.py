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

PAROLE_CHIAVE = {
    "morto": 3, "morta": 3, "scomparso": 3, "scomparsa": 3, "lutto": 3,
    "premio strega": 3, "premio letterario": 3, "vince il premio": 3, "nobel": 3,
    "festival": 2, "salone del libro": 2, "fiera del libro": 2,
    "anniversario": 2, "uscita": 2, "presentazione": 2,
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
        punteggio = 0
        for parola, peso in PAROLE_CHIAVE.items():
            if parola in testo_completo:
                punteggio += peso
        if punteggio > 0:
            notizie_rilevanti.append({
                "fonte": nome_fonte,
                "titolo": titolo,
                "link": articolo.get("link", ""),
                "punteggio": punteggio
            })

notizie_rilevanti.sort(key=lambda n: n["punteggio"], reverse=True)
# per l'email teniamo solo le prime 12, altrimenti diventa troppo lunga
notizie_da_mostrare = notizie_rilevanti[:12]
print(f"Trovate {len(notizie_rilevanti)} notizie rilevanti (mostro le prime {len(notizie_da_mostrare)}).")

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

# blocco notizie
html_notizie = ""
for n in notizie_da_mostrare:
    html_notizie += f"""
    <div style="margin-bottom:10px; padding:8px; border-bottom:1px solid #eee;">
        {etichetta_priorita(n['punteggio'])} — <strong>{n['titolo']}</strong><br>
        <span style="font-size:13px; color:#888;">Fonte: {n['fonte']}</span><br>
        <a href="{n['link']}" style="font-size:13px;">Leggi l'articolo →</a>
    </div>
    """
if not notizie_da_mostrare:
    html_notizie = "<p style='color:#888;'>Nessuna notizia rilevante trovata oggi.</p>"

corpo_email = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width:600px; margin:0 auto; color:#222;">
    <h2>📚 Briefing Libreria — {data_leggibile}</h2>

    <h3>📅 Ricorrenze di oggi</h3>
    {html_ricorrenze}

    <h3>📰 Notizie rilevanti (ordinate per priorità)</h3>
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
