import pandas as pd
import streamlit as st
import io
import uuid
import re
from openpyxl import load_workbook

def transform_csv_to_excel_with_mapping(csv_data, template_file, column_mapping, selected_category, sheet_name):
    """ 
    Masukkan data CSV ke kolom yang dipilih di template Excel (meskipun tidak bersampingan).
    """

    # Cek apakah CSV kosong
    try:
        csv_text = io.StringIO(csv_data.getvalue().decode("utf-8"))  
        data = pd.read_csv(csv_text)
        if data.empty:
            st.error("File CSV tidak mengandung data!")
            st.stop()
    except pd.errors.EmptyDataError:
        st.error("File CSV kosong atau tidak valid!")
        st.stop()
    except UnicodeDecodeError:
        st.error("Format encoding file tidak didukung! Coba simpan ulang file dengan UTF-8.")
        st.stop()

    # Filter berdasarkan kategori jika ada
    if selected_category != "Semua" and "Segment_Category" in data.columns:
        data = data[data["Segment_Category"] == selected_category]

    # Buka template Excel
    template_bytes = io.BytesIO(template_file.getvalue())  
    book = load_workbook(template_bytes)  

    # Cek apakah sheet tersedia
    if sheet_name not in book.sheetnames:
        return None, f"Sheet '{sheet_name}' tidak ditemukan dalam template!"

    sheet = book[sheet_name]  

    # Dapatkan posisi kolom di Excel berdasarkan header baris pertama
    excel_columns = {cell.value: cell.column for cell in next(sheet.iter_rows(min_row=1, max_row=1)) if cell.value}

    # Mulai memasukkan data dari baris kedua
    row_idx = 2  
    for _, row in data.iterrows():
        for csv_col, excel_col in column_mapping.items():
            if csv_col in data.columns and excel_col in excel_columns:
                col_idx = excel_columns[excel_col]  # Ambil posisi kolom di Excel berdasarkan header
                sheet.cell(row=row_idx, column=col_idx, value=row[csv_col])
        row_idx += 1

    # Simpan hasil ke memori
    output = io.BytesIO()
    book.save(output)
    output.seek(0)

    return output, None

# ============================ STREAMLIT UI ============================ #

st.title("Ekstrak Data CSV ke Template Excel")

# **Upload file CSV**
uploaded_csv = st.file_uploader("Upload file CSV", type=["csv"])

# **Upload Template Excel**
uploaded_template = st.file_uploader("Upload Template Excel", type=["xlsx"])

if uploaded_csv and uploaded_template:
    # Membaca CSV
    data = pd.read_csv(uploaded_csv)

    # Pilih sheet dalam template Excel
    book = load_workbook(io.BytesIO(uploaded_template.getvalue()))
    sheet_name = st.selectbox("Pilih Sheet untuk Menyimpan Data", book.sheetnames)

    # Ambil kolom dari Excel (header baris pertama)
    sheet = book[sheet_name]
    excel_columns = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1)) if cell.value]

    # Ambil kolom dari CSV
    csv_columns = data.columns.tolist()

    # Mapping kolom CSV ke kolom Excel
    column_mapping = {}
    st.write("Cocokkan kolom CSV dengan kolom di Excel:")
    for csv_col in csv_columns:
        excel_col = st.selectbox(f"Pilih kolom Excel untuk `{csv_col}`", ["(Tidak digunakan)"] + excel_columns, key=csv_col)
        if excel_col != "(Tidak digunakan)":
            column_mapping[csv_col] = excel_col

    # Pilih kategori jika ada
    selected_category = "Semua"
    if "Segment_Category" in data.columns:
        kategori_unik = ["Semua"] + sorted(data["Segment_Category"].dropna().unique().tolist())
        selected_category = st.selectbox("Pilih Kategori", kategori_unik)

    # Input nama file custom
    file_name = st.text_input("Masukkan nama file Excel (tanpa ekstensi)", "export_data")

    # Pastikan nama file tidak mengandung karakter tidak valid
    file_name = re.sub(r'[<>:"/\\|?*]', '', file_name).strip()  # Hapus karakter tidak valid

    if st.button("Ekspor ke Template Excel"):
        output_excel, error = transform_csv_to_excel_with_mapping(
            uploaded_csv, uploaded_template, column_mapping, selected_category, sheet_name
        )

        if error:
            st.error(error)
        else:
            # Tambahkan ekstensi .xlsx
            output_file_name = f"{file_name}.xlsx"

            st.download_button(
                label="Unduh File",
                data=output_excel,
                file_name=output_file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
