import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ========================================
# KONFIGURASI HALAMAN
# ========================================
st.set_page_config(
    page_title="ANALISA MARGIN ILMI GRUB",
    page_icon="📊",
    layout="wide"
)

# ========================================
# CUSTOM CSS
# ========================================
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #FF6B00 0%, #FFB800 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #FF6B00;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px;
        margin: 10px 0;
    }
    .danger-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ========================================
# HEADER
# ========================================
st.markdown("""
    <div class="main-header">
        <h1>📊 ANALISIS MARGIN ILMI GRUB</h1>
        <h3>Ilmimart - Pusat Kontrol Harga & Profitabilitas</h3>
    </div>
""", unsafe_allow_html=True)

# ========================================
# FUNGSI PEMBERSIHAN DATA
# ========================================
def clean_numeric_column(series, column_name):
    """
    Membersihkan kolom numerik dari format Indonesia dan nilai non-numerik
    """
    if series.dtype == 'object':
        # Hapus titik pemisah ribuan dan ganti koma dengan titik
        series = series.astype(str).str.replace('.', '', regex=False)
        series = series.str.replace(',', '.', regex=False)
        series = series.str.strip()
        
        # Konversi ke numeric, set error menjadi NaN
        series = pd.to_numeric(series, errors='coerce')
    
    return series

def load_and_clean_data(uploaded_file):
    """
    Load data dari file Excel/CSV dan bersihkan
    """
    try:
        # Baca file
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=0)
        
        # Deteksi nama kolom (case-insensitive)
        columns_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'nama' in col_lower and 'item' in col_lower:
                columns_map['Nama Item'] = col
            elif 'modal' in col_lower and 'ilmimart' in col_lower:
                columns_map['Harga Modal Ilmimart'] = col
            elif 'harga' in col_lower and 'jual' in col_lower and 'modal' not in col_lower:
                columns_map['Harga Jual'] = col
            elif 'kode' in col_lower:
                columns_map['Kode Item'] = col
            elif 'stok' in col_lower:
                columns_map['Stok'] = col
            elif 'satuan' in col_lower:
                columns_map['Satuan'] = col
        
        # Rename kolom
        df = df.rename(columns=columns_map)
        
        # Pastikan kolom wajib ada
        required_cols = ['Nama Item', 'Harga Modal Ilmimart', 'Harga Jual']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Kolom berikut tidak ditemukan: {', '.join(missing_cols)}")
            st.info("💡 Pastikan file Excel memiliki kolom: Nama Item, Harga Modal Ilmimart, dan Harga Jual")
            return None
        
        # Bersihkan kolom numerik
        df['Harga Modal Ilmimart'] = clean_numeric_column(df['Harga Modal Ilmimart'], 'Harga Modal Ilmimart')
        df['Harga Jual'] = clean_numeric_column(df['Harga Jual'], 'Harga Jual')
        
        # Filter baris dengan nilai valid
        original_rows = len(df)
        df = df.dropna(subset=['Harga Modal Ilmimart', 'Harga Jual'])
        df = df[df['Harga Modal Ilmimart'] > 0]
        df = df[df['Harga Jual'] > 0]
        
        dropped_rows = original_rows - len(df)
        if dropped_rows > 0:
            st.warning(f"⚠️ {dropped_rows} baris dihapus karena data tidak valid (nilai 0, kosong, atau teks)")
        
        return df
    
    except Exception as e:
        st.error(f"❌ Error membaca file: {str(e)}")
        return None

