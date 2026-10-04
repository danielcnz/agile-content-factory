import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
import re
import numpy as np
from datetime import datetime
import io
import zipfile
import requests

# --- FUNCIONES TÉCNICAS ---

def validar_licencia_lemonsqueezy(license_key):
    if not license_key:
        return False
    
    # 1. Validación prioritaria con los Secrets de Streamlit (Modo Administrador)
    try:
        clave_maestra = st.secrets.get("DEV_KEY", "")
        if clave_maestra and license_key.strip() == str(clave_maestra).strip():
            return True
    except Exception:
        pass

    # 2. Validación con Lemon Squeezy (si la clave no es la de administrador)
    try:
        url = "https://api.lemonsqueezy.com/v1/licenses/validate"
        res = requests.post(url, data={"license_key": license_key.strip()}, timeout=5)
        data = res.json()
        return data.get("valid", False)
    except Exception:
        return False

def aplicar_marca_agua_centrada(img_base, texto="AGILE CONTENT FACTORY - FREE"):
    """Estampa una marca de agua de alta visibilidad con fondo semitransparente."""
    ancho, alto = img_base.size
    
    capa_wm = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw_wm = ImageDraw.Draw(capa_wm)
    
    tamano_wm = int(ancho * 0.065)
    try:
        font_wm = ImageFont.truetype("Roboto-Bold.ttf", tamano_wm)
    except Exception:
        font_wm = ImageFont.load_default()
        
    bbox = draw_wm.textbbox((0, 0), texto, font=font_wm)
    w_t = bbox[2] - bbox[0]
    h_t = bbox[3] - bbox[1]
    
    pad_x, pad_y = 40, 20
    ancho_badge = w_t + (pad_x * 2)
    alto_badge = h_t + (pad_y * 2)
    
    # Placa o cinta con fondo oscuro translúcido y texto blanco nítido
    img_texto = Image.new("RGBA", (ancho_badge, alto_badge), (0, 0, 0, 0))
    draw_txt = ImageDraw.Draw(img_texto)
    
    # Fondo rectangular oscuro semitransparente detrás del texto
    draw_txt.rounded_rectangle(
        [(0, 0), (ancho_badge, alto_badge)],
        radius=18,
        fill=(15, 23, 42, 175),       # Azul noche oscuro con buena opacidad
        outline=(255, 255, 255, 120), # Borde fino blanco
        width=2
    )
    
    # Texto blanco de alto contraste
    draw_txt.text((pad_x, pad_y), texto, font=font_wm, fill=(255, 255, 255, 230))
    
    # Rotación en ángulo diagonal
    texto_rotado = img_texto.rotate(22, expand=True, resample=Image.Resampling.BICUBIC)
    
    pos_x = (ancho - texto_rotado.width) // 2
    pos_y = (alto - texto_rotado.height) // 2
    capa_wm.paste(texto_rotado, (pos_x, pos_y), texto_rotado)
    
    return Image.alpha_composite(img_base, capa_wm)

