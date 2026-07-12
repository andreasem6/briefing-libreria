import os
from datetime import date
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
# SUPABASE_URL e SUPABASE_KEY non sono scritte qui per sicurezza:
# le leggiamo da "variabili d'ambiente" che imposteremo su GitHub nello step successivo
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Prendiamo la data di oggi
oggi = date.today()
giorno_oggi = oggi.day
mese_oggi = oggi.month

print(f"Cerco le ricorrenze per il {giorno_oggi}/{mese_oggi}...")

# Chiediamo a Supabase: "dammi tutte le righe della tabella ricorrenze
# dove giorno = oggi e mese = oggi"
risposta = supabase.table("ricorrenze").select("*").eq("giorno", giorno_oggi).eq("mese", mese_oggi).execute()

ricorrenze_oggi = risposta.data

if ricorrenze_oggi:
    print(f"Trovate {len(ricorrenze_oggi)} ricorrenze per oggi:")
    for r in ricorrenze_oggi:
        print(f"- {r['titolo']} (categoria: {r['categoria']}, priorità: {r['priorita']})")
else:
    print("Nessuna ricorrenza trovata per oggi.")