# ========================================
# FUNGSI KALKULASI MARGIN
# ========================================
def calculate_margin_analysis(df, target_margin):
    """
    Menghitung margin saat ini dan rekomendasi harga baru
    """
    # 1. Margin Saat Ini (%)
    df['Margin Saat Ini (%)'] = ((df['Harga Jual'] - df['Harga Modal Ilmimart']) / df['Harga Jual'] * 100)
    
    # 2. Harga Jual Baru (berdasarkan target margin)
    df['Harga Jual Baru'] = df['Harga Modal Ilmimart'] / (1 - (target_margin / 100))
    
    # 3. Selisih Harga
    df['Selisih Harga'] = df['Harga Jual Baru'] - df['Harga Jual']
    
    # 4. Margin Baru (setelah penyesuaian)
    df['Margin Baru (%)'] = target_margin
    
    # 5. Saran Bisnis
    def get_recommendation(row):
        margin = row['Margin Saat Ini (%)']
        if pd.isna(margin):
            return "DATA TIDAK VALID"
        elif margin < target_margin:
            return "🔴 NAIKKAN HARGA"
        elif margin > (target_margin + 10):
            return "🟡 HARGA KOMPETITIF (Bisa Turunkan Sedikit)"
        else:
            return "🟢 PERTAHANKAN"
    
    df['Aksi'] = df.apply(get_recommendation, axis=1)
    
    # 6. Status Margin
    def get_status(row):
        margin = row['Margin Saat Ini (%)']
        if pd.isna(margin):
            return "Invalid"
        elif margin < target_margin:
            return "Di Bawah Target"
        elif margin > (target_margin + 10):
            return "Terlalu Tinggi"
        else:
            return "Aman"
    
    df['Status Margin'] = df.apply(get_status, axis=1)
    
    return df

# ========================================
# FUNGSI FORMAT CURRENCY
# ========================================
def format_currency(value):
    """Format angka ke format Rupiah"""
    if pd.isna(value):
        return "Rp 0"
    return f"Rp {value:,.0f}".replace(',', '.')

def format_percentage(value):
    """Format angka ke persentase"""
    if pd.isna(value):
        return "0.00%"
    return f"{value:.2f}%"

# ========================================
# SIDEBAR - UPLOAD & SETTINGS
# ========================================
st.sidebar.image("https://via.placeholder.com/300x100/FF6B00/FFFFFF?text=ILMIMART", use_container_width=True)
st.sidebar.markdown("---")

st.sidebar.header("⚙️ Pengaturan")

# Upload File
uploaded_file = st.sidebar.file_uploader(
    "📁 Upload File Excel/CSV",
    type=['xlsx', 'xls', 'csv'],
    help="Upload file dengan kolom: Nama Item, Harga Modal Ilmimart, Harga Jual"
)

