# 📸 Instagram Scraper + Análisis IA

Herramienta de scraping para perfiles de Instagram que extrae métricas, comentarios y genera un informe profesional automático usando inteligencia artificial (Gemini API).

---

## ¿Qué hace?

- Extrae datos del perfil: nombre, biografía, seguidores, seguidos y total de publicaciones
- Analiza los últimos N posts: likes, engagement y tipo de post
- Recolecta comentarios reales de cada post con su autor
- Distingue posts propios de posts donde el usuario fue etiquetado
- Calcula el engagement rate promedio y lo compara con benchmarks del sector
- Genera un informe profesional completo con IA (Gemini)
- Exporta los resultados en `.txt` y `.csv`

---

## Requisitos

- Python 3.10+
- Google Chrome instalado
- Cuenta de Instagram abierta en Chrome
- API Key de Gemini (gratuita en [aistudio.google.com](https://aistudio.google.com))

---
## Instalación
 Instala las dependencias:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Uso

1. Abre Chrome con el puerto de depuración activado:

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\tmp\chrome_debug"
```

2. Inicia sesión en Instagram dentro de ese Chrome

3. Corre el scraper:

```bash
python scraper.py
```

4. Al terminar encontrarás los resultados en:

```
ENTREGA_FINAL_UCE_PERFECTA.txt
ENTREGA_FINAL_UCE_PERFECTA.csv
```

---

## Estructura del proyecto

```
📁 tu-repo/
├── scraper.py          # script principal
├── .env.example        # plantilla de variables de entorno
├── .gitignore          # excluye .env y archivos sensibles
├── requirements.txt    # dependencias del proyecto
└── README.md
```

---

## Informe generado por IA

El análisis incluye 6 secciones:

1. **Perfil del creador** — nicho y tipo de contenido
2. **Análisis de audiencia** — comportamiento de la comunidad
3. **Análisis de engagement** — interpretación de métricas
4. **Sentimiento de comentarios** — tono general (positivo/negativo/neutro)
5. **Fortalezas y oportunidades** — qué funciona y qué mejorar
6. **Conclusión general** — resumen para marcas o colaboraciones

---

## Dependencias principales

| Librería | Uso |
|---|---|
| `playwright` | Automatización del navegador |
| `python-dotenv` | Manejo seguro de variables de entorno |
| `requests` | Comunicación con la API de Gemini |

