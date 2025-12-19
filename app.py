import streamlit as st
import pdfplumber
import datetime
from collections import Counter

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

# --- FUNGSI PARSING & SUMMARY ---
def get_cargo_summary(uploaded_file, page_index):
    raw_symbols = []
    # Daftar kata yang pasti bukan simbol kargo
    trash = ["NO", "X", "POL", "BAY", "VOY", "DATE", "PAGE", "DKT", "STW", "EVER", "BLINK"]
    
    with pdfplumber.open(uploaded_file) as pdf:
        page = pdf.pages[page_index]
        words = page.extract_words()
        for w in words:
            txt = w['text'].strip().upper()
            # Hanya ambil huruf besar tunggal (seperti P, J, U, X)
            # Karena di PDF Anda simbol kargo biasanya huruf tunggal
            if len(txt) == 1 and txt.isalpha() and txt not in trash:
                raw_symbols.append(txt)
            elif len(txt) > 1 and txt.isalpha() and txt not in trash:
                # Jika ada teks seperti 'PPP', kita ambil 'P' saja
                if len(set(txt)) == 1: 
                    raw_symbols.append(txt[0])
                    
    return Counter(raw_symbols)

# --- UI STREAMLIT ---
st.set_page_config(page_title="BAP Generator Smart", layout="wide")
st.title("🚢 PDF to BAP - Lite Version")

with st.sidebar:
    st.header("Vessel Info")
    v_name = st.text_input("Vessel Name", "EVER BLINK")
    v_voy = st.text_input("Voyage", "1170-077A")
    v_pol = st.text_input("POL", "IDJKT")

uploaded_file = st.file_uploader("Upload Stowage PDF", type=["pdf"])

if uploaded_file:
    # 1. Get Summary
    summary = get_cargo_summary(uploaded_file, 0)
    
    if not summary:
        st.warning("Tidak ditemukan kode kargo yang valid di Halaman 1.")
    else:
        st.subheader("📊 Ringkasan Data Terdeteksi")
        
        # Tampilkan Summary dalam kolom
        sum_cols = st.columns(len(summary))
        for i, (sym, count) in enumerate(summary.items()):
            sum_cols[i].metric(label=f"Simbol {sym}", value=f"{count} Box")

        st.divider()
        st.subheader("📍 Mapping POD (Kosongkan jika tidak ingin diproses)")
        
        mapping = {}
        input_cols = st.columns(len(summary))
        for i, sym in enumerate(summary.keys()):
            mapping[sym] = input_cols[i].text_input(f"POD untuk {sym}", key=f"in_{sym}").upper()

        if st.button("🚀 Generate .BAP File"):
            # Filter hanya yang diisi POD-nya
            active_mapping = {k: v for k, v in mapping.items() if v.strip() != ""}
            
            if not active_mapping:
                st.error("Minimal satu POD harus diisi untuk generate file.")
            else:
                gen = BapGenerator(v_name, v_voy, v_pol)
                
                # Logic simulasi: memasukkan data berdasarkan jumlah box yang ditemukan
                # Catatan: Untuk koordinat asli (Bay/Row/Tier) memerlukan deteksi grid x,y
                for sym, pod in active_mapping.items():
                    total_box = summary[sym]
                    for _ in range(total_box):
                        # Contoh dummy koordinat
                        gen.add_slot("001", "08", "82", v_pol, pod)
                
                output = gen.finalize()
                st.success(f"Berhasil memproses {len(active_mapping)} kode kargo.")
                st.download_button("📥 Download .BAP", output, f"{v_name}_{v_voy}.BAP")
                st.text_area("Preview:", output, height=150)
