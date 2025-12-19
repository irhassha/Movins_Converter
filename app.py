import streamlit as st
import pdfplumber
import datetime
import re

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

# --- FUNGSI PARSING DENGAN WHITELIST KARAKTER ---
def extract_cargo_codes(uploaded_file, page_index):
    cargo_symbols = []
    
    with pdfplumber.open(uploaded_file) as pdf:
        page = pdf.pages[page_index]
        words = page.extract_words()
        
        for w in words:
            raw_text = w['text'].strip()
            
            # Kriteria Ketat (Whitelist):
            # 1. Harus Huruf Besar semua
            # 2. Tidak boleh ada angka
            # 3. Panjangnya 1-3 karakter (misal: P, PP, PPP)
            # 4. Bukan kata umum yang sering muncul di header/footer
            if (raw_text.isupper() and 
                raw_text.isalpha() and 
                len(raw_text) <= 3 and
                raw_text not in ["NO", "X", "POL", "BAY", "VOY", "DKT", "STW", "PAGE"]):
                
                # Kita ambil karakter tunggalnya saja (misal PPP jadi P)
                single_code = raw_text[0]
                cargo_symbols.append(single_code)
                
    return sorted(list(set(cargo_symbols)))

# --- UI STREAMLIT ---
st.set_page_config(page_title="Stowage to BAP v3", layout="centered")
st.title("🚢 BAP Generator (Final Filter)")

with st.sidebar:
    st.header("Informasi Kapal")
    v_name = st.text_input("Vessel Name", "EVER BLINK")
    v_voy = st.text_input("Voyage", "1170-077A")
    v_pol = st.text_input("POL", "IDJKT")

uploaded_file = st.file_uploader("Upload Stowage PDF (Page 1)", type=["pdf"])

if uploaded_file:
    # Scan simbol
    detected = extract_cargo_codes(uploaded_file, 0)
    
    if not detected:
        st.warning("Tidak ditemukan kode kargo (seperti P, J, U) di halaman ini.")
    else:
        st.subheader("📍 Validasi Tujuan (POD)")
        st.write("Ditemukan simbol kargo di dalam Bay. Masukkan UNLOCODE tujuannya:")
        
        mapping = {}
        # Tampilkan secara horizontal
        cols = st.columns(len(detected))
        for i, sym in enumerate(detected):
            with cols[i]:
                mapping[sym] = st.text_input(f"Simbol {sym}", placeholder="POD", key=f"v_{sym}").upper()

        if st.button("Generate .BAP"):
            if any(v == "" for v in mapping.values()):
                st.error("Mohon lengkapi semua mapping POD.")
            else:
                gen = BapGenerator(v_name, v_voy, v_pol)
                
                # Loop simulasi (Defaulting ke satu slot per simbol untuk testing)
                for sym, pod in mapping.items():
                    gen.add_slot("001", "08", "82", v_pol, pod)
                
                res = gen.finalize()
                st.success("Konversi Berhasil!")
                st.download_button("Download .BAP", res, f"MOVINS_{v_voy}.BAP")
                st.code(res, language='text')
