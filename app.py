import base64
import io
import os
import re
import pandas as pd
import streamlit as st

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="Operatör - Kargo & Fatura Takibi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. OTURUM DURUMU (Session State)
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Ana Panel"
if "perf_df" not in st.session_state:
    st.session_state.perf_df = None
if "fatura_df" not in st.session_state:
    st.session_state.fatura_df = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "raw_fatura_df" not in st.session_state:
    st.session_state.raw_fatura_df = None

KULLANICI_ISIM = "Celal ŞENOL"
KULLANICI_GOREV = "Şube Şefi"

# ==========================================
# CSS VE MODERN GÖRSEL BİLEŞEN TASARIMLARI
# ==========================================
custom_css = """
<style>
    .notranslate {
        translate: no !important;
    }
    .stApp {
        background-color: #0B192C !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #1E3E62 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        height: 48px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, #00B4D8 0%, #0077B6 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #90E0EF !important;
        box-shadow: 0 6px 0 #03045E, 0 8px 10px rgba(0, 0, 0, 0.4) !important;
        margin-bottom: 10px !important;
        text-align: left !important;
        padding-left: 15px !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background: linear-gradient(135deg, #48CAE4 0%, #00B4D8 100%) !important;
    }
    
    /* Dosya Yükleme Alanı Tasarımı */
    [data-testid="stFileUploader"] section {
        background: linear-gradient(135deg, #FFD166 0%, #FFB703) !important;
        border: 2px dashed #FB8500 !important;
        border-radius: 12px !important;
    }
    [data-testid="stFileUploader"] section * {
        color: #000000 !important;
    }
    [data-testid="stFileUploader"] button {
        background: linear-gradient(135deg, #FFB703 0%, #FB8500) !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 0 #9E2A2B, 0 6px 8px rgba(0,0,0,0.3) !important;
    }

    .person-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .profile-section {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .avatar-circle {
        width: 62px;
        height: 62px;
        border-radius: 50%;
        border: 2px solid #FFB703;
        object-fit: cover;
        background-color: #1E3E62;
    }
    .person-name {
        font-size: 15px;
        font-weight: 700;
        color: #FFFFFF !important;
    }
    .metric-title {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .metric-value {
        font-size: 19px;
        font-weight: 700;
    }
    
    /* Dashboard Kartları */
    .dashboard-card {
        background: linear-gradient(135deg, #162A45 0%, #0B192C 100%);
        border: 1px solid rgba(255, 183, 3, 0.3);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    
    /* İlerleme Çubukları */
    .progress-container {
        background: rgba(255, 255, 255, 0.07);
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .progress-bar-bg {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        height: 10px;
        width: 100%;
        margin-top: 6px;
        overflow: hidden;
    }
    .progress-bar-fill-orange {
        background: linear-gradient(90deg, #FB8500 0%, #FFB703 100%);
        height: 100%;
        border-radius: 6px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ==========================================
# İSİM TEMİZLEME VE NORMALİZASYON
# ==========================================
def clean_string(text):
    if pd.isna(text) or not text:
        return ""
    text = str(text).upper().strip()
    replacements = {
        "İ": "I",
        "I": "I",
        "Ş": "S",
        "Ğ": "G",
        "Ü": "U",
        "Ö": "O",
        "Ç": "C",
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def norm_name(val):
    if pd.isna(val) or not val:
        return ""
    val_str = str(val).strip()
    if val_str.upper() in ["NAN", "NONE", "-", ""]:
        return ""
    
    cleaned = " ".join(val_str.upper().split())
    
    # Hatice IŞIK ve Hatice Kübra IŞIK ortak normalizasyonu
    if cleaned in ["HATICE ISIK", "HATICE KUBRA ISIK"]:
        return "HATICE KUBRA ISIK"
        
    return cleaned


# ==========================================
# OTOMATİK PERSONEL FOTOĞRAFI ALMA
# ==========================================
def get_courier_photo(courier_name):
    # Hatice IŞIK ve Hatice Kübra IŞIK için ortak arama adı türetelim
    if clean_string(courier_name) in ["HATICEISIK", "HATICEKUBRAISIK"]:
        courier_name = "Hatice Kübra IŞIK"

    clean_courier = clean_string(courier_name)
    search_dirs = []
    if os.path.exists("kuryeler"):
        search_dirs.append("kuryeler")
    search_dirs.append(".")

    for target_dir in search_dirs:
        try:
            files = os.listdir(target_dir)
            for file in files:
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower().replace(".", "")
                    if ext in ["png", "jpg", "jpeg", "webp"]:
                        file_name_clean = clean_string(os.path.splitext(file)[0])
                        if file_name_clean == clean_courier:
                            try:
                                with open(file_path, "rb") as image_file:
                                    encoded_string = base64.b64encode(image_file.read()).decode()
                                    mime_type = "image/png" if ext == "png" else f"image/{ext}"
                                    return f"data:{mime_type};base64,{encoded_string}"
                            except Exception:
                                pass

            for file in files:
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower().replace(".", "")
                    if ext in ["png", "jpg", "jpeg", "webp"]:
                        file_name_clean = clean_string(os.path.splitext(file)[0])
                        if (
                            file_name_clean
                            and clean_courier
                            and (
                                file_name_clean in clean_courier
                                or clean_courier in file_name_clean
                            )
                        ):
                            try:
                                with open(file_path, "rb") as image_file:
                                    encoded_string = base64.b64encode(image_file.read()).decode()
                                    mime_type = "image/png" if ext == "png" else f"image/{ext}"
                                    return f"data:{mime_type};base64,{encoded_string}"
                            except Exception:
                                pass
        except Exception:
            continue

    return f"https://ui-avatars.com/api/?name={courier_name.replace(' ', '+')}&background=1E3E62&color=FFB703&bold=true&size=150"


# ==========================================
# AKILLI DOSYA OKUMA MOTORU
# ==========================================
def smart_read_file(uploaded_file):
    file_bytes = uploaded_file.getvalue()
    encodings = ["cp1254", "iso-8859-9", "utf-8-sig", "utf-8", "latin1"]
    separators = [";", ",", "\t", None]

    for enc in encodings:
        for sep in separators:
            try:
                engine_type = "python" if sep is None else None
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    sep=sep,
                    encoding=enc,
                    engine=engine_type,
                    on_bad_lines="skip",
                )
                if df is not None and len(df.columns) > 1 and len(df) > 0:
                    return df
            except Exception:
                continue

    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception:
        pass

    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
    except Exception:
        pass

    raise Exception(
        "Dosya yapısı çözümlenemedi. Lütfen dosyanın bozuk olmadığını kontrol edin."
    )


# ==========================================
# TESLİM DOSYASI İŞLEME MOTORU (TESLİM SAYISI)
# ==========================================
def process_teslim_data(df):
    df.columns = df.columns.astype(str).str.strip()
    target_col = "İşlem Yapan Personel"
    if target_col not in df.columns:
        return None, [target_col]

    valid_df = df[
        df[target_col].notna()
        & (df[target_col].astype(str).str.strip() != "")
        & (df[target_col].astype(str).str.strip().str.upper() != "NAN")
        & (df[target_col].astype(str).str.strip().str.upper() != "NONE")
    ].copy()

    valid_df["Norm_Personel"] = valid_df[target_col].apply(norm_name)
    personnel_groups = valid_df.groupby("Norm_Personel")

    summary = []
    for norm_p, p_df in personnel_groups:
        if norm_p == "HATICE KUBRA ISIK":
            p_name = "Hatice Kübra IŞIK"
        else:
            p_name = (
                p_df[target_col].mode()[0]
                if not p_df[target_col].mode().empty
                else norm_p
            )
            p_name = " ".join(str(p_name).split())
            
        teslim_cnt = len(p_df)

        summary.append({
            "Personel": p_name,
            "TESLİM SAYISI": teslim_cnt,
        })

    res_df = pd.DataFrame(summary)
    if not res_df.empty:
        res_df = res_df.sort_values(by="TESLİM SAYISI", ascending=False)
        res_df.index = range(1, len(res_df) + 1)

    return res_df, None


# ==========================================
# FATURA DOSYASI İŞLEME MOTORU (FATURA KESİM SAYISI)
# ==========================================
def process_fatura_data(df):
    df.columns = df.columns.astype(str).str.strip()
    target_col = "Kesen Personel Adı"
    if target_col not in df.columns:
        return None, [target_col]

    valid_df = df[
        df[target_col].notna()
        & (df[target_col].astype(str).str.strip() != "")
        & (df[target_col].astype(str).str.strip().str.upper() != "NAN")
        & (df[target_col].astype(str).str.strip().str.upper() != "NONE")
    ].copy()

    valid_df["Norm_Personel"] = valid_df[target_col].apply(norm_name)
    personnel_groups = valid_df.groupby("Norm_Personel")

    summary = []
    for norm_p, p_df in personnel_groups:
        if norm_p == "HATICE KUBRA ISIK":
            p_name = "Hatice Kübra IŞIK"
        else:
            p_name = (
                p_df[target_col].mode()[0]
                if not p_df[target_col].mode().empty
                else norm_p
            )
            p_name = " ".join(str(p_name).split())
            
        fatura_cnt = len(p_df)

        summary.append({
            "Personel": p_name,
            "Fatura Kesim Sayısı": fatura_cnt,
        })

    res_df = pd.DataFrame(summary)
    if not res_df.empty:
        res_df = res_df.sort_values(by="Fatura Kesim Sayısı", ascending=False)
        res_df.index = range(1, len(res_df) + 1)

    return res_df, None


# ==========================================
# SIDEBAR VE GEZİNTİ MENÜSÜ
# ==========================================
with st.sidebar:
    st.markdown(
        """
    <div class="notranslate" style="text-align: center; padding-bottom: 10px;">
        <h2 style="margin: 0; color: #FFFFFF;">Operatör</h2>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='border: 1px solid rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="notranslate" style="background: linear-gradient(135deg, #FF7B00 0%, #FF5400 100%); border-radius: 12px; padding: 12px; margin-bottom: 15px; border: 1px solid #FFA200; box-shadow: 0 4px 8px rgba(255,123,0,0.3);">
        <small style="color: #FFFFFF; font-weight: 600;">Aktif Kullanıcı:</small><br>
        <strong style="color: #FFFFFF; font-size: 15px;">{KULLANICI_ISIM}</strong><br>
        <span style="color: #FFFFFF; font-size: 13px; font-weight: bold;">({KULLANICI_GOREV})</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    uploaded_teslim = st.file_uploader(
        "📂 TESLİM Dosyası Yükle", type=["xlsx", "xls", "csv"], key="teslim_file"
    )
    uploaded_fatura = st.file_uploader(
        "📂 FATURA Dosyası Yükle", type=["xlsx", "xls", "csv"], key="fatura_file"
    )

    st.markdown(
        "<hr style='border: 1px solid rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    if st.button("📊 Ana Panel"):
        st.session_state.active_tab = "Ana Panel"
    if st.button("👥 Personel"):
        st.session_state.active_tab = "Personel"
    if st.button("📄 Fatura"):
        st.session_state.active_tab = "Fatura"

# ==========================================
# AKILLI VERİ YÖNETİMİ
# ==========================================
if uploaded_teslim is not None:
    try:
        raw_df = smart_read_file(uploaded_teslim)
        st.session_state.raw_df = raw_df
        perf_res, err = process_teslim_data(raw_df)
        if err:
            st.error(f"❌ Eksik Sütun (Teslim): '{err[0]}' sütunu bulunamadı.")
        else:
            st.session_state.perf_df = perf_res
    except Exception as e:
        st.error(f"❌ Teslim Dosyası Okuma Hatası: {e}")

if uploaded_fatura is not None:
    try:
        raw_fatura_df = smart_read_file(uploaded_fatura)
        st.session_state.raw_fatura_df = raw_fatura_df
        fatura_res, err = process_fatura_data(raw_fatura_df)
        if err:
            st.error(f"❌ Eksik Sütun (Fatura): '{err[0]}' sütunu bulunamadı.")
        else:
            st.session_state.fatura_df = fatura_res
    except Exception as e:
        st.error(f"❌ Fatura Dosyası Okuma Hatası: {e}")

# ==========================================
# TAB 1: ANA PANEL
# ==========================================
if st.session_state.active_tab == "Ana Panel":
    st.title("📊 Operatör - Genel Performans Özeti")

    perf_df = st.session_state.perf_df
    fatura_df = st.session_state.fatura_df

    col1, col2 = st.columns(2)
    with col1:
        total_teslim = perf_df["TESLİM SAYISI"].sum() if perf_df is not None and not perf_df.empty else 0
        st.metric("📦 Toplam Teslim Sayısı", f"{total_teslim:,}")
    with col2:
        total_fatura = fatura_df["Fatura Kesim Sayısı"].sum() if fatura_df is not None and not fatura_df.empty else 0
        st.metric("📄 Toplam Fatura Kesim Sayısı", f"{total_fatura:,}")

    st.markdown("---")

    if perf_df is not None and not perf_df.empty:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(
            "<h3 style='color: #FFB703 !important; margin-bottom: 20px;'>📊 Personel Bazlı Teslim Sayısı Dağılımı</h3>",
            unsafe_allow_html=True,
        )

        c_sol, c_sag = st.columns([1, 2])
        with c_sol:
            max_p = perf_df.iloc[0] if not perf_df.empty else None
            max_name = max_p["Personel"] if max_p is not None else "-"
            max_val = max_p["TESLİM SAYISI"] if max_p is not None else 0
            max_avatar_url = get_courier_photo(max_name) if max_p is not None else ""

            st.markdown(
                f"""
                <div style="padding: 5px 0;" class="notranslate">
                    <div class="stat-label">En Çok Teslimat Yapan Personel</div>
                    <div style="display: flex; align-items: center; gap: 20px; margin-top: 12px; margin-bottom: 18px;">
                        <img src="{max_avatar_url}" style="width: 110px; height: 110px; border-radius: 50%; border: 4px solid #FFB703; object-fit: cover; background-color: #1E3E62;">
                        <div>
                            <div style="font-size: 22px; font-weight: bold; color: #FFFFFF; line-height: 1.3;">{max_name}</div>
                            <div style="font-size: 32px; font-weight: 800; color: #FFB703; margin-top: 6px;">{max_val} Adet</div>
                        </div>
                    </div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with c_sag:
            bars_html = ""
            for _, r in perf_df.iterrows():
                p_adi = r["Personel"]
                p_adet = r["TESLİM SAYISI"]
                yuzde = round((p_adet / total_teslim) * 100, 1) if total_teslim > 0 else 0
                bars_html += f"""
                    <div class="progress-container notranslate">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600;">
                            <span>{p_adi}</span>
                            <span style="color: #FFB703;">{p_adet} Adet (%{yuzde})</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill-orange" style="width: {min(yuzde * 2, 100)}%;"></div>
                        </div>
                    </div>
                    """
            st.markdown(bars_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("💡 Sol menüden **TESLİM** dosyanızı yükleyerek teslimat panellerini etkinleştirebilirsiniz.")

# ==========================================
# TAB 2: PERSONEL PANELİ (TESLİMAT)
# ==========================================
elif st.session_state.active_tab == "Personel":
    st.title("👥 Personel Paneli (Teslimat)")

    perf_df = st.session_state.perf_df
    if perf_df is not None and not perf_df.empty:
        st.success(f"✅ TESLİM raporu aktif. Toplam **{len(perf_df)}** personel bulundu.")

        all_personnel = ["Tümü"] + sorted(perf_df["Personel"].dropna().unique().tolist())
        selected_personnel = st.selectbox("🔍 Personel Seçerek Süzgeçle:", all_personnel)

        filtered_perf_df = perf_df if selected_personnel == "Tümü" else perf_df[perf_df["Personel"] == selected_personnel]

        for idx, row in filtered_perf_df.iterrows():
            p_name = row["Personel"]
            teslim_sayisi = row["TESLİM SAYISI"]
            avatar_url = get_courier_photo(p_name)

            card_html = f"""
            <div class="person-card notranslate">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                    <div class="profile-section" style="min-width: 220px;">
                        <img src="{avatar_url}" class="avatar-circle">
                        <div>
                            <div class="person-name">{p_name}</div>
                            <small style="color: #FFB703;">Saha Personeli</small>
                        </div>
                    </div>
                    <div style="text-align: center; margin-right: 20px;">
                        <div class="metric-title">TESLİM SAYISI</div>
                        <div class="metric-value" style="color: #4CAF50; font-size: 24px;">{teslim_sayisi} Adet</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        st.subheader("📋 Teslimat Performans Tablosu")
        st.dataframe(perf_df, use_container_width=True)
    else:
        st.warning("⚠️ Personel teslimat kartlarını görmek için sol menüden **TESLİM** dosyasını yükleyin.")

# ==========================================
# TAB 3: FATURA PANELİ
# ==========================================
elif st.session_state.active_tab == "Fatura":
    st.title("📄 Fatura Kesim Paneli")

    fatura_df = st.session_state.fatura_df
    if fatura_df is not None and not fatura_df.empty:
        total_fatura = fatura_df["Fatura Kesim Sayısı"].sum()
        toplam_personel_fatura = len(fatura_df)

        c1, c2 = st.columns(2)
        c1.metric("📄 Toplam Fatura Kesim Sayısı", f"{total_fatura:,}")
        c2.metric("👥 Fatura Kesen Personel Sayısı", f"{toplam_personel_fatura:,}")

        st.markdown("---")

        all_personnel = ["Tümü"] + sorted(fatura_df["Personel"].dropna().unique().tolist())
        selected_personnel = st.selectbox("🔍 Personel Seçerek Süzgeçle (Fatura):", all_personnel)

        filtered_fatura_df = fatura_df if selected_personnel == "Tümü" else fatura_df[fatura_df["Personel"] == selected_personnel]

        for idx, row in filtered_fatura_df.iterrows():
            p_name = row["Personel"]
            fatura_sayisi = row["Fatura Kesim Sayısı"]
            avatar_url = get_courier_photo(p_name)

            card_html = f"""
            <div class="person-card notranslate">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                    <div class="profile-section" style="min-width: 220px;">
                        <img src="{avatar_url}" class="avatar-circle">
                        <div>
                            <div class="person-name">{p_name}</div>
                            <small style="color: #FFB703;">Operasyon Personeli</small>
                        </div>
                    </div>
                    <div style="text-align: center; margin-right: 20px;">
                        <div class="metric-title">FATURA KESİM SAYISI</div>
                        <div class="metric-value" style="color: #00B4D8; font-size: 24px;">{fatura_sayisi} Adet</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        st.subheader("📋 Fatura Kesim Performans Tablosu")
        st.dataframe(fatura_df, use_container_width=True)
    else:
        st.warning("⚠️ Fatura kartlarını ve analizini görmek için sol menüden **FATURA** dosyasını yükleyin.")
