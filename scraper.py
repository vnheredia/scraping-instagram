import re
import csv
from playwright.sync_api import sync_playwright
import urllib.request
import json
from dotenv import load_dotenv
import os
import time

load_dotenv()
USUARIO_OBJETIVO = "macabeso"
NUM_POSTS = 10 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Falta GEMINI_API_KEY en el archivo .env")

# ════════════════════════════════════════════════════
#  FUNCIÓN: Engagement + Extras
# ════════════════════════════════════════════════════
def calcular_engagement(posts_data, seguidores_str):
    def parsear_numero(s):
        if s == "N/A" or not s: return 0
        s = s.replace(".", "").replace(",", ".").strip()
        match = re.search(r'([\d.]+)\s*([KkMm]?)', s)
        if not match: return 0
        num = float(match.group(1))
        sufijo = match.group(2).upper()
        if sufijo == "K": num *= 1_000
        if sufijo == "M": num *= 1_000_000
        return int(num)

    seguidores_n = parsear_numero(seguidores_str)
    stats = []
    contador_usuarios = {}

    for post in posts_data:
        likes_n = parsear_numero(post["likes"])
        es_propio = f"/{USUARIO_OBJETIVO}/" in post["url"]
        eng = round((likes_n / seguidores_n * 100), 4) if (seguidores_n > 0 and es_propio) else None
        stats.append({
            "num":        post["num"],
            "url":        post["url"],
            "likes":      likes_n,
            "engagement": eng,
            "es_propio":  es_propio
        })
        for c in post["comentarios"]:
            u = c["usuario"]
            contador_usuarios[u] = contador_usuarios.get(u, 0) + 1

    # Promedio solo con posts propios
    propios = [s for s in stats if s["es_propio"] and s["engagement"] is not None]
    eng_promedio = round(sum(s["engagement"] for s in propios) / len(propios), 4) if propios else 0
    likes_prom   = int(sum(s["likes"] for s in propios) / len(propios)) if propios else 0
    post_top     = max(propios, key=lambda x: x["likes"]) if propios else None

    if eng_promedio >= 6:     benchmark = "🔥 VIRAL (>6%)"
    elif eng_promedio >= 3:   benchmark = "⭐ Excelente (3-6%)"
    elif eng_promedio >= 1:   benchmark = "✅ Bueno (1-3%)"
    elif eng_promedio >= 0.5: benchmark = "⚠️ Promedio (0.5-1%)"
    else:                     benchmark = "❌ Bajo (<0.5%)"

    top_comentaristas = sorted(contador_usuarios.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "seguidores_n":      seguidores_n,
        "engagement_prom":   eng_promedio,
        "likes_prom":        likes_prom,
        "benchmark":         benchmark,
        "post_top":          post_top,
        "top_comentaristas": top_comentaristas,
        "stats_posts":       stats
    }