def crear_degradado_rgb(ancho, alto, c1_hex, c2_hex):
    c1 = tuple(int(c1_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    c2 = tuple(int(c2_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    base = np.zeros((alto, ancho, 3), dtype=np.uint8)
    for i in range(3):
        base[:, :, i] = np.linspace(c1[i], c2[i], alto).reshape(-1, 1)
    return Image.fromarray(base).convert("RGBA")

def dibujar_frase_estilizada(draw, frase, ancho, alto, f_reg, f_bold, c_pri, c_sec, modo_fuente):
    margen = int(ancho * 0.85)
    f_base = f_bold if modo_fuente == "Todo Bold" else f_reg
    f_destacada = f_bold if modo_fuente == "Todo Bold" else f_reg
    
    espacio = draw.textbbox((0, 0), " ", font=f_base)[2]
    ascent, descent = f_base.getmetrics()
    alto_linea = ascent + descent + 15

    tokens = re.split(r'(\[[^\]]+\])', frase)
    palabras_data = []
    for t in tokens:
        if t.startswith('[') and t.endswith(']'):
            palabras_data.append({'texto': t[1:-1], 'font': f_destacada, 'color': c_sec})
        elif t.strip():
            for p in t.split():
                palabras_data.append({'texto': p, 'font': f_base, 'color': c_pri})

    lineas, linea_act, ancho_acum = [], [], 0
    for p in palabras_data:
        ancho_p = draw.textbbox((0, 0), p['texto'], font=p['font'])[2]
        if ancho_acum + ancho_p <= margen:
            linea_act.append(p)
            ancho_acum += ancho_p + espacio
        else:
            lineas.append(linea_act)
            linea_act, ancho_acum = [p], ancho_p + espacio
    if linea_act:
        lineas.append(linea_act)

    if not lineas:
        return

    y_act = (alto - (len(lineas) * alto_linea)) // 2
    for linea in lineas:
        ancho_l = sum(draw.textbbox((0, 0), p['texto'], font=p['font'])[2] for p in linea) + (espacio * (len(linea)-1))
        x_act = (ancho - ancho_l) // 2
        for p in linea:
            draw.text((x_act, y_act), p['texto'], font=p['font'], fill=p['color'])
            x_act += draw.textbbox((0, 0), p['texto'], font=p['font'])[2] + espacio
        y_act += alto_linea

# --- INTERFAZ ---
st.set_page_config(page_title="Agile Content Factory Pro", layout="wide")

st.markdown("""
<style>
    /* Tipografía y espaciado general */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Barra lateral moderna */
    [data-testid="stSidebar"] {
        background-color: #0f172a; /* Fondo pizarra oscuro elegante */
        color: #f8fafc;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #f1f5f9 !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    [data-testid="stSidebar"] label {
        color: #cbd5e1 !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }

    /* Estilo de la caja de llamada a la acción en la barra lateral */
    .upgrade-card {
        background: linear-gradient(135deg, rgba(234, 88, 12, 0.15) 0%, rgba(249, 115, 22, 0.05) 100%);
        border: 1px solid rgba(249, 115, 22, 0.35);
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .upgrade-card p {
        color: #fed7aa;
        font-size: 0.85rem;
        margin-bottom: 10px;
    }
    .upgrade-btn {
        display: block;
        text-align: center;
        background: linear-gradient(90deg, #ea580c, #f97316);
        color: #ffffff !important;
        font-weight: 700;
        font-size: 0.9rem;
        padding: 10px 14px;
        border-radius: 8px;
        text-decoration: none;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.3);
        transition: transform 0.15s ease;
    }
    .upgrade-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(234, 88, 12, 0.4);
    }

    /* Encabezado principal */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Botón de descarga principal destacado */
    .stDownloadButton button {
        background: linear-gradient(90deg, #2563eb, #1d4ed8) !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.75rem 2rem !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # --- CONTROL DE LICENCIA PRO ---
    st.markdown("### ⚙️ Configuración")
    
    st.markdown("#### 👑 Estado de Licencia")
    licencia_input = st.text_input("Ingresa tu clave de acceso", type="password", placeholder="Pegar clave aquí...")
    
    es_pro = validar_licencia_lemonsqueezy(licencia_input)
    
    if es_pro:
        st.success("🌟 **Modo Pro Activo**\nDescargas limpias y hasta 100 posts.")
        limite_maximo = 100
        default_posts = 10
    else:
        # Aquí se dibuja la tarjeta moderna en vez del enlace plano st.markdown(...)
        st.markdown("""
        <div class="upgrade-card">
            <p><strong>Versión Demo activa</strong><br>Máximo 3 posts con marca de agua central.</p>
            <a href="https://lemonsqueezy.com" target="_blank" class="upgrade-btn">
                ⚡ Desbloquear Modo Pro
            </a>
        </div>
        """, unsafe_allow_html=True)
        limite_maximo = 3
        default_posts = 3
        
    st.divider()

    st.subheader("1. Formato")
    formato = st.radio("Tamaño del Post", ["1080x1080 (Cuadrado)", "1080x1350 (Retrato)"])
    ancho, alto = (1080, 1080) if "1080x1080" in formato else (1080, 1350)
    
    st.subheader("2. Identidad (Opcional)")
    logo_file = st.file_uploader("Logo (PNG transparente)", type=["png"])
    tamano_logo = st.slider("Tamaño Logo", 50, 400, 180) if logo_file else 0
    
    st.subheader("3. Fondo")
    tipo_bg = st.radio("Tipo", ["Color Plano", "Degradado", "Plantilla"])
    if tipo_bg == "Plantilla":
        bg_file = st.file_uploader("Sube Imagen", type=["png", "jpg"])
    elif tipo_bg == "Color Plano":
        bg_color = st.color_picker("Fondo", "#1E1E1E")
    else:
        c1 = st.color_picker("Color Superior", "#4facfe")
        c2 = st.color_picker("Color Inferior", "#00f2fe")

    st.subheader("4. Texto")
    modo_fuente = st.radio("Estilo", ["Todo Regular", "Todo Bold"])
    c_pri = st.color_picker("Color Base", "#FFFFFF")
    c_sec = st.color_picker("Color Destacado", "#FFD700")
    tamano_f = st.slider("Tamaño Letra", 40, 150, 85)
    
    num_posts = st.number_input("Cantidad a procesar", 1, limite_maximo, default_posts)

st.markdown('<div class="main-title">🚀 Agile Content Factory</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Diseña y genera lotes de imágenes optimizadas para redes sociales en segundos.</div>', unsafe_allow_html=True)
frases_bulk = st.text_area("Frases (una por línea):", "Automatiza tu [negocio]\nUsa [Python] hoy\nMarketing [inteligente]", height=150)

fondo_listo = (tipo_bg == "Plantilla" and bg_file is not None) or tipo_bg != "Plantilla"

if fondo_listo:
    lista_frases = [f.strip() for f in frases_bulk.split('\n') if f.strip()][:num_posts]
    
    archivo_fuente_regular = "Roboto-Regular.ttf"
    archivo_fuente_bold = "Roboto-Bold.ttf"

    if os.path.exists(archivo_fuente_regular) and os.path.exists(archivo_fuente_bold):
        f_reg = ImageFont.truetype(archivo_fuente_regular, tamano_f)
        f_bold = ImageFont.truetype(archivo_fuente_bold, tamano_f)
    else:
        st.sidebar.warning("⚠️ No se encontraron los archivos .ttf en la carpeta. Usando fuente del sistema.")
        f_reg = f_bold = ImageFont.load_default()

    st.header(f"🖼️ Vista Previa ({formato})")
    cols = st.columns(3)
    imagenes_finales = []

    for i, frase in enumerate(lista_frases):
        if tipo_bg == "Plantilla" and bg_file:
            img = Image.open(bg_file).convert("RGBA").resize((ancho, alto))
        elif tipo_bg == "Color Plano":
            img = Image.new("RGBA", (ancho, alto), bg_color)
        else:
            img = crear_degradado_rgb(ancho, alto, c1, c2)

        draw = ImageDraw.Draw(img)
        dibujar_frase_estilizada(draw, frase, ancho, alto, f_reg, f_bold, c_pri, c_sec, modo_fuente)
        
        if logo_file:
            logo_img = Image.open(logo_file).convert("RGBA")
            logo_img.thumbnail((tamano_logo, tamano_logo))
            img.paste(logo_img, (ancho - tamano_logo - 40, alto - tamano_logo - 40), logo_img)
        
        # Inyección de marca de agua central si no es Pro
        if not es_pro:
            img = aplicar_marca_agua_centrada(img, texto="AGILE CONTENT FACTORY - FREE")
        
        imagenes_finales.append(img)
        with cols[i % 3]:
            st.image(img, caption=f"Post {i+1}", use_container_width=True)

    st.divider()
    
    if imagenes_finales:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, img_save in enumerate(imagenes_finales):
                img_bytes_buffer = io.BytesIO()
                img_save.save(img_bytes_buffer, format="PNG")
                img_bytes_buffer.seek(0)
                
                nombre_archivo = f"post_{timestamp}_{idx+1}.png"
                zip_file.writestr(nombre_archivo, img_bytes_buffer.getvalue())
        
        zip_buffer.seek(0)
        
        st.download_button(
            label=f"💾 DESCARGAR LOS {len(imagenes_finales)} POSTS EN .ZIP",
            data=zip_buffer,
            file_name=f"content_factory_tanda_{timestamp}.zip",
            mime="application/zip",
            use_container_width=True
        )
else:
    st.info("💡 Selecciona un color de fondo o sube una plantilla para comenzar.")
