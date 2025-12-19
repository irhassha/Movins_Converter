import streamlit as st
import io

def clean_edi_element(segment_str):
    """Membersihkan newline/whitespace yang tidak perlu di akhir segmen"""
    return segment_str.strip()

def process_baplie_to_movins(content, target_loc="IDJKT"):
    """
    Core logic konversi:
    1. Ganti Header ke MOVINS SMDG20
    2. Grouping per Slot (LOC+147)
    3. Filter hanya yang mengandung target_loc (JKT)
    4. Hapus Nomor Container di EQD
    """
    
    # 1. Split berdasarkan terminator segment (biasanya ' diakhiri newline)
    # Kita replace newline dulu agar aman, lalu split by '
    raw_segments = content.replace('\n', '').replace('\r', '').split("'")
    
    processed_segments = []
    
    # Header & Footer Buffer
    header_buffer = []
    cargo_blocks = []
    current_block = []
    is_inside_cargo = False
    
    # --- STEP 1: PARSING & GROUPING ---
    for seg in raw_segments:
        seg = seg.strip()
        if not seg: continue # Skip empty lines
        
        # Deteksi Header Change
        if seg.startswith("UNH+"):
            # Ganti Header BAPLIE jadi MOVINS sesuai request (SMDG20)
            # Kita ambil Reference number dari aslinya (biasanya index 1)
            parts = seg.split('+')
            msg_ref = parts[1] if len(parts) > 1 else "1"
            new_header = f"UNH+{msg_ref}+MOVINS:S:93A:UN:SMDG20"
            header_buffer.append(new_header)
            continue
            
        # Deteksi Mulai Cargo Block (LOC+147 adalah posisi stowage)
        if seg.startswith("LOC+147"):
            is_inside_cargo = True
            # Jika ada block sebelumnya yang sedang diproses, simpan dulu
            if current_block:
                cargo_blocks.append(current_block)
            current_block = [seg] # Mulai block baru
        
        # Deteksi Akhir File (UNT / UNZ)
        elif seg.startswith("UNT+") or seg.startswith("UNZ+"):
            if current_block:
                cargo_blocks.append(current_block)
                current_block = []
            is_inside_cargo = False
            # Update UNT count nanti, simpan logic footer nanti atau generate baru
        
        # Segmen biasa
        else:
            if is_inside_cargo:
                current_block.append(seg)
            else:
                header_buffer.append(seg)

    # Push block terakhir jika ada
    if current_block:
        cargo_blocks.append(current_block)

    # --- STEP 2: FILTERING & TRANSFORMING ---
    final_cargo_segments = []
    
    for block in cargo_blocks:
        # Gabungkan block jadi string untuk pencarian cepat keyword "IDJKT"
        block_str = "'".join(block)
        
        # Filter Logic: Hanya ambil jika ada "IDJKT" (atau keyword user)
        if target_loc in block_str:
            transformed_block = []
            for seg in block:
                # Transform Logic: Hapus Nomor Container
                if seg.startswith("EQD+CN"):
                    # Format: EQD+CN+CONTAINER_NO+TYPE...
                    parts = seg.split('+')
                    if len(parts) > 2:
                        parts[2] = "" # Kosongkan posisi Container No
                    new_seg = "+".join(parts)
                    transformed_block.append(new_seg)
                else:
                    transformed_block.append(seg)
            
            final_cargo_segments.extend(transformed_block)

    # --- STEP 3: REBUILDING ---
    # Hitung ulang jumlah segmen untuk UNT (Header + Cargo + UNT itu sendiri)
    # UNH sudah masuk header_buffer[1] biasanya
    
    output_segments = header_buffer + final_cargo_segments
    
    # Buat Footer UNT baru
    # Count: Jumlah segmen termasuk UNH dan UNT.
    # Cari Reference number UNH tadi
    unh_ref = "1"
    for s in header_buffer:
        if s.startswith("UNH+"):
            unh_ref = s.split('+')[1]
            break
            
    total_segments = len(output_segments) + 1 # +1 untuk UNT itu sendiri
    unt_segment = f"UNT+{total_segments}+{unh_ref}"
    output_segments.append(unt_segment)
    
    # Tambahkan UNZ jika di input ada UNB (biasanya ada)
    # Sederhananya kita ambil UNZ standard atau copy dari raw jika mau kompleks.
    # Untuk aman, kita tutup dengan UNZ generic jika belum ada logic UNZ complex
    output_segments.append(f"UNZ+1+{unh_ref}") 

    # Gabungkan dengan terminator '
    return "'\n".join(output_segments) + "'"

# --- STREAMLIT UI ---
st.set_page_config(page_title="BAPLIE to MOVINS Converter", page_icon="🚢")

st.title("🚢 BAPLIE to MOVINS Converter")
st.markdown("""
Aplikasi ini mengubah file **BAPLIE** menjadi format **MOVINS** (SMDG20) dengan aturan:
1.  **Header:** Diubah ke `MOVINS:S:93A:UN:SMDG20`.
2.  **Filter:** Hanya mengambil slot yang mengandung lokasi **JKT** (IDJKT).
3.  **Clean:** Menghapus **Nomor Kontainer** pada segmen `EQD`.
""")

uploaded_file = st.file_uploader("Upload file BAPLIE (.EDI / .TXT)", type=['edi', 'txt', 'bap'])

col1, col2 = st.columns(2)
target_loc = col1.text_input("Filter Location Code (Keep Only)", value="IDJKT")

if uploaded_file is not None:
    # Baca file
    content = uploaded_file.getvalue().decode("utf-8")
    
    st.info(f"File uploaded: {uploaded_file.name}")
    
    # Preview Input (10 baris pertama)
    with st.expander("Lihat Preview Input (Raw)"):
        st.code(content[:500] + "\n...", language="text")

    if st.button("Convert to MOVINS"):
        try:
            result_text = process_baplie_to_movins(content, target_loc)
            
            st.success(f"Konversi Berhasil! Data difilter untuk lokasi: {target_loc}")
            
            # Preview Output
            with st.expander("Lihat Preview Output (Result)"):
                st.code(result_text[:1000] + "\n...", language="text")
            
            # Tombol Download
            output_filename = f"MOVINS_{target_loc}_{uploaded_file.name}"
            st.download_button(
                label="Download MOVINS File",
                data=result_text,
                file_name=output_filename,
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memproses: {e}")