# Target Margin Slider
target_margin = st.sidebar.slider(
    "🎯 Target Margin Global (%)",
    min_value=0,
    max_value=50,
    value=10,
    step=1,
    help="Tentukan target margin keuntungan yang diinginkan"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
    <div class="metric-card">
        <h4>Target Margin Aktif</h4>
        <h2 style='color: #FF6B00;'>{target_margin}%</h2>
    </div>
""", unsafe_allow_html=True)

# ========================================
# MAIN CONTENT
# ========================================

if uploaded_file is None:
    # Tampilan awal jika belum ada file
    st.info("👈 Silakan upload file Excel/CSV di sidebar untuk memulai analisis")
    
    st.markdown("### 📋 Format File yang Dibutuhkan:")
    st.markdown("""
    File Excel/CSV harus memiliki kolom berikut:
    - **Nama Item** (atau Nama Barang)
    - **Harga Modal Ilmimart** (atau Modal Ilmimart)
    - **Harga Jual** (atau Harga Jual Ilmimart)
    
    Kolom opsional:
    - Kode Item
    - Stok
    - Satuan
    """)
    
    st.markdown("### 📊 Fitur Aplikasi:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="success-box">
            <h4>✅ Kalkulasi Otomatis</h4>
            <ul>
                <li>Margin saat ini</li>
                <li>Harga jual baru</li>
                <li>Selisih harga</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="warning-box">
            <h4>⚡ Rekomendasi Cerdas</h4>
            <ul>
                <li>Naikkan harga</li>
                <li>Pertahankan</li>
                <li>Turunkan sedikit</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="danger-box">
            <h4>📥 Export Data</h4>
            <ul>
                <li>Download Excel</li>
                <li>Filter by status</li>
                <li>Laporan lengkap</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

else:
    # Load dan proses data
    df = load_and_clean_data(uploaded_file)
    
    if df is not None and len(df) > 0:
        # Kalkulasi margin
        df_result = calculate_margin_analysis(df.copy(), target_margin)
        
        # ========================================
        # RINGKASAN STATISTIK
        # ========================================
        st.markdown("## 📈 Ringkasan Analisis")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_items = len(df_result)
            st.metric("Total Item", f"{total_items:,}")
        
        with col2:
            below_target = len(df_result[df_result['Status Margin'] == 'Di Bawah Target'])
            st.metric("Di Bawah Target", f"{below_target:,}", delta=f"-{below_target/total_items*100:.1f}%", delta_color="inverse")
        
        with col3:
            safe_margin = len(df_result[df_result['Status Margin'] == 'Aman'])
            st.metric("Margin Aman", f"{safe_margin:,}", delta=f"{safe_margin/total_items*100:.1f}%")
        
        with col4:
            too_high = len(df_result[df_result['Status Margin'] == 'Terlalu Tinggi'])
            st.metric("Terlalu Tinggi", f"{too_high:,}", delta=f"{too_high/total_items*100:.1f}%")
        
        st.markdown("---")
        
        # ========================================
        # FILTER OPTIONS
        # ========================================
        st.markdown("## 🔍 Filter Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status Margin",
                options=['Semua'] + df_result['Status Margin'].unique().tolist(),
                default=['Semua']
            )
        
        with col2:
            aksi_filter = st.multiselect(
                "Rekomendasi Aksi",
                options=['Semua'] + df_result['Aksi'].unique().tolist(),
                default=['Semua']
            )
        
        with col3:
            show_rows = st.selectbox(
                "Tampilkan Baris",
                options=[10, 25, 50, 100, 'Semua'],
                index=1
            )
        
        # Apply filters
        df_filtered = df_result.copy()
        
        if 'Semua' not in status_filter:
            df_filtered = df_filtered[df_filtered['Status Margin'].isin(status_filter)]
        
        if 'Semua' not in aksi_filter:
            df_filtered = df_filtered[df_filtered['Aksi'].isin(aksi_filter)]
        
        st.markdown("---")
        
        # ========================================
        # TABEL HASIL
        # ========================================
        st.markdown("## 📊 Hasil Analisis Detail")
        
        # Pilih kolom yang akan ditampilkan
        display_columns = ['Nama Item', 'Harga Modal Ilmimart', 'Harga Jual', 
                          'Margin Saat Ini (%)', 'Harga Jual Baru', 'Selisih Harga', 
                          'Status Margin', 'Aksi']
        
        # Tambahkan kolom opsional jika ada
        if 'Kode Item' in df_filtered.columns:
            display_columns.insert(0, 'Kode Item')
        if 'Stok' in df_filtered.columns:
            display_columns.append('Stok')
        if 'Satuan' in df_filtered.columns:
            display_columns.append('Satuan')
        
        df_display = df_filtered[display_columns].copy()
        
        # Limit rows
        if show_rows != 'Semua':
            df_display = df_display.head(show_rows)
        
        # Styling function
        def highlight_rows(row):
            if row['Status Margin'] == 'Di Bawah Target':
                return ['background-color: #f8d7da'] * len(row)
            elif row['Status Margin'] == 'Terlalu Tinggi':
                return ['background-color: #fff3cd'] * len(row)
            else:
                return ['background-color: #d4edda'] * len(row)
        
        # Format angka
        format_dict = {
            'Harga Modal Ilmimart': lambda x: format_currency(x),
            'Harga Jual': lambda x: format_currency(x),
            'Harga Jual Baru': lambda x: format_currency(x),
            'Selisih Harga': lambda x: format_currency(x),
            'Margin Saat Ini (%)': lambda x: format_percentage(x)
        }
        
        # Tampilkan tabel dengan styling
        styled_df = df_display.style.apply(highlight_rows, axis=1).format(format_dict)
        
        st.dataframe(styled_df, use_container_width=True, height=600)
        
        st.markdown(f"*Menampilkan {len(df_display)} dari {len(df_filtered)} item (setelah filter)*")
        
        # ========================================
        # ANALISIS TAMBAHAN
        # ========================================
        st.markdown("---")
        st.markdown("## 💡 Insight & Rekomendasi")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔴 Item Perlu Kenaikan Harga")
            need_increase = df_result[df_result['Status Margin'] == 'Di Bawah Target'].sort_values('Margin Saat Ini (%)')
            
            if len(need_increase) > 0:
                top_5 = need_increase.head(5)[['Nama Item', 'Margin Saat Ini (%)', 'Selisih Harga']]
                top_5_formatted = top_5.copy()
                top_5_formatted['Margin Saat Ini (%)'] = top_5_formatted['Margin Saat Ini (%)'].apply(format_percentage)
                top_5_formatted['Selisih Harga'] = top_5_formatted['Selisih Harga'].apply(format_currency)
                st.dataframe(top_5_formatted, use_container_width=True)
                
                total_potential_revenue = need_increase['Selisih Harga'].sum()
                st.success(f"💰 Potensi Tambahan Revenue: **{format_currency(total_potential_revenue)}**")
            else:
                st.info("✅ Tidak ada item yang memerlukan kenaikan harga")
        
        with col2:
            st.markdown("### 🟡 Item dengan Margin Tertinggi")
            highest_margin = df_result.sort_values('Margin Saat Ini (%)', ascending=False).head(5)
            
            if len(highest_margin) > 0:
                top_margin = highest_margin[['Nama Item', 'Margin Saat Ini (%)', 'Harga Jual']]
                top_margin_formatted = top_margin.copy()
                top_margin_formatted['Margin Saat Ini (%)'] = top_margin_formatted['Margin Saat Ini (%)'].apply(format_percentage)
                top_margin_formatted['Harga Jual'] = top_margin_formatted['Harga Jual'].apply(format_currency)
                st.dataframe(top_margin_formatted, use_container_width=True)
                
                avg_margin = df_result['Margin Saat Ini (%)'].mean()
                st.info(f"📊 Rata-rata Margin: **{format_percentage(avg_margin)}**")
        
        # ========================================
        # DOWNLOAD BUTTON
        # ========================================
        st.markdown("---")
        st.markdown("## 📥 Download Hasil Analisis")
        
        # Siapkan data untuk export
        df_export = df_result.copy()
        
        # Format kolom untuk Excel
        df_export['Harga Modal Ilmimart'] = df_export['Harga Modal Ilmimart'].round(2)
        df_export['Harga Jual'] = df_export['Harga Jual'].round(0)
        df_export['Harga Jual Baru'] = df_export['Harga Jual Baru'].round(0)
        df_export['Selisih Harga'] = df_export['Selisih Harga'].round(0)
        df_export['Margin Saat Ini (%)'] = df_export['Margin Saat Ini (%)'].round(2)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Analisis Margin')
            
            # Auto-adjust columns' width
            worksheet = writer.sheets['Analisis Margin']
            for idx, col in enumerate(df_export.columns):
                max_length = max(
                    df_export[col].astype(str).map(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
        
        excel_data = output.getvalue()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.download_button(
                label="📊 Download Excel - Semua Data",
                data=excel_data,
                file_name=f"Analisis_Margin_Ilmimart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # Download hanya item yang perlu dinaikkan
            need_raise = df_result[df_result['Status Margin'] == 'Di Bawah Target']
            if len(need_raise) > 0:
                output_raise = BytesIO()
                with pd.ExcelWriter(output_raise, engine='openpyxl') as writer:
                    need_raise.to_excel(writer, index=False, sheet_name='Perlu Kenaikan')
                
                st.download_button(
                    label="🔴 Download - Perlu Naik",
                    data=output_raise.getvalue(),
                    file_name=f"Item_Perlu_Kenaikan_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col3:
            st.info(f"✅ {len(df_result)} item siap diexport")

# ========================================
# FOOTER
# ========================================
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>📊 <strong>Analisis Margin Ilmimart</strong> | Dikembangkan oleh <strong>NAUFAL MUZAQI</strong></p>
        <p style='font-size: 12px;'>© 2026 Ilmi Group - Solusi Cerdas Manajemen Harga & Margin</p>
    </div>
""", unsafe_allow_html=True)