# ════════════════════════════════════════════════════
#  FUNCIÓN: Análisis IA con Gemini API
# ════════════════════════════════════════════════════
def analizar_con_ia(perfil, posts_data, engagement):
    print("\n🤖 Generando análisis con IA (Gemini)...")

    resumen_comentarios = ""
    for post in posts_data:
        resumen_comentarios += f"\nPost {post['num']} ({post['likes']} likes):\n"
        for c in post["comentarios"]:
            resumen_comentarios += f"  - @{c['usuario']}: {c['texto']}\n"

    top_c = ", ".join([f"@{u} ({n} veces)" for u, n in engagement["top_comentaristas"]])

    prompt = f"""Eres un experto en análisis de redes sociales e influencer marketing.
Analiza el siguiente perfil de Instagram y entrega un informe profesional en español.

=== DATOS DEL PERFIL ===
Usuario: @{perfil['usuario']}
Nombre: {perfil['nombre']}
Biografía: {perfil['biografia']}
Publicaciones totales: {perfil['posts']}
Seguidores: {perfil['seguidores']}
Seguidos: {perfil['seguidos']}

=== MÉTRICAS DE LOS ÚLTIMOS {NUM_POSTS} POSTS ===
Likes promedio: {engagement['likes_prom']}
Engagement rate promedio: {engagement['engagement_prom']}%
Benchmark: {engagement['benchmark']}
Post más viral: Post {engagement['post_top']['num']} con {engagement['post_top']['likes']} likes

=== COMENTARIOS RECOLECTADOS ===
{resumen_comentarios}

=== COMENTARISTAS MÁS ACTIVOS ===
{top_c}

Genera un informe con estas secciones exactas:

1. PERFIL DEL CREADOR
   Quién es, qué tipo de contenido hace, cuál es su nicho.

2. ANÁLISIS DE AUDIENCIA
   Cómo se comporta su comunidad, qué tipo de personas comentan, qué temas generan reacción.

3. ANÁLISIS DE ENGAGEMENT
   Qué significa su tasa de engagement, si es buena o mala para su tamaño de audiencia, contexto de los posts de terceras cuentas.

4. SENTIMIENTO DE COMENTARIOS
   Analiza el tono general de los comentarios (positivo, negativo, neutro, emocional).

5. FORTALEZAS Y OPORTUNIDADES
   Qué está haciendo bien y dónde puede mejorar.

6. CONCLUSIÓN GENERAL
   Un párrafo final resumiendo el perfil como si fuera para una marca que quiere hacer una colaboración.

Sé específico, profesional y usa los datos reales."""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

    for intento in range(3):
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                analisis = data["candidates"][0]["content"]["parts"][0]["text"]
                print("  ✅ Análisis generado correctamente")
                return analisis


        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"  ⚠️ Intento {intento+1}/3 — HTTP {e.code}: {body[:150]}")
            if e.code in (401, 403):
                print("  ❌ Key inválida o sin permisos. Revisa tu .env")
                break
            if intento < 2:
                print(f"  ⏳ Reintentando en 4 segundos...")
                time.sleep(4)

        except Exception as e:
            print(f"  ⚠️ Intento {intento+1}/3 — Error inesperado: {e}")
            if intento < 2:
                print(f"  ⏳ Reintentando en 4 segundos...")
                time.sleep(4)

    return "No se pudo generar el análisis automático."

# ════════════════════════════════════════════════════
#  FUNCIÓN: Datos del perfil 
# ════════════════════════════════════════════════════
def extraer_perfil(page):
    datos = {
        "usuario":    USUARIO_OBJETIVO,
        "nombre":     "N/A",
        "biografia":  "N/A",
        "posts":      "N/A",
        "seguidores": "N/A",
        "seguidos":   "N/A",
    }

    resultado = page.evaluate("""() => {
        const header = document.querySelector('header');
        if (!header) return {};
        const spans = Array.from(header.querySelectorAll('span'));
        const textos = spans.map(s => s.innerText.trim()).filter(t => t.length > 0);
        const nombre = header.querySelector('h2')?.innerText.trim()
                    || header.querySelector('h1')?.innerText.trim()
                    || 'N/A';
        let posts = 'N/A', seguidores = 'N/A', seguidos = 'N/A', bio = 'N/A';
        for (const t of textos) {
            const tl = t.toLowerCase();
            if (/^\\d/.test(t) && tl.includes('publicac'))  posts      = t;
            if (/^\\d/.test(t) && tl.includes('seguidor'))  seguidores = t;
            if (/^\\d/.test(t) && tl.includes('seguido') && !tl.includes('seguidor')) seguidos = t;
        }
        const ignorar = [nombre.toLowerCase(), 'seguir', 'enviar mensaje'];
        for (const t of textos) {
            const tl = t.toLowerCase();
            if (t.length < 3) continue;
            if (/^\\d/.test(t)) continue;
            if (ignorar.includes(tl)) continue;
            if (/^[a-z0-9._]{1,30}$/.test(tl)) continue;
            bio = t;
            break;
        }
        return { nombre, posts, seguidores, seguidos, bio };
    }""")

    datos["nombre"]     = resultado.get("nombre",     "N/A")
    datos["biografia"]  = resultado.get("bio",        "N/A")
    datos["posts"]      = resultado.get("posts",      "N/A")
    datos["seguidores"] = resultado.get("seguidores", "N/A")
    datos["seguidos"]   = resultado.get("seguidos",   "N/A")

    print(f"  👤 {datos['nombre']}")
    print(f"  📝 Bio: {datos['biografia'][:80]}")
    print(f"  📊 Posts: {datos['posts']} | Seguidores: {datos['seguidores']} | Seguidos: {datos['seguidos']}")
    return datos


