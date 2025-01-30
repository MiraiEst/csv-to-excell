import pandas as pd
import streamlit as st
import io
import uuid

def transform_csv_to_excel(data, selected_columns, column_mapping, selected_category):
    """
    Fungsi untuk memproses dan mengonversi data ke file Excel tanpa menyimpannya di server.
    """
    # Memilih hanya kolom yang dipilih pengguna
    filtered_data = data[selected_columns]

    # Filter berdasarkan kategori yang dipilih
    if selected_category != "Semua" and "Segment_Category" in selected_columns:
        filtered_data = filtered_data[filtered_data['Segment_Category'] == selected_category]

    # Mengganti nama kolom sesuai pemetaan
    renamed_data = filtered_data.rename(columns={col: column_mapping.get(col, col) for col in selected_columns})

    # Simpan ke memori (bukan file di server)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        renamed_data.to_excel(writer, index=False)
    output.seek(0)  # Reset posisi pointer agar bisa dibaca

    return output

# Membuat UI Streamlit
st.title("Ekstrak Data Csv ke Excel")

# **Menambahkan fitur upload file**
uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

if uploaded_file is not None:
    # Membaca data dari file yang diunggah
    data = pd.read_csv(uploaded_file)

    # Menampilkan daftar kolom yang bisa dipilih
    all_columns = data.columns.tolist()
    
    # Multiselect untuk memilih kolom
    selected_columns = st.multiselect("Pilih kolom yang ingin diekspor", all_columns, default=all_columns[:3])

    # Pemetaan kolom (jika ingin mengganti nama)
    column_mapping = {col: col for col in selected_columns}  # Default nama kolom tetap

    # Pilihan kategori (hanya jika kolom 'Segment_Category' tersedia)
    if "Segment_Category" in data.columns:
        kategori_unik = ["Semua"] + sorted(data['Segment_Category'].dropna().unique().tolist())
        selected_category = st.selectbox("Pilih Kategori", kategori_unik)
    else:
        selected_category = "Semua"

    if st.button("Ekspor ke Excel"):
        # Generate file di memori, bukan di disk
        output_excel = transform_csv_to_excel(data, selected_columns, column_mapping, selected_category)

        # Nama file unik untuk menghindari konflik
        unique_filename = f"export_{uuid.uuid4().hex}.xlsx"

        # Tombol download langsung dari memori
        st.download_button(
            label="Unduh File",
            data=output_excel,
            file_name=unique_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
