import csv
import re
from playwright.sync_api import sync_playwright

USUARIO_OBJETIVO = "macabeso"

# ════════════════════════════════════════════════════
#  FUNCIÓN 1: Datos del perfil
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

        // Nombre: h2 dentro del header
        const nombre = header.querySelector('h2')?.innerText.trim()
                    || header.querySelector('h1')?.innerText.trim()
                    || 'N/A';

        // Stats: spans que empiezan con número y tienen etiqueta conocida
        let posts = 'N/A', seguidores = 'N/A', seguidos = 'N/A', bio = 'N/A';

        for (const t of textos) {
            const tl = t.toLowerCase();
            if (/^\\d/.test(t) && tl.includes('publicac'))  posts       = t;
            if (/^\\d/.test(t) && tl.includes('seguidor'))  seguidores  = t;
            if (/^\\d/.test(t) && tl.includes('seguido') && !tl.includes('seguidor')) seguidos = t;
        }

        // Bio: span que NO empieza con número, no es el nombre, y tiene contenido real
        const ignorar = [nombre.toLowerCase(), 'seguir', 'enviar mensaje', 'actor'];
        for (const t of textos) {
            const tl = t.toLowerCase();
            if (t.length < 3) continue;
            if (/^\\d/.test(t)) continue;
            if (ignorar.includes(tl)) continue;
            if (/^[a-z0-9._]{1,30}$/.test(tl)) continue; // username
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
#  FUNCIÓN 2: Comentarios por post
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

    ignorar_autores  = {USUARIO_OBJETIVO.lower()}
    ignorar_en_texto = list(ignorar_autores)

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
        # ✅ NUEVO: filtra captions (texto multilinea con saltos o hashtags)
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
                }""",
                el
            )
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

    # ── 1. Perfil ──
    print(f"📸 Extrayendo perfil de @{USUARIO_OBJETIVO}...")
    page.goto(f"https://www.instagram.com/{USUARIO_OBJETIVO}/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    perfil = extraer_perfil(page)

    # ── 2. Links de posts ──
    links = [
        f"https://www.instagram.com{el.get_attribute('href')}"
        for el in page.query_selector_all("a[href*='/p/']")[:5]
    ]

    if not links:
        print("⚠️ No se encontraron posts. Verifica que hayas iniciado sesión.")
        exit()

    # ── 3. Scraping de posts ──
    posts_data = []
    for i, url in enumerate(links, 1):
        print(f"\n🚀 Post {i}/5: {url}")
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

    # ── 4. Guardar TXT ──
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

        for post in posts_data:
            f.write(f"  POST {post['num']}: {post['url']}\n")
            f.write(f"  LIKES: {post['likes']}\n")
            if post['comentarios']:
                for j, c in enumerate(post['comentarios'], 1):
                    f.write(f"    Comentario {j}: @{c['usuario']} -> {c['texto']}\n")
            else:
                f.write("    (Sin comentarios extraídos)\n")
            f.write("-" * 60 + "\n\n")

    # ── 5. Guardar CSV ──
    with open("ENTREGA_FINAL_UCE_PERFECTA.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        # Hoja de perfil
        writer.writerow(["=== DATOS DEL PERFIL ==="])
        writer.writerow(["Usuario", "Nombre", "Biografía", "Posts", "Seguidores", "Seguidos"])
        writer.writerow([
            perfil["usuario"], perfil["nombre"], perfil["biografia"],
            perfil["posts"],   perfil["seguidores"], perfil["seguidos"]
        ])

        writer.writerow([])  # línea en blanco separadora

        # Hoja de posts y comentarios
        writer.writerow(["=== POSTS Y COMENTARIOS ==="])
        writer.writerow(["#", "URL del Post", "Likes", "Comentario #", "Usuario", "Texto"])
        for post in posts_data:
            if post["comentarios"]:
                for j, c in enumerate(post["comentarios"], 1):
                    writer.writerow([post["num"], post["url"], post["likes"], j, c["usuario"], c["texto"]])
            else:
                writer.writerow([post["num"], post["url"], post["likes"], "-", "-", "(Sin comentarios)"])

    print("\n🎉 ¡Listo!")
    print("   📄 ENTREGA_FINAL_UCE_PERFECTA.txt")
    print("   📊 ENTREGA_FINAL_UCE_PERFECTA.csv")