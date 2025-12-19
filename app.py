import streamlit as st
import pdfplumber
import datetime
import pandas as pd

class BapGenerator:
    def __init__(self, vessel_name, voyage, pol):
        self.segments = []
        now = datetime.datetime.now()
        self.segments.append(f"UNB+UNOA:1+IDP000026+EMC+{now.strftime('%y%m%d:%H%M')}+0+++++'")
        self.segments.append("UNH+1+MOVINS:S:93A:UN:SMDG20'")
        self.segments.append("BGM++0+9'")
        self.segments.append(f"DTM+137:{now.strftime('%Y%m%d%H%M')}:201'")
        self.segments.append(f"TDT+20+{voyage}+++:172:20+++BKLU:103::{vessel_name}'")
        self.segments.append(f"LOC+5+{pol}:139:6'")

    def add_slot(self, bay, row, tier, pol, pod):
        # Format 7 digit: BBBRRTT
        coord = f"{int(bay):03d}{int(row):02d}{int(tier):02d}"
        self.segments.append(f"LOC+147+{coord}'")
        self.segments.append("MEA+WT++KGM:00000'") 
        self.segments.append(f"LOC+9+{pol}'")
        self.segments.append(f"LOC+11+{pod}'")
        self.segments.append("RFF+BM:1'")
        self.segments.append("EQD+CN++2210+++5'")

    def finalize(self):
        count = len(self.segments) - 1
        self.segments.append(f"UNT+{count}+1'")
        self.segments.append("UNZ+1+0'")
        return '\r\n'.join(self.segments)

def parse_pdf_to_slots(uploaded_file, page_index, mapping):
    slots = []
    trash = ["NO", "X", "POL", "BAY", "VOY", "DATE", "PAGE"]
    
    with pdfplumber.open(uploaded_file) as pdf:
        page = pdf.pages[page_index]
        width = page.width
        height = page.height
        words = page.extract_words()
        
        for w in words:
            txt = w['text'].strip().upper()
            clean_txt = txt[0] if (len(txt) <= 4 and txt.isalpha()) else ""
            
            # Jika simbol ada di mapping yang diisi user
            if clean_txt in mapping and mapping[clean_txt].strip() != "":
                # ESTIMASI KOORDINAT (LOGIKA SEDERHANA)
                # Row: Dihitung dari posisi horizontal (x0)
                # Tier: Dihitung dari posisi vertikal (top)
                
                # Ini perlu kalibrasi sesuai PDF Anda:
                estimated_row = int((w['x0'] / width) * 20) # Asumsi max 20 rows
                estimated_tier = 80 + int((1 - (w['top'] / height)) * 20) # Asumsi Tier On-Deck mulai 82
                
                slots.append({
                    "sym": clean_txt,
                    "pod": mapping[clean_txt],
                    "bay": "001", # Idealnya ditarik dari judul BAY di PDF
                    "row": estimated_row,
                    "tier": estimated_tier
                })
    return slots

# --- UI STREAMLIT ---
st.title("🚢 BAP Generator (Auto-Location)")

with st.sidebar:
    v_name = st.text_input("Vessel", "EVER BLINK")
    v_voy = st.text_input("Voyage", "1170-077A")
    v_pol = st.text_input("POL", "IDJKT")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file:
    # 1. Identifikasi simbol unik dulu
    all_words = []
    with pdfplumber.open(uploaded_file) as pdf:
        for w in pdf.pages[0].extract_words():
            t = w['text'].strip().upper()
            if len(t) == 1 and t.isalpha() and t not in ["X", "N"]: all_words.append(t)
    
    unique_syms = sorted(list(set(all_words)))
    
    st.subheader("Mapping & Summary")
    mapping = {}
    cols = st.columns(len(unique_syms) if unique_syms else 1)
    for i, s in enumerate(unique_syms):
        mapping[s] = cols[i].text_input(f"POD {s}", key=f"m_{s}").upper()

    if st.button("Generate .BAP"):
        # Ambil data slot berdasarkan posisi
        final_slots = parse_pdf_to_slots(uploaded_file, 0, mapping)
        
        if not final_slots:
            st.error("Tidak ada data untuk diproses.")
        else:
            gen = BapGenerator(v_name, v_voy, v_pol)
            for s in final_slots:
                gen.add_slot(s['bay'], s['row'], s['tier'], v_pol, s['pod'])
            
            output = gen.finalize()
            st.success(f"Berhasil generate {len(final_slots)} container dengan lokasi berbeda.")
            st.download_button("Download", output, "output.BAP")
            st.text_area("Preview", output)
