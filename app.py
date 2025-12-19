import streamlit as st
import io

def clean_edi_element(segment_str):
    """Membersihkan newline/whitespace yang tidak perlu di akhir segmen"""
    return segment_str.strip()

def process_baplie_to_movins(content, target_loc="IDJKT"):
    """
    Core logic konversi:
    1. Ganti Header ke MOVINS SMDG20
    2. Tambahkan HAN+LOA sebelum cargo
    3. Filter hanya yang mengandung target_loc
    4. Hapus Nomor Container di EQD
    """
    
    raw_segments = content.replace('\n', '').replace('\r', '').split("'")
    
    header_buffer = []
    cargo_blocks = []
    current_block = []
    is_inside_cargo = False
    
    # --- STEP 1: PARSING & GROUPING ---
    for seg in raw_segments:
        seg = seg.strip()
        if not seg: continue 
        
        # 1. Handle Header Change (BAPLIE -> MOVINS)
        if seg.startswith("UNH+"):
            parts = seg.split('+')
            msg_ref = parts[1] if len(parts) > 1 else "1"
            # Hardcode header MOVINS SMDG20
            new_header = f"UNH+{msg_ref}+MOVINS:S:93A:UN:SMDG20"
            header_buffer.append(new_header)
            continue
            
        # 2. Deteksi Mulai Cargo Block (LOC+147)
        if seg.startswith("LOC+147"):
            is_inside_cargo = True
            if current_block:
                cargo_blocks.append(current_block)
            current_block = [seg] 
        
        # 3. Deteksi Akhir File
        elif seg.startswith("UNT+") or seg.startswith("UNZ+"):
            if current_block:
                cargo_blocks.append(current_block)
                current_block = []
            is_inside_cargo = False
        
        # 4. Segmen Lainnya
        else:
            if is_inside_cargo:
                current_block.append(seg)
            else:
                # Masukkan ke header buffer
                header_buffer.append(seg)

    # Push block terakhir jika tertinggal
    if current_block:
        cargo_blocks.append(current_block)

    # --- STEP 2: MENYISIPKAN 'HAN+LOA' ---
    # Kita perlu memastikan HAN+LOA ada di akhir header, sebelum masuk cargo.
    # Cek dulu apakah di header asli sudah ada (kemungkinan besar belum ada di BAPLIE)
    has_han_loa = any("HAN+LOA" in s for s in header_buffer)
    
    if not has_han_loa:
        # Sisipkan HAN+LOA di posisi paling akhir dari Header Buffer
        header_buffer.append("HAN+LOA")

    # --- STEP 3: FILTERING & TRANSFORMING ---
    final_cargo_segments = []
    
    for block in cargo_blocks:
        block_str = "'".join(block)
        
        # Filter Logic: Harus mengandung target_loc (IDJKT)
        if target_loc in block_str:
            transformed_block = []
            for seg in block:
                # Transform Logic: Hapus Nomor Container
                if seg.startswith("EQD+CN"):
                    # EQD+CN+NOMOR+TIPE... -> EQD+CN++TIPE...
                    parts = seg.split('+')
                    if len(parts) > 2:
                        parts[2] = "" 
                    new_seg = "+".join(parts)
                    transformed_block.append(new_seg)
                else:
                    transformed_block.append(seg)
            
            final_cargo_segments.extend(transformed_block)

    # --- STEP 4: REBUILDING ---
    output_segments = header_buffer + final_cargo_segments
    
    # Generate Footer UNT
    unh_ref = "1"
    for s in header_buffer:
        if s.startswith("UNH+"):
            unh_ref = s.split('+')[1]
            break
            
    total_segments = len(output_segments) + 1 
    unt_segment = f"UNT+{total_segments}+{unh_ref}"
    output_segments.append(unt_segment)
    
    # Generate Footer UNZ (Standard simple UNZ)
    output_segments.append(f"UNZ+1+{unh_ref}") 

    return "'\n".join(output_segments) + "'"