# ════════════════════════════════════════════════════
#  FUNCIÓN: Comentarios
# ════════════════════════════════════════════════════
def extraer_limpio(page):
    comentarios = []
    page.mouse.click(1000, 500)
    page.wait_for_timeout(2000)
    elementos = page.query_selector_all(".x4h1yfo [dir='auto']")
    blacklist_exacta  = {"ver traducción", "responder", "editado", "me gusta"}
    patron_fecha      = re.compile(r'^\d+\s?(d|sem|h|min|s|días|semanas)\.?$', re.IGNORECASE)
    patron_likes      = re.compile(r'^\d[\d\.,]*\s*(me gusta|likes?)$', re.IGNORECASE)
    patron_respuestas = re.compile(r'ver\s*(las|los)?\s*\d*\s*respuestas?', re.IGNORECASE)
    patron_username   = re.compile(r'^[a-z0-9._]{1,30}$', re.IGNORECASE)
    ignorar_autores   = {USUARIO_OBJETIVO.lower()}
    ignorar_en_texto  = list(ignorar_autores)

    for el in elementos:
        try:
            texto = el.inner_text().strip()
        except Exception as e:
            print(f"      ⚠️ Error leyendo texto: {e}")
            continue
        tl = texto.lower()
        if len(texto) < 3:                                continue
        if tl in blacklist_exacta:                        continue
        if patron_fecha.match(tl):                        continue
        if patron_likes.match(tl):                        continue
        if patron_respuestas.search(tl):                  continue
        if patron_username.match(texto):                  continue
        if "verificados" in tl:                           continue
        if any(x in tl for x in ignorar_en_texto):        continue
        if "\n" in texto:                                 continue
        if "#" in texto and len(texto) > 80:              continue

        autor = "Usuario"
        try:
            autor_el = page.evaluate(
                """(el) => {
                    let node = el;
                    for (let i = 0; i < 5; i++) {
                        if (!node.parentElement) break;
                        node = node.parentElement;
                        const links = node.querySelectorAll('a[href^="/"][href$="/"]');
                        for (const link of links) {
                            const href = link.getAttribute('href');
                            if (!href.includes('/p/') && !href.includes('/explore/') && href.split('/').length === 3) {
                                return link.innerText.trim();
                            }
                        }
                    }
                    return null;
                }""", el)
            if autor_el:
                autor = autor_el
        except Exception as e:
            print(f"      ⚠️ Error obteniendo autor: {e}")

        if texto.lower() == autor.lower():                continue
        if autor.lower() in ignorar_autores:              continue
        if any(c['texto'] == texto for c in comentarios): continue

        comentarios.append({"usuario": autor, "texto": texto})
        print(f"      ✅ @{autor}: {texto[:60]}")
        if len(comentarios) >= 3:
            break

    return comentarios


