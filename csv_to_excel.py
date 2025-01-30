import pandas as pd
import streamlit as st
import io
import uuid
from datetime import datetime

def process_data(data, selected_columns, cleaning_options, filters):
    """
    Fungsi untuk memproses data dengan berbagai opsi pembersihan dan filter
    """
    # Filter kolom terlebih dahulu
    processed_data = data[selected_columns].copy()
    
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
    
    # Terapkan filter dinamis
    for col, f in filters.items():
        if f['type'] == 'numeric':
            processed_data = processed_data[(processed_data[col] >= f['min']) & 
                                           (processed_data[col] <= f['max'])]
        elif f['type'] == 'categorical':
            processed_data = processed_data[processed_data[col].isin(f['values'])]
    
    return processed_data

def transform_data(data, output_format, column_mapping):
    """
    Fungsi untuk mengonversi data ke format yang diinginkan
    """
    renamed_data = data.rename(columns=column_mapping)
    
    output = io.BytesIO()
    
    if output_format == 'Excel':
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            renamed_data.to_excel(writer, index=False)
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

# UI Streamlit
st.title("📊 Advanced Data Exporter")
st.sidebar.header("Pengaturan Pemrosesan")

# Upload file
uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

if uploaded_file is not None:
    # Baca data
    data = pd.read_csv(uploaded_file)
    all_columns = data.columns.tolist()
    
    # Opsi pembersihan data di sidebar
    with st.sidebar.expander("⚙️ Opsi Pembersihan Data"):
        cleaning_options = {
            'handle_missing': st.radio("Penanganan Data Kosong",
                                      ['Pertahankan', 'Hapus Baris', 'Isi dengan Nilai']),
            'remove_duplicates': st.checkbox("Hapus Data Duplikat")
        }
    
    # Pemilihan kolom
    selected_columns = st.multiselect("Pilih kolom untuk diekspor", all_columns, default=all_columns)
    
    # Filter dinamis
    filters = {}
    if selected_columns:
        st.subheader("🔍 Filter Data")
        cols = st.columns(2)
        for i, col in enumerate(selected_columns):
            with cols[i % 2]:
                if pd.api.types.is_numeric_dtype(data[col]):
                    min_val = float(data[col].min())
                    max_val = float(data[col].max())
                    selected_range = st.slider(
                        f"Rentang {col}",
                        min_val,
                        max_val,
                        (min_val, max_val)
                    )
                    filters[col] = {
                        'type': 'numeric',
                        'min': selected_range[0],
                        'max': selected_range[1]
                    }
                else:
                    unique_vals = data[col].unique().tolist()
                    selected_vals = st.multiselect(
                        f"Nilai {col}",
                        unique_vals,
                        default=unique_vals
                    )
                    filters[col] = {
                        'type': 'categorical',
                        'values': selected_vals
                    }
    
    # Pemrosesan data
    processed_data = process_data(data, selected_columns, cleaning_options, filters)
    
    # Preview data
    with st.expander("👀 Preview Data"):
        st.dataframe(processed_data.head(10))
    
    # Pengaturan ekspor
    st.subheader("⚡ Pengaturan Ekspor")
    
    col1, col2 = st.columns(2)
    with col1:
        # Pemetaan nama kolom
        column_mapping = {}
        for col in selected_columns:
            column_mapping[col] = st.text_input(
                f"Ganti nama '{col}'",
                value=col
            )
    
    with col2:
        # Format output
        output_format = st.radio("Format Output", ['Excel', 'CSV', 'JSON'])
        output_name = st.text_input("Nama File", value="export_data")
    
    # Tombol ekspor
    if st.button("🚀 Ekspor Data"):
        try:
            output, mime_type, file_ext = transform_data(
                processed_data,
                output_format,
                column_mapping
            )
            
            # Generate nama file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{output_name}_{timestamp}.{file_ext}"
            
            # Tombol unduh
            st.download_button(
                label="💾 Unduh File",
                data=output,
                file_name=filename,
                mime=mime_type
            )
            st.success("✅ Data berhasil diproses dan siap diunduh!")
            
        except Exception as e:
            st.error(f"❌ Error dalam pemrosesan data: {str(e)}")

else:
    st.info("ℹ️ Silahkan upload file CSV untuk memulai")
