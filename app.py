import streamlit as st
import pandas as pd

# Sayfa Genişliği
st.set_page_config(layout="wide", page_title="Kurye Performans Paneli")

st.title("📦 Kurye Performans Özeti")

# Dosya yükleme
uploaded_file = st.file_uploader("AT ZİMMET Raporu Yükle", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    # Dosya okuma (CSV ise ayrı, Excel ise ayrı işlem)
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # SÜTUN İSMİ AYARI: Excel'inizdeki sütun adını buraya yazın
    personel_col = "İşlem Yapan Personel" 
    
    if personel_col in df.columns:
        # Veriyi grupla: Personel ismine göre satır sayısını al
        performance_data = df.groupby(personel_col).size().reset_index(name='Toplam İşlem')
        
        st.success(f"AT ZİMMET İZLEME raporu aktif. Toplam {len(performance_data)} kurye bulundu.")
        
        # Filtreleme
        kuryeler = ["Tümü"] + list(performance_data[personel_col].unique())
        secilen = st.selectbox("Personel Seçerek Süzgeçle:", kuryeler)
        
        if secilen != "Tümü":
            performance_data = performance_data[performance_data[personel_col] == secilen]
            
        # Kartları Oluşturma
        for index, row in performance_data.iterrows():
            with st.container():
                # Kart tasarımı
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.subheader(row[personel_col])
                    st.caption("Saha Kuryesi")
                
                with col2:
                    st.metric("ZİMMET SAYISI", row['Toplam İşlem'])
                    
                with col3:
                    # Not: Teslim edilen kargo durumunu belirten bir sütun varsa burayı güncelleyebiliriz
                    st.metric("TESLİMAT SAYISI", row['Toplam İşlem'])
                    
                with col4:
                    st.metric("BAŞARI ORANI", "%100") # Örnek değer
                
                st.divider() # Kartlar arasına çizgi
                
    else:
        st.error(f"Dosyada '{personel_col}' sütunu bulunamadı. Lütfen sütun ismini kontrol edin.")
