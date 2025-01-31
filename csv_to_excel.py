import pandas as pd
import streamlit as st
import io
import chardet  # Library untuk mendeteksi encoding

# Fungsi untuk membaca file CSV dengan encoding yang sesuai
def read_csv_with_encoding(uploaded_file):
    # Baca file untuk mendeteksi encoding
    raw_data = uploaded_file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    
    # Kembalikan pointer file ke awal
    uploaded_file.seek(0)
    
    # Coba baca file dengan encoding yang terdeteksi
    try:
        data = pd.read_csv(uploaded_file, encoding=encoding)
        return data
    except Exception as e:
        st.error(f"Gagal membaca file CSV dengan encoding {encoding}. Error: {str(e)}")
        st.stop()

# UI Streamlit
st.set_page_config(page_title="Data Exporter", layout="centered")
st.title("📁 Data Exporter")

# Upload file
uploaded_file = st.file_uploader("Upload CSV", type=["csv"], help="Upload file CSV maksimal 100MB")

if uploaded_file is not None:
    try:
        # Baca file CSV dengan encoding yang sesuai
        data = read_csv_with_encoding(uploaded_file)
        st.success("File CSV berhasil dibaca!")
        
        # Lanjutkan dengan proses lainnya...
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
                with st.expander("Filter Data", expanded=True):
                    filters = {}
                    cols = st.columns(2)
                    for i, col in enumerate(selected_columns):
                        with cols[i % 2]:
                            if pd.api.types.is_numeric_dtype(data[col]):
                                min_val = float(data[col].min())
                                max_val = float(data[col].max())
                                selected_range = st.slider(
                                    f"**{col}**",
                                    min_val,
                                    max_val,
                                    (min_val, max_val)
                                )
                                filters[col] = {'type': 'numeric', 'min': selected_range[0], 'max': selected_range[1]}
                            else:
                                unique_vals = data[col].unique().tolist()
                                selected_vals = st.multiselect(
                                    f"**{col}**",
                                    unique_vals,
                                    default=unique_vals
                                )
                                filters[col] = {'type': 'categorical', 'values': selected_vals}

        with col2:
            # Tanggal dan Export
            date_settings = {}
            if selected_columns:
                with st.expander("Pengaturan Tanggal"):
                    for col in selected_columns:
                        if pd.api.types.is_datetime64_any_dtype(data[col]) or data[col].astype(str).str.contains(r'\d{4}-\d{2}-\d{2}').any():
                            date_settings[col] = {
                                'is_date': st.checkbox(f"Tanggal: {col}", True),
                                'start_date': st.date_input(f"Mulai {col}", pd.to_datetime(data[col]).min()),
                                'end_date': st.date_input(f"Akhir {col}", pd.to_datetime(data[col]).max()),
                                'date_format': st.selectbox(f"Format {col}", ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"])
                            }

            with st.expander("Pengaturan Export"):
                output_format = st.radio("Format", ['Excel', 'CSV', 'JSON'])
                output_name = st.text_input("Nama File", "data_export")
                
                column_mapping = {}
                for col in selected_columns:
                    column_mapping[col] = st.text_input(
                        f"Rename '{col}'",
                        value=col
                    )

        # Proses dan Validasi
        if selected_columns:
            processed_data = process_data(data, selected_columns, cleaning_options, filters, date_settings)
            
            # Validasi
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

            # Export Button
            if st.button("🔼 Export Data", type="primary", use_container_width=True):
                with st.spinner("Memproses..."):
                    try:
                        output, mime_type, file_ext = transform_data(
                            processed_data,
                            output_format,
                            column_mapping,
                            excel_options
                        )
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{output_name}_{timestamp}.{file_ext}"
                        
                        st.download_button(
                            label="⬇️ Download File",
                            data=output,
                            file_name=filename,
                            mime=mime_type,
                            use_container_width=True
                        )
                        st.toast("✅ Export berhasil!", icon="🎉")
                        
                    except Exception as e:
                        st.error(f"Gagal export: {str(e)}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {str(e)}")

else:
    st.info("Silahkan upload file CSV untuk memulai", icon="ℹ️")
