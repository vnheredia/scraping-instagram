import instaloader
import json
import os
from datetime import datetime

USERNAME = "nayeli.nxx"   
MAX_POSTS = 5               

L = instaloader.Instaloader()

# ─────────────────────────────────────────
# OBTENER DATOS DEL PERFIL
# ─────────────────────────────────────────
print(f"\n🔍 Scrapeando perfil: @{USERNAME}\n")

perfil = instaloader.Profile.from_username(L.context, USERNAME)

datos_perfil = {
    "usuario":      perfil.username,
    "nombre":       perfil.full_name,
    "biografia":    perfil.biography,
    "seguidores":   perfil.followers,
    "siguiendo":    perfil.followees,
    "total_posts":  perfil.mediacount,
    "es_privado":   perfil.is_private,
    "es_verificado":perfil.is_verified,
    "url_externo":  perfil.external_url,
    "fecha_scraping": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

print("📋 INFORMACIÓN DEL PERFIL")
print("─" * 40)
for clave, valor in datos_perfil.items():
    print(f"  {clave:<20}: {valor}")

# ─────────────────────────────────────────
# OBTENER POSTS RECIENTES
# ─────────────────────────────────────────
print(f"\n📸 ÚLTIMOS {MAX_POSTS} POSTS")
print("─" * 40)

lista_posts = []

for i, post in enumerate(perfil.get_posts()):
    if i >= MAX_POSTS:
        break

    datos_post = {
        "numero":       i + 1,
        "fecha":        str(post.date),
        "likes":        post.likes,
        "comentarios":  post.comments,
        "tipo":         post.typename,
        "url":          f"https://www.instagram.com/p/{post.shortcode}/",
        "caption":      post.caption[:100] if post.caption else "Sin texto"
    }

    lista_posts.append(datos_post)

    print(f"\n  Post #{i+1}")
    print(f"  📅 Fecha     : {datos_post['fecha']}")
    print(f"  ❤️ Likes     : {datos_post['likes']}")
    print(f"  💬 Comentarios: {datos_post['comentarios']}")
    print(f"  🔗 URL       : {datos_post['url']}")
    print(f"  📝 Caption   : {datos_post['caption']}")

# ─────────────────────────────────────────
# GUARDAR RESULTADOS EN JSON
# ─────────────────────────────────────────
resultado_final = {
    "perfil": datos_perfil,
    "posts":  lista_posts
}

os.makedirs("resultados", exist_ok=True)
scrapeo = f"resultados/{USERNAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

with open(scrapeo, "w", encoding="utf-8") as f:
    json.dump(resultado_final, f, ensure_ascii=False, indent=4)

print(f"\n✅ Resultados guardados en: {scrapeo}\n")