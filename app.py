import streamlit as st
import os
from PIL import Image, ImageDraw, ImageFont
import re
import numpy as np
from datetime import datetime
import io       # <-- IMPORTANTE: Para manejar la memoria RAM
import zipfile  # <-- IMPORTANTE: Para empaquetar el lote en un archivo comprimido

# --- FUNCIONES TÉCNICAS ---

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
    lineas.append(linea_act)

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

with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("1. Formato")
    formato = st.radio("Tamaño del Post", ["1080x1080 (Cuadrado)", "1080x1350 (Retrato)"])
    ancho, alto = (1080, 1080) if "1080x1080" in formato else (1080, 1350)
    
    st.divider()
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
    
    num_posts = st.number_input("Cantidad a procesar", 1, 100, 3)

st.title("🚀 Agile Content Factory")
frases_bulk = st.text_area("Frases (una por línea):", "Automatiza tu [negocio]\nUsa [Python] hoy\nMarketing [inteligente]", height=150)

# Validación de fondo para mostrar previsualización
fondo_listo = (tipo_bg == "Plantilla" and bg_file is not None) or tipo_bg != "Plantilla"

if fondo_listo:
    lista_frases = [f.strip() for f in frases_bulk.split('\n') if f.strip()][:num_posts]
    
    try:
        # Nota: Si subes esto a la nube, asegúrate de que la ruta de la fuente sea compatible o usa una local en tu proyecto.
        f_reg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", tamano_f)
        f_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", tamano_f, index=1)
    except:
        f_reg = f_bold = ImageFont.load_default()

    st.header(f"🖼️ Vista Previa ({formato})")
    cols = st.columns(3)
    imagenes_finales = []

    for i, frase in enumerate(lista_frases):
        # Lógica de Fondo
        if tipo_bg == "Plantilla" and bg_file:
            img = Image.open(bg_file).convert("RGBA").resize((ancho, alto))
        elif tipo_bg == "Color Plano":
            img = Image.new("RGBA", (ancho, alto), bg_color)
        else:
            img = crear_degradado_rgb(ancho, alto, c1, c2)

        draw = ImageDraw.Draw(img)
        dibujar_frase_estilizada(draw, frase, ancho, alto, f_reg, f_bold, c_pri, c_sec, modo_fuente)
        
        # Logo (Solo si existe)
        if logo_file:
            logo_img = Image.open(logo_file).convert("RGBA")
            logo_img.thumbnail((tamano_logo, tamano_logo))
            img.paste(logo_img, (ancho - tamano_logo - 40, alto - tamano_logo - 40), logo_img)
        
        imagenes_finales.append(img)
        with cols[i % 3]:
            st.image(img, caption=f"Post {i+1}", use_container_width=True)

    # --- NUEVA LÓGICA DE EXPORTACIÓN DIRECTA AL DISCO DURO (COMPATIBLE CON GITHUB) ---
    st.divider()
    
    if imagenes_finales:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Crear un contenedor temporal en la memoria RAM para el archivo ZIP
        zip_buffer = io.BytesIO()
        
        # 2. Escribir las imágenes dentro del ZIP en memoria
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, img_save in enumerate(imagenes_finales):
                # Crear un buffer temporal de bytes para cada imagen individual
                img_bytes_buffer = io.BytesIO()
                img_save.save(img_bytes_buffer, format="PNG")
                img_bytes_buffer.seek(0)
                
                # Definir el nombre que tendrá la imagen dentro del paquete comprimido
                nombre_archivo = f"post_{timestamp}_{idx+1}.png"
                
                # Inyectar la imagen al archivo ZIP
                zip_file.writestr(nombre_archivo, img_bytes_buffer.getvalue())
        
        # 3. Colocar el puntero del buffer al inicio para que pueda ser leído completamente
        zip_buffer.seek(0)
        
        # 4. Botón nativo de Streamlit para descargar directo al equipo
        st.download_button(
            label=f"💾 DESCARGAR LOS {len(imagenes_finales)} POSTS EN .ZIP",
            data=zip_buffer,
            file_name=f"content_factory_tanda_{timestamp}.zip",
            mime="application/zip",
            use_container_width=True
        )
else:
    st.info("💡 Selecciona un color de fondo o sube una plantilla para comenzar.")