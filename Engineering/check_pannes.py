import database

ps = database.fetch_all(
    "SELECT wo, date_panne, heure_panne, machine, statut "
    "FROM pannes ORDER BY id DESC LIMIT 10"
)

if not ps:
    print("Aucune panne en base.")
else:
    print(f"{len(ps)} panne(s) :")
    for p in ps:
        print(f"  {p['wo']} • {p['date_panne']} {p['heure_panne'] or '—'} "
              f"• {p['machine']} • {p['statut']}")