import streamlit as st
import pdfplumber
import datetime

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

    def add_slot(self, bay, row, tier, pol, pod):
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

# --- FUNGSI PARSING DENGAN BLACKLIST ---
def extract_clean_symbols(uploaded_file, page_index):
    symbols_found = []
    # Daftar kata yang harus diabaikan (Blacklist)
    blacklist = ["NO", "X", "PAGE", "VOY", "DATE", "POL", "BAY", "DKT", "STW", "BLNK"]
    
    with pdfplumber.open(uploaded_file) as pdf:
        page = pdf.pages[page_index]
        words = page.extract_words()
        
        for w in words:
            text = w['text'].strip().upper()
            
            # Kriteria: Huruf saja, panjang 1-3 karakter, bukan angka, bukan blacklist
            if (len(text) <= 3 and 
                text.isalpha() and 
                text not in blacklist):
                symbols_found.append(text)
                
    return sorted(list(set(symbols_found)))

# --- UI STREAMLIT ---
st.set_page_config(page_title="Stowage Clean Converter", layout="centered")
st.title("🚢 BAP Generator (Clean Version)")

with st.sidebar:
    st.header("Vessel Info")
    v_name = st.text_input("Vessel Name", "EVER BLINK")
    v_voy = st.text_input("Voyage", "1170-077A")
    v_pol = st.text_input("POL", "IDJKT")

uploaded_file = st.file_uploader("Upload PDF Page 1", type=["pdf"])

if uploaded_file:
    st.info("Menganalisis kode kargo di Halaman 1...")
    
    # Ambil simbol yang bersih
    detected_symbols = extract_clean_symbols(uploaded_file, 0)
    
    if not detected_symbols:
        st.warning("Tidak ditemukan kode kargo yang valid di halaman ini.")
    else:
        st.subheader("📍 Validasi Kode Pelabuhan")
        st.write("Tentukan UNLOCODE untuk simbol kargo yang ditemukan:")
        
        mapping_dict = {}
        # Layout kolom dinamis berdasarkan jumlah simbol
        cols = st.columns(max(len(detected_symbols), 1))
        for i, sym in enumerate(detected_symbols):
            with cols[i]:
                mapping_dict[sym] = st.text_input(f"Simbol: {sym}", placeholder="POD", key=f"v_{sym}")

        if st.button("Generate .BAP File"):
            if any(v == "" for v in mapping_dict.values()):
                st.error("Mohon isi semua POD.")
            else:
                gen = BapGenerator(v_name, v_voy, v_pol)
                
                # Logic: Untuk setiap simbol, kita buatkan record di BAP
                # (Proses koordinat otomatis akan memerlukan logic grid mapping)
                for sym, pod_code in mapping_dict.items():
                    # Contoh dummy Bay 01
                    gen.add_slot("001", "08", "82", v_pol, pod_code)
                
                output_bap = gen.finalize()
                st.success("File MOVINS Berhasil Dibuat!")
                st.download_button("📥 Download .BAP", output_bap, f"{v_name}_{v_voy}.BAP")
