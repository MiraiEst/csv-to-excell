import pandas as pd
import streamlit as st
import io
import uuid
import re
import chardet  # Untuk mendeteksi encoding
from datetime import datetime
from xlsxwriter.utility import xl_col_to_name

# Fungsi untuk mendeteksi encoding file CSV
def detect_encoding(file):
    raw_data = file.read()
    result = chardet.detect(raw_data)
    file.seek(0)  # Reset pointer file setelah membaca
    return result["encoding"]

# Fungsi untuk validasi data
def validate_data(data):
    warnings = []
    
    # Validasi format email
    email_cols = [col for col in data.columns if 'email' in col.lower()]
    for col in email_cols:
        invalid_emails = data[col][~data[col].apply(lambda x: re.match(r"[^@]+@[^@]+\.[^@]+", str(x)))]
        if not invalid_emails.empty:
            warnings.append(f"Format email tidak valid di kolom {col}: {len(invalid_emails)} entri")
    
    # Validasi nomor telepon
    phone_cols = [col for col in data.columns if 'phone' in col.lower()]
    for col in phone_cols:
        invalid_phones = data[col][~data[col].apply(lambda x: re.match(r"^\+?[0-9\s\-()]+$", str(x)))]

        if not invalid_phones.empty:
            warnings.append(f"Format telepon tidak valid di kolom {col}: {len(invalid_phones)} entri")
    
    return warnings

# UI Streamlit
st.set_page_config(page_title="Data Exporter", layout="centered")
st.title("📁 Data Exporter")

# Upload file
uploaded_file = st.file_uploader("Upload CSV", type=["csv"], help="Upload file CSV maksimal 100MB")

if uploaded_file is not None:
    try:
        # Deteksi encoding file
        detected_encoding = detect_encoding(uploaded_file)

        # Coba membaca file CSV dengan encoding yang terdeteksi
        data = pd.read_csv(uploaded_file, encoding=detected_encoding, errors="replace")

    except UnicodeDecodeError:
        st.error("Gagal membaca file. Coba gunakan format encoding lain seperti UTF-8, Latin-1, atau Windows-1252.")
        st.stop()
    except Exception as e:
        st.error(f"Terjadi kesalahan saat membaca file: {str(e)}")
        st.stop()

    all_columns = data.columns.tolist()

    # Sidebar Settings
    with st.sidebar:
        st.header("⚙️ Pengaturan")
        
        with st.expander("Pembersihan Data"):
            cleaning_options = {
                'handle_missing': st.radio("Data Kosong",
                                          ['Pertahankan', 'Hapus Baris', 'Isi dengan Nilai']),
                'remove_duplicates': st.checkbox("Hapus Duplikat")
            }
            
        with st.expander("Format Excel"):
            excel_options = {
                'auto_width': st.checkbox("Auto Lebar Kolom", True),
                'header_color': st.color_picker("Warna Header", '#4F81BD'),
                'freeze_header': st.checkbox("Freeze Header", True)
            }

    # Main Content
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Kolom dan Filter
        selected_columns = st.multiselect("Pilih Kolom", all_columns, default=all_columns)
        
    if selected_columns:
        processed_data = data[selected_columns].copy()

        # Validasi data
        validation_warnings = validate_data(processed_data)
        if validation_warnings:
            with st.container(border=True):
                st.warning("⚠️ Peringatan Validasi")
                for warning in validation_warnings:
                    st.write(f"- {warning}")

        # Preview
        with st.expander("Preview Data"):
            st.dataframe(processed_data.head(8), use_container_width=True)
            st.caption(f"Menampilkan 8 dari {len(processed_data)} baris")

else:
    st.info("Silahkan upload file CSV untuk memulai", icon="ℹ️")
