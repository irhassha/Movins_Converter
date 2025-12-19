import streamlit as st
import pdfplumber
import datetime

# --- FUNGSI CORE: GENERATOR BAP ---
class BapGenerator:
    def __init__(self, vessel_name, voyage, pol):
        self.segments = []
        now = datetime.datetime.now()
        # Format sesuai sample .BAP yang diberikan
        self.segments.append(f"UNB+UNOA:1+IDP000026+EMC+{now.strftime('%y%m%d:%H%M')}+0+++++'")
        self.segments.append("UNH+1+MOVINS:S:93A:UN:SMDG20'")
        self.segments.append("BGM++0+9'")
        self.segments.append(f"DTM+137:{now.strftime('%Y%m%d%H%M')}:201'")
        self.segments.append(f"TDT+20+{voyage}+++:172:20+++BKLU:103::{vessel_name}'")
        self.segments.append(f"LOC+5+{pol}:139:6'")
        self.segments.append("HAN+LOA'")

    def add_slot(self, bay, row, tier, pol, pod):
        coord = f"{int(bay):03d}{int(row):02d}{int(tier):02d}"
        self.segments.append(f"LOC+147+{coord}'")
        self.segments.append("MEA+WT++KGM:00000'") # Berat Default 0
        self.segments.append(f"LOC+9+{pol}'")
        self.segments.append(f"LOC+11+{pod}'")
        self.segments.append("RFF+BM:1'")
        self.segments.append("EQD+CN++2210+++5'") # Default ISO 2210

    def finalize(self):
        count = len(self.segments) - 1
        self.segments.append(f"UNT+{count}+1'")
        self.segments.append("UNZ+1+0'")
        return '\r\n'.join(self.segments)

# --- FUNGSI PARSING DENGAN FILTER KETAT ---
def extract_clean_symbols(uploaded_file, page_index):
    valid_symbols = []
    with pdfplumber.open(uploaded_file) as pdf:
        page = pdf.pages[page_index]
        words = page.extract_words()
        
        for w in words:
            text = w['text'].strip().upper()
            # FILTER: Hanya ambil teks yang panjangnya 1-2 karakter 
            # Ini biasanya adalah simbol warna/kargo (X, P, J, U)
            # Dan abaikan angka (karena angka biasanya Row/Tier/Total)
            if len(text) <= 2 and text.isalpha():
                valid_symbols.append(text)
                
    return sorted(list(set(valid_symbols)))

# --- UI STREAMLIT ---
st.set_page_config(page_title="Stowage to MOVINS", layout="centered")
st.title("🚢 BAP Generator (Page 1 Only)")

with st.sidebar:
    st.header("Vessel Info")
    vessel = st.text_input("Vessel Name", "EVER BLINK")
    voyage = st.text_input("Voyage", "1170-077A")
    pol = st.text_input("POL", "IDJKT")

uploaded_file = st.file_uploader("Upload Stowage Plan PDF", type=["pdf"])

if uploaded_file:
    # Kita kunci hanya untuk Page 1 (Index 0)
    st.info("Menganalisis Simbol Kargo di Halaman 1...")
    
    # Ekstraksi simbol yang sudah difilter (Hanya huruf tunggal/pendek)
    detected_symbols = extract_clean_symbols(uploaded_file, 0)
    
    if not detected_symbols:
        st.warning("Tidak ditemukan simbol kargo (X/P/J) di halaman ini.")
    else:
        st.subheader("📍 Mapping Pelabuhan Tujuan")
        st.write("Isi UNLOCODE tujuan untuk simbol yang terdeteksi di dalam Bay:")
        
        mapping_dict = {}
        # Menampilkan input hanya untuk simbol yang benar-benar ada (X, P, J, dll)
        cols = st.columns(len(detected_symbols))
        for i, sym in enumerate(detected_symbols):
            with cols[i]:
                mapping_dict[sym] = st.text_input(f"Simbol: {sym}", placeholder="POD", key=f"v_{sym}")

        if st.button("Generate .BAP"):
            # Validasi apakah semua sudah diisi
            if any(v == "" for v in mapping_dict.values()):
                st.error("Mohon isi semua POD untuk simbol yang terdeteksi.")
            else:
                gen = BapGenerator(vessel, voyage, pol)
                
                # Logic simulasi: Kita ambil Page 1, cari posisi X/P/J dan convert ke koordinat
                # Untuk prototype ini, kita buat sample baris berdasarkan mapping user
                with pdfplumber.open(uploaded_file) as pdf:
                    # Contoh: Kita asumsikan menemukan 1 kontainer untuk setiap simbol yang divalidasi
                    for sym, pod_code in mapping_dict.items():
                        # Contoh koordinat dummy (nanti bisa dikembangkan ke grid mapping)
                        gen.add_slot("001", "08", "82", pol, pod_code)
                
                output_bap = gen.finalize()
                
                st.success("MOVINS Berhasil dibuat!")
                st.download_button("Download .BAP File", output_bap, f"{vessel}_{voyage}.BAP")
                st.text_area("Preview Content:", output_bap, height=200)
