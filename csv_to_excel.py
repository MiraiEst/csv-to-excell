import pandas as pd
import streamlit as st
import io
import chardet
import re
from datetime import datetime

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

# Fungsi untuk memproses data
def process_data(data, selected_columns, cleaning_options, filters, date_settings):
    processed_data = data[selected_columns].copy()
    
    # Handle kolom tanggal
    for col, settings in date_settings.items():
        if settings['is_date']:
            try:
                processed_data[col] = pd.to_datetime(processed_data[col])
                processed_data = processed_data[
                    (processed_data[col] >= pd.to_datetime(settings['start_date'])) &
                    (processed_data[col] <= pd.to_datetime(settings['end_date']))
                ]
                processed_data[col] = processed_data[col].dt.strftime(settings['date_format'])
            except:
                st.warning(f"Gagal memproses kolom tanggal {col}")
    
    # Handle missing values
    if cleaning_options['handle_missing'] == 'Hapus Baris':
        processed_data = processed_data.dropna()
    elif cleaning_options['handle_missing'] == 'Isi dengan Nilai':
        for col in selected_columns:
            if processed_data[col].dtype == 'object':
                processed_data[col].fillna('Tidak Diketahui', inplace=True)
            else:
                processed_data[col].fillna(0, inplace=True)
    
    # Hapus duplikat
    if cleaning_options['remove_duplicates']:
        processed_data = processed_data.drop_duplicates()
    
    # Terapkan filter
    for col, f in filters.items():
        if f['type'] == 'numeric':
            processed_data = processed_data[(processed_data[col] >= f['min']) & 
                                           (processed_data[col] <= f['max'])]
        elif f['type'] == 'categorical':
            processed_data = processed_data[processed_data[col].isin(f['values'])]
    return processed_data

# Fungsi untuk transformasi data
def transform_data(data, output_format, column_mapping, excel_options):
    renamed_data = data.rename(columns=column_mapping)
    
    output = io.BytesIO()
    
    if output_format == 'Excel':
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            renamed_data.to_excel(writer, index=False)
            
            # Excel formatting
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Auto-adjust column width
            if excel_options['auto_width']:
                for idx, col in enumerate(renamed_data.columns):
                    max_len = max((
                        renamed_data[col].astype(str).map(len).max(),
                        len(str(col))
                    )) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            # Header formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': excel_options['header_color'],
                'border': 1
            })
            
            for col_num, value in enumerate(renamed_data.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_ext = "xlsx"
    
    elif output_format == 'CSV':
        renamed_data.to_csv(output, index=False)
        mime_type = "text/csv"
        file_ext = "csv"
    
    elif output_format == 'JSON':
        output.write(renamed_data.to_json(orient='records').encode())
        mime_type = "application/json"
        file_ext = "json"
    
    output.seek(0)
    return output, mime_type, file_ext

# Fungsi untuk membaca CSV dengan penanganan error yang diperbarui
def read_csv_with_encoding(uploaded_file):
    # Baca file untuk deteksi encoding
    raw_data = uploaded_file.read()
    result = chardet.detect(raw_data)
    detected_encoding = result['encoding']
    uploaded_file.seek(0)

    # Deteksi delimiter menggunakan pandas Sniffer
    try:
        sample = uploaded_file.read(1024).decode(detected_encoding)
        dialect = pd.io.parsers.Sniffer().sniff(sample)
        delimiters = [dialect.delimiter]
        uploaded_file.seek(0)
    except:
        delimiters = [',', ';', '\t', '|', ':', '~', ' ']  # Delimiter alternatif

    # Coba berbagai delimiter
    for delimiter in delimiters:
        try:
            uploaded_file.seek(0)
            data = pd.read_csv(
                uploaded_file,
                encoding=detected_encoding,
                sep=delimiter,
                engine='python',
                on_bad_lines='skip',
                quotechar='"',
                escapechar='\\'
            )
            if not data.empty and len(data.columns) > 1:
                st.session_state.delimiter = delimiter
                return data, detected_encoding
        except Exception as e:
            continue

    # Jika semua gagal, tampilkan opsi manual
    st.error("⚠️ Gagal mendeteksi delimiter otomatis!")
    manual_delimiter = st.text_input("Masukkan delimiter manual:", ',')
    
    try:
        uploaded_file.seek(0)
        data = pd.read_csv(
            uploaded_file,
            encoding=detected_encoding,
            sep=manual_delimiter,
            engine='python',
            on_bad_lines='skip'
        )
        if not data.empty:
            st.session_state.delimiter = manual_delimiter
            return data, detected_encoding
    except Exception as e:
        st.error(f"Tetap gagal: {str(e)}")
        st.stop()

# UI Streamlit
st.set_page_config(page_title="Data Exporter Pro", layout="centered")
st.title("📁 Data Exporter Pro")

# Upload file
uploaded_file = st.file_uploader("Upload CSV", type=["csv"], help="Upload file CSV maksimal 100MB")

if uploaded_file is not None:
    try:
        # Baca file dengan penanganan error
        data, detected_encoding = read_csv_with_encoding(uploaded_file)
        
        # Tampilkan preview data mentah
        with st.expander("🔍 Preview Data Mentah (Cek Pemisah Kolom)"):
            cols = st.columns(2)
            cols[0].write("5 Baris Pertama:")
            cols[0].dataframe(data.head(), use_container_width=True)
            cols[1].write("Informasi File:")
            cols[1].json({
                "Encoding": detected_encoding,
                "Delimiter": st.session_state.get('delimiter', 'auto'),
                "Jumlah Baris": len(data),
                "Jumlah Kolom": len(data.columns)
            })
        
        # Definisikan all_columns di sini
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

        # Tambahan fitur parsing ulang manual
        if len(data.columns) == 1:
            st.warning("Kolom tidak terpisah dengan benar!")
            with st.expander("⚠️ Perbaiki Pemisah Kolom"):
                new_delimiter = st.text_input("Masukkan delimiter baru:", st.session_state.get('delimiter', ','))
                if st.button("Coba Parsing Ulang"):
                    try:
                        uploaded_file.seek(0)
                        data = pd.read_csv(
                            uploaded_file,
                            encoding=detected_encoding,
                            sep=new_delimiter,
                            engine='python',
                            on_bad_lines='skip'
                        )
                        st.session_state.delimiter = new_delimiter
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

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
