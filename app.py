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
        self.segments.append("HAN+LOA'")

    def add_slot(self, bay, row, tier, pol, pod, iso_type="2210"):
        coord = f"{int(bay):03d}{int(row):02d}{int(tier):02d}"
        self.segments.append(f"LOC+147+{coord}'")
        self.segments.append("MEA+WT++KGM:00000'") 
        self.segments.append(f"LOC+9+{pol}'")
        self.segments.append(f"LOC+11+{pod}'")
        self.segments.append("RFF+BM:1'")
        self.segments.append(f"EQD+CN++{iso_type}+++5'")

    def finalize(self):
        count = len(self.segments) - 1
        self.segments.append(f"UNT+{count}+1'")
        self.segments.append("UNZ+1+0'")
        return '\r\n'.join(self.segments)

# --- FUNGSI PARSING PDF (BERDASARKAN HALAMAN PILIHAN) ---
def get_pdf_info(uploaded_file):
    """Fungsi untuk mengambil info jumlah halaman dan deteksi Bay"""
    pages_info = []
    with pdfplumber.open(uploaded_file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            # Mencoba mencari nomor Bay di teks (Contoh: "BAY 21")
            bay_label = f"Halaman {i+1}"
            if text:
                for line in text.split('\n'):
                    if "BAY" in line.upper():
                        bay_label = f"{line.strip()} (Hal {i+1})"
                        break
            pages_info.append({"index": i, "label": bay_label})
    return pages_info

def extract_symbols_from_selected_pages(uploaded_file, selected_page_indices):
    symbols_found = []
    with pdfplumber.open(uploaded_file) as pdf:
        for idx in selected_page_indices:
            page = pdf.pages[idx]
            text = page.extract_text()
            if text:
                for word in text.split():
                    # Membersihkan simbol (hanya ambil yang penting)
                    clean_word = "".join(filter(str.isalpha, word.upper()))
                    if 0 < len(clean_word) <= 3:
                        symbols_found.append(clean_word)
    return sorted(list(set(symbols_found)))

# --- ANTARMUKA STREAMLIT ---
st.set_page_config(page_title="PDF to MOVINS", layout="wide")
st.title("🚢 PDF to MOVINS Converter")

with st.sidebar:
    st.header("1. Informasi Kapal")
    vessel = st.text_input("Nama Kapal", "EVER BLINK")
    voyage = st.text_input("Voyage", "1170-077A")
    pol = st.text_input("Port of Loading", "IDJKT")

uploaded_file = st.file_uploader("2. Upload PDF Stowage Plan", type=["pdf"])

if uploaded_file:
    # Ambil info halaman
    pdf_pages = get_pdf_info(uploaded_file)
    page_options = {p['label']: p['index'] for p in pdf_pages}

    st.subheader("3. Pilih Halaman/Bay")
    selected_labels = st.multiselect(
        "Pilih halaman yang ingin diproses menjadi MOVINS:",
        options=list(page_options.keys()),
        default=list(page_options.keys())[0] # Default pilih halaman pertama
    )
    
    selected_indices = [page_options[lbl] for lbl in selected_labels]

    if selected_indices:
        # Analisis simbol hanya dari halaman terpilih
        detected_symbols = extract_symbols_from_selected_pages(uploaded_file, selected_indices)
        
        st.subheader("4. Validasi Mapping Port")
        st.info(f"Menganalisis simbol dari {len(selected_indices)} halaman terpilih...")
        
        mapping_data = {}
        cols = st.columns(3)
        for i, symbol in enumerate(detected_symbols):
            with cols[i % 3]:
                mapping_data[symbol] = st.text_input(f"POD untuk '{symbol}':", placeholder="Contoh: MYPTP", key=f"s_{symbol}")

        if st.button("Generate MOVINS (.BAP)"):
            gen = BapGenerator(vessel, voyage, pol)
            
            # Simulasi ekstraksi koordinat (Ini adalah bagian yang perlu disesuaikan 
            # lebih lanjut dengan koordinat tabel PDF Anda)
            # Contoh dummy untuk testing:
            gen.add_slot("01", "08", "82", pol, mapping_data.get(detected_symbols[0], "UNKNOWN") if detected_symbols else "UNKNOWN")
            
            bap_content = gen.finalize()
            
            st.success(f"Berhasil mengonversi {len(selected_indices)} halaman!")
            st.download_button(
                label="📥 Download File .BAP",
                data=bap_content,
                file_name=f"MOVINS_{vessel}_{voyage}.BAP",
                mime="text/plain"
            )
    else:
        st.warning("Silakan pilih minimal satu halaman untuk diproses.")