# ════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════
with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        print("✅ Conectado...\n")
    except Exception as e:
        print(f"❌ Chrome no detectado. Detalle: {e}")
        exit()

    print(f"📸 Extrayendo perfil de @{USUARIO_OBJETIVO}...")
    page.goto(f"https://www.instagram.com/{USUARIO_OBJETIVO}/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    perfil = extraer_perfil(page)

            # ✅ hace scroll para cargar más posts antes de recoger links
    print("  📜 Cargando posts...")
    for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)

            links = list(dict.fromkeys([
                f"https://www.instagram.com{el.get_attribute('href')}"
                for el in page.query_selector_all("a[href*='/p/']")
            ]))[:NUM_POSTS]
            
    if not links:
        print("⚠️ No se encontraron posts.")
        exit()

    posts_data = []
    for i, url in enumerate(links, 1):
        print(f"\n🚀 Post {i}/{NUM_POSTS}: {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        likes_n = "N/A"
        try:
            likes_el = page.query_selector("a[href*='/liked_by/'] span, span[class*='likes']")
            if likes_el:
                likes_n = likes_el.inner_text().strip()
            else:
                texto_seccion = page.locator("section").first.inner_text()
                match = re.search(r'([\d\.,]+)\s*(me gusta|likes?)', texto_seccion, re.IGNORECASE)
                if match:
                    likes_n = match.group(1)
        except Exception as e:
            print(f"  ⚠️ Error obteniendo likes: {e}")

        coms = extraer_limpio(page)
        posts_data.append({"num": i, "url": url, "likes": likes_n, "comentarios": coms})

    # ── Calcular engagement ──
    engagement = calcular_engagement(posts_data, perfil["seguidores"])

    # ── Análisis IA ──
    analisis_ia = analizar_con_ia(perfil, posts_data, engagement)

    # Precalcular posts_display con eng_str y etiqueta para TXT y CSV
    posts_display = []
    for post in posts_data:
        s = next(x for x in engagement["stats_posts"] if x["num"] == post["num"])
        etiqueta = "PROPIO" if s["es_propio"] else "ETIQUETADO (excluido del eng.)"
        eng_str  = f"{s['engagement']}%" if s["engagement"] is not None else "N/A (post externo)"
        posts_display.append({**post, "stat": s, "etiqueta": etiqueta, "eng_str": eng_str})
        
    # ── Guardar TXT ──
    with open("ENTREGA_FINAL_UCE_PERFECTA.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write(f"  PERFIL: @{perfil['usuario']}\n")
        f.write("=" * 60 + "\n")
        f.write(f"  Nombre:     {perfil['nombre']}\n")
        f.write(f"  Biografía:  {perfil['biografia']}\n")
        f.write(f"  Posts:      {perfil['posts']}\n")
        f.write(f"  Seguidores: {perfil['seguidores']}\n")
        f.write(f"  Seguidos:   {perfil['seguidos']}\n")
        f.write("=" * 60 + "\n\n")

        for pd in posts_display:
            f.write(f"  POST {pd['num']}: {pd['url']}\n")
            f.write(f"  LIKES: {pd['likes']}  |  ENGAGEMENT: {pd['eng_str']}  |  {pd['etiqueta']}\n")
            if pd["comentarios"]:
                for j, c in enumerate(pd["comentarios"], 1):
                    f.write(f"    Comentario {j}: @{c['usuario']} -> {c['texto']}\n")
            else:
                f.write("    (Sin comentarios extraídos)\n")
            f.write("-" * 60 + "\n\n")

        f.write("=" * 60 + "\n")
        f.write("  MÉTRICAS GENERALES\n")
        f.write("=" * 60 + "\n")
        f.write(f"  Likes promedio:       {engagement['likes_prom']}\n")
        f.write(f"  Engagement promedio:  {engagement['engagement_prom']}%\n")
        f.write(f"  Benchmark:            {engagement['benchmark']}\n")
        if engagement["post_top"]:
            f.write(f"  Post más viral:       Post {engagement['post_top']['num']} ({engagement['post_top']['likes']} likes)\n")
        f.write(f"  Top comentaristas:\n")
        for u, n in engagement["top_comentaristas"]:
            f.write(f"    @{u} — {n} comentario(s)\n")
        f.write("\n")

        f.write("=" * 60 + "\n")
        f.write("  ANÁLISIS IA DEL PERFIL\n")
        f.write("=" * 60 + "\n")
        f.write(analisis_ia + "\n")

    # ── Guardar CSV ──
    with open("ENTREGA_FINAL_UCE_PERFECTA.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["=== DATOS DEL PERFIL ==="])
        writer.writerow(["Usuario", "Nombre", "Biografía", "Posts", "Seguidores", "Seguidos"])
        writer.writerow([perfil["usuario"], perfil["nombre"], perfil["biografia"],
                         perfil["posts"], perfil["seguidores"], perfil["seguidos"]])
        writer.writerow([])

        writer.writerow(["=== POSTS Y COMENTARIOS ==="])
        writer.writerow(["#", "URL", "Likes", "Engagement %", "Tipo", "Comentario #", "Usuario", "Texto"])
        for pd in posts_display:
            if pd["comentarios"]:
                for j, c in enumerate(pd["comentarios"], 1):
                    writer.writerow([pd["num"], pd["url"], pd["likes"], pd["eng_str"], pd["etiqueta"], j, c["usuario"], c["texto"]])
            else:
                writer.writerow([pd["num"], pd["url"], pd["likes"], pd["eng_str"], pd["etiqueta"], "-", "-", "(Sin comentarios)"])
        writer.writerow([]) 

        writer.writerow(["=== MÉTRICAS GENERALES ==="])
        writer.writerow(["Likes promedio", "Engagement promedio %", "Benchmark", "Post más viral"])
        pt = engagement["post_top"]
        writer.writerow([engagement["likes_prom"], engagement["engagement_prom"],
                         engagement["benchmark"], f"Post {pt['num']} ({pt['likes']} likes)" if pt else "N/A"])
        writer.writerow([])

        writer.writerow(["=== TOP COMENTARISTAS ==="])
        writer.writerow(["Usuario", "Comentarios"])
        for u, n in engagement["top_comentaristas"]:
            writer.writerow([f"@{u}", n])
        writer.writerow([])

        writer.writerow(["=== ANÁLISIS IA ==="])
        writer.writerow([analisis_ia])

    print("\n🎉 ¡Listo!")
    print("   📄 ENTREGA_FINAL_UCE_PERFECTA.txt")
    print("   📊 ENTREGA_FINAL_UCE_PERFECTA.csv")