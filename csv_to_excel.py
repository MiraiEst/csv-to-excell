import pandas as pd
import streamlit as st
import io
import uuid
from openpyxl import load_workbook

def transform_csv_to_excel_with_template(csv_data, template_file, selected_columns, column_mapping, selected_category, sheet_name):
    """
    Memasukkan data CSV ke dalam template Excel yang diunggah pengguna.
    """
    # Membaca CSV sebagai DataFrame
    csv_df = pd.read_csv(csv_data)

    # Pilih hanya kolom yang dipilih pengguna
    csv_df = csv_df[selected_columns]

    # Filter berdasarkan kategori yang dipilih
    if selected_category != "Semua" and "Segment_Category" in csv_df.columns:
        csv_df = csv_df[csv_df["Segment_Category"] == selected_category]

    # Ganti nama kolom sesuai pemetaan
    csv_df = csv_df.rename(columns={col: column_mapping.get(col, col) for col in selected_columns})

    # Buka template Excel
    template_bytes = io.BytesIO(template_file.getvalue())  # Konversi file ke BytesIO
    book = load_workbook(template_bytes)  

    # Pastikan sheet yang dipilih tersedia
    if sheet_name not in book.sheetnames:
        return None, f"Sheet '{sheet_name}' tidak ditemukan dalam template!"

    sheet = book[sheet_name]  # Ambil sheet yang dipilih

    # Masukkan data ke sheet (dimulai dari baris kedua agar tidak menimpa header)
    for r_idx, row in enumerate(csv_df.itertuples(index=False), start=2):
        for c_idx, value in enumerate(row, start=1):
            sheet.cell(row=r_idx, column=c_idx, value=value)

    # Simpan hasil ke memori (bukan disk)
    output = io.BytesIO()
    book.save(output)
    output.seek(0)

    return output, None

# ============================ STREAMLIT UI ============================ #

st.title("Ekstrak Data ke Template Excel")

# **Upload file CSV**
uploaded_csv = st.file_uploader("Upload file CSV", type=["csv"])

# **Upload Template Excel**
uploaded_template = st.file_uploader("Upload Template Excel", type=["xlsx"])

if uploaded_csv and uploaded_template:
    # Membaca data CSV
    data = pd.read_csv(uploaded_csv)

    # Menampilkan daftar kolom yang bisa dipilih
    all_columns = data.columns.tolist()

    # Pilih kolom yang ingin dimasukkan ke Excel
    selected_columns = st.multiselect("Pilih kolom yang ingin dimasukkan", all_columns, default=all_columns[:3])

    # Pemetaan nama kolom
    column_mapping = {col: col for col in selected_columns}

    # Pilihan kategori (jika 'Segment_Category' tersedia)
    if "Segment_Category" in data.columns:
        kategori_unik = ["Semua"] + sorted(data["Segment_Category"].dropna().unique().tolist())
        selected_category = st.selectbox("Pilih Kategori", kategori_unik)
    else:
        selected_category = "Semua"

    # Pilih sheet dalam template Excel
    book = load_workbook(io.BytesIO(uploaded_template.getvalue()))
    sheet_name = st.selectbox("Pilih Sheet untuk Menyimpan Data", book.sheetnames)

    if st.button("Ekspor ke Template Excel"):
        output_excel, error = transform_csv_to_excel_with_template(
            uploaded_csv, uploaded_template, selected_columns, column_mapping, selected_category, sheet_name
        )

        if error:
            st.error(error)
        else:
            unique_filename = f"export_{uuid.uuid4().hex}.xlsx"
            st.download_button(
                label="Unduh File",
                data=output_excel,
                file_name=unique_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
