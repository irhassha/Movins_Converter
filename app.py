import streamlit as st
import pdfplumber
import datetime
import pandas as pd

# --- FUNGSI CORE: GENERATOR BAP ---
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
        self.segments.append(f"DTM+132:{now.strftime('%Y%m%d%H%M')}:201'")
        self.segments.append("HAN+LOA'")

    def add_slot(self, bay, row, tier, pol, pod, iso_type="2210"):
        coord = f"{int(bay):03d}{int(row):02d}{int(tier):02d}"
        self.segments.append(f"LOC+147+{coord}'")
        self.segments.append("MEA+WT++KGM:00000'") # Default 0
        self.segments.append(f"LOC+9+{pol}'")
        self.segments.append(f"LOC+11+{pod}'")
        self.segments.append("RFF+BM:1'")
        self.segments.append(f"EQD+CN++{iso_type}+++5'")

    def finalize(self):
        count = len(self.segments) - 1
        self.segments.append(f"UNT+{count}+1'")
        self.segments.append("UNZ+1+0'")
        return '\r\n'.join(self.segments)

# --- FUNGSI PARSING PDF (SEDERHANA) ---
def extract_pdf_symbols(uploaded_file):
    # Logika ini perlu disesuaikan dengan posisi grid spesifik di PDF Anda
    # Sebagai contoh, kita ambil semua karakter tunggal/pendek yang ditemukan
    symbolsfound = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Logika simulasi: mencari karakter unik yang sering muncul (X, P, J, K, dsb)
                for word in text.split():
                    if len(word) <= 3 and word.isalpha():
                        symbolsfound.append(word.upper())
    return sorted(list(set(symbolsfound)))

# --- ANTARMUKA STREAMLIT ---
st.set_page_config(page_title="PDF to MOVINS Converter", layout="wide")
st.title("🚢 PDF to MOVINS (.BAP) Converter")
st.write("Upload PDF Stowage Plan untuk diconvert menjadi format EDIFACT MOVINS.")

with st.sidebar:
    st.header("Informasi Kapal")
    vessel = st.text_input("Nama Kapal", "EVER BLINK")
    voyage = st.text_input("Voyage", "1170-077A")
    pol = st.text_input("Port of Loading", "IDJKT")

uploaded_file = st.file_uploader("Pilih file PDF Stowage Plan", type=["pdf"])

if uploaded_file:
    # 1. Ekstraksi Simbol
    st.info("Menganalisis simbol di PDF...")
    detected_symbols = extract_pdf_symbols(uploaded_file)
    
    st.subheader("🛠 Validasi Mapping Port")
    st.write("Tentukan UNLOCODE (5 Huruf) untuk setiap simbol yang ditemukan di PDF.")
    
    # 2. Form Validasi User
    mapping_data = {}
    col1, col2 = st.columns(2)
    
    for i, symbol in enumerate(detected_symbols):
        with col1 if i % 2 == 0 else col2:
            mapping_data[symbol] = st.text_input(f"POD untuk Simbol '{symbol}':", 
                                                placeholder="Contoh: MYPTP", 
                                                key=f"sym_{symbol}")

    if st.button("Generate File BAP"):
        # 3. Proses Pembuatan File
        # (Dalam aplikasi nyata, koordinat bay/row/tier diambil dari posisi grid di PDF)
        # Di bawah ini adalah simulasi data koordinat
        gen = BapGenerator(vessel, voyage, pol)
        
        # Contoh simulasi loop data (nanti diintegrasikan dengan koordinat PDF asli)
        # Di sini kita hanya mendemonstrasikan hasil mapping
        dummy_data = [
            {"bay": "01", "row": "08", "tier": "82", "sym": detected_symbols[0] if detected_symbols else "X"}
        ]
        
        for item in dummy_data:
            pod_target = mapping_data.get(item['sym'], "UNKNOWN")
            gen.add_slot(item['bay'], item['row'], item['tier'], pol, pod_target)
        
        bap_content = gen.finalize()
        
        st.success("File Berhasil Dibuat!")
        st.download_button(
            label="Download .BAP File",
            data=bap_content,
            file_name=f"MOVINS_{vessel}_{voyage}.BAP",
            mime="application/octet-stream"
        )
        
        st.code(bap_content, language='text')
