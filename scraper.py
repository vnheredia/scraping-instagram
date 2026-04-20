import requests
import csv

usuario = "nayeli.nxx"

url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={usuario}"

headers = {
    "User-Agent": "Mozilla/5.0",
    "x-ig-app-id": "936619743392459"
}

try:
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        data = response.json()
        user = data["data"]["user"]

        print("===== PERFIL =====")
        print("Usuario:", user["username"])
        print("Biografía:", user["biography"])
        print("Seguidores:", user["edge_followed_by"]["count"])
        print("Seguidos:", user["edge_follow"]["count"])
        print("Total posts:", user["edge_owner_to_timeline_media"]["count"])

        print("\n===== POSTS =====\n")

        posts = user["edge_owner_to_timeline_media"]["edges"]

        likes_list = []
        comentarios_list = []

        with open("posts_instagram.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["URL", "Likes", "Comentarios"])

            for post in posts[:10]:
                node = post["node"]

                url_post = "https://www.instagram.com/p/" + node["shortcode"]
                likes = node["edge_liked_by"]["count"]
                comentarios = node["edge_media_to_comment"]["count"]

                print("URL:", url_post)
                print("Likes:", likes)
                print("Comentarios:", comentarios)
                print("-----")

                writer.writerow([url_post, likes, comentarios])

                likes_list.append(likes)
                comentarios_list.append(comentarios)

        if likes_list and comentarios_list:
            prom_likes = sum(likes_list) / len(likes_list)
            prom_comentarios = sum(comentarios_list) / len(comentarios_list)

            max_likes = max(likes_list)
            min_likes = min(likes_list)

            seguidores = user["edge_followed_by"]["count"]
            engagement = ((prom_likes + prom_comentarios) / seguidores) * 100 if seguidores > 0 else 0

            print("\n===== ESTADÍSTICAS =====")
            print("Promedio likes:", round(prom_likes, 2))
            print("Promedio comentarios:", round(prom_comentarios, 2))
            print("Max likes:", max_likes)
            print("Min likes:", min_likes)
            print("Engagement rate (%):", round(engagement, 4))

        print("\n✅ Datos guardados en posts_instagram.csv")

    else:
        print("❌ Error HTTP:", response.status_code)

except requests.exceptions.RequestException as e:
    print("❌ Error de conexión:", e)