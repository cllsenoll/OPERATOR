import streamlit as st
import pandas as pd

# Sayfa ayarları
st.set_page_config(page_title="Kargo İşlem Takibi", layout="wide")

st.title("📦 Kargo İşlem Takip Paneli")
st.write("Lütfen 'TESLİM' adlı Excel dosyanızı yükleyin.")

# Dosya yükleme alanı
uploaded_file = st.file_uploader("Excel Dosyası Seçin", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Excel dosyasını oku
        df = pd.read_excel(uploaded_file)
        
        # Sütun adlarını kontrol et (Sizin dosyanızdaki başlığa göre düzenleyin)
        # Örneğin: 'İşlem Yapan Personel' sütununun adı dosyanızda tam olarak neyse onu kullanın
        personel_col = "İşlem Yapan Personel"
        
        if personel_col in df.columns:
            # Personel bazında sayım yap
            counts = df[personel_col].value_counts().reset_index()
            counts.columns = [personel_col, "Kargo Sayısı"]
            
            st.success("Dosya başarıyla yüklendi!")
            
            # Sonuçları göster
            st.subheader("Personel Bazında Kargo Sayıları")
            st.dataframe(counts, use_container_width=True)
            
            # Grafik olarak göster
            st.bar_chart(counts.set_index(personel_col))
            
        else:
            st.error(f"Hata: Excel dosyasında '{personel_col}' adında bir sütun bulunamadı. "
                     f"Lütfen sütun adını kontrol edin. Mevcut sütunlar: {list(df.columns)}")
            
    except Exception as e:
        st.error(f"Dosya işlenirken bir hata oluştu: {e}")
