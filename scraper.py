import csv
import re
from playwright.sync_api import sync_playwright

USUARIO_OBJETIVO = "macabeso"

def extraer_limpio(page):
    comentarios = []

    page.mouse.click(1000, 500)
    page.wait_for_timeout(2000)

    elementos = page.query_selector_all(".x4h1yfo [dir='auto']")

    blacklist_exacta = {"ver traducción", "responder", "editado", "me gusta"}
    patron_fecha     = re.compile(r'^\d+\s?(d|sem|h|min|s|días|semanas)\.?$', re.IGNORECASE)
    # ✅ NUEVO: "197 Me gusta", "6 Me gusta", etc.
    patron_likes     = re.compile(r'^\d[\d\.,]*\s*(me gusta|likes?)$', re.IGNORECASE)
    # ✅ NUEVO: "Ver las 4 respuestas", "Ver respuestas", etc.
    patron_respuestas = re.compile(r'ver\s*(las|los)?\s*\d*\s*respuestas?', re.IGNORECASE)
    # ✅ NUEVO: texto que es puro nombre de usuario de IG (letras, números, puntos, guiones bajos)
    patron_username  = re.compile(r'^[a-z0-9._]{1,30}$', re.IGNORECASE)

    ignorar_autores   = {USUARIO_OBJETIVO.lower(), "mileendkicksmovie", "independentfilmco", "foryoursoulworldwide"}
    ignorar_en_texto  = list(ignorar_autores)

    for el in elementos:
        try:
            texto = el.inner_text().strip()
        except Exception as e:
            print(f"      ⚠️ Error leyendo texto: {e}")
            continue

        tl = texto.lower()

        # --- FILTROS ---
        if len(texto) < 3:
            continue
        if tl in blacklist_exacta:
            continue
        if patron_fecha.match(tl):
            continue
        if patron_likes.match(tl):                  # ✅ "197 Me gusta"
            continue
        if patron_respuestas.search(tl):             # ✅ "Ver las 4 respuestas"
            continue
        if patron_username.match(texto):             # ✅ nombre de usuario suelto
            continue
        if "verificados" in tl:
            continue
        if any(x in tl for x in ignorar_en_texto):
            continue

        # --- AUTOR ---
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

        # ✅ NUEVO: si el texto ES el autor (username filtrado como comentario)
        if texto.lower() == autor.lower():
            continue
        if autor.lower() in ignorar_autores:
            continue
        if any(c['texto'] == texto for c in comentarios):
            continue

        comentarios.append({"usuario": autor, "texto": texto})
        print(f"      ✅ @{autor}: {texto[:60]}")

        if len(comentarios) >= 5:
            break

    return comentarios


with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        print("✅ Conectado para la limpieza final...")
    except Exception as e:
        print(f"❌ Error: Chrome no detectado. Detalle: {e}")
        exit()

    page.goto(f"https://www.instagram.com/{USUARIO_OBJETIVO}/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    links = [
        f"https://www.instagram.com{el.get_attribute('href')}"
        for el in page.query_selector_all("a[href*='/p/']")[:5]
    ]

    if not links:
        print("⚠️ No se encontraron posts. Verifica que hayas iniciado sesión.")
        exit()

    with open("ENTREGA_FINAL_UCE_PERFECTA.txt", "w", encoding="utf-8") as f:
        for url in links:
            print(f"\n🚀 Procesando Post: {url}")
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

            f.write(f"POST: {url}\nLIKES: {likes_n}\n")
            if coms:
                for i, c in enumerate(coms, 1):
                    f.write(f"  Comentario {i}: @{c['usuario']} -> {c['texto']}\n")
            else:
                f.write("  (Sin comentarios extraídos)\n")
            f.write("=" * 60 + "\n")

    print("\n🎉 ¡Listo! Revisa 'ENTREGA_FINAL_UCE_PERFECTA.txt'")