import streamlit as st

# Configuration de la page (titre de l'onglet et icône)
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# Titre principal de la page
st.title("🛡️ Page d'Accueil Admin")

# Ton message de bienvenue
st.write("Hello admin")