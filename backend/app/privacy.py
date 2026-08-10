"""Garde-fous RGPD / anonymisation (MVP mobilité)."""

# Seuil k-anonymité : ne pas exposer de flux avec volume < k
K_ANONYMITY_MIN = 5

# Seuil métier recommandé pour l'UI (au-dessus du plancher légal)
OD_MIN_PASSENGERS_DEFAULT = 20
