import streamlit as st
import requests
import streamlit.components.v1 as components

# Config page
st.set_page_config(layout="wide")

# Constantes
API_UTXO = "https://mempool.space/api/address/{address}/utxo"
API_BLOCK_HEIGHT = "https://mempool.space/api/blocks"
API_CONGESTION = "https://mempool.space/api/v1/fees/mempool-blocks"
API_BTC_EUR = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur"
DUST_THRESHOLD = 546  # satoshis
SATOSHIS_PER_BTC = 10 ** 8
BLOCKS_PER_DAY = 144  # ~6 blocs/heure * 24h

# Initialisation session wallets
if "wallets" not in st.session_state:
    st.session_state.wallets = {
        "Default": "bc1qrttfx5gcfmdxlzxplz2xax9j958m3xz78l9cv4"
    }

def fetch_utxos(address):
    try:
        r = requests.get(API_UTXO.format(address=address))
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API UTXO : {e}")
        return []

def fetch_latest_block_height():
    try:
        r = requests.get(API_BLOCK_HEIGHT)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list):
            return data[0]["height"]
    except Exception as e:
        st.error(f"Erreur API block height : {e}")
    return None

def fetch_congestion_data():
    try:
        r = requests.get(API_CONGESTION)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API congestion : {e}")
        return []

def fetch_btc_to_eur():
    try:
        r = requests.get(API_BTC_EUR)
        r.raise_for_status()
        return r.json()["bitcoin"]["eur"]
    except Exception as e:
        st.error(f"Erreur API BTC→EUR : {e}")
        return None

def is_valid_btc_address(address):
    if address.startswith(("bc1", "1", "3")) and 25 <= len(address) <= 42:
        return True
    return False

def render_progress_table(balance_btc, btc_to_eur):
    targets = {
        "1/4 BTC (0.25)": 0.25,
        "1/3 BTC (~0.33)": 1/3,
        "1/2 BTC (0.5)": 0.5,
        "1 BTC": 1.0,
    }

    rows_html = ""
    for label, target in targets.items():
        progress = min(balance_btc / target, 1.0)
        percent = progress * 100
        missing_btc = max(target - balance_btc, 0)
        missing_eur = missing_btc * btc_to_eur if btc_to_eur else None
        missing_str = f"{missing_btc:.8f} BTC / €{missing_eur:.2f}" if missing_eur else f"{missing_btc:.8f} BTC / €?"

        color = "#ff4b4b" if progress >= 1.0 else "#0a84ff"

        # Icône médaille si seuil franchi, sinon progression en %
        if progress >= 1.0:
            icon_html = "🏅"
        else:
            icon_html = f"{percent:.0f}%"

        rows_html += f"""
        <tr>
            <td>{icon_html} {label}</td>
            <td>{balance_btc:.8f} / {target:.8f} BTC</td>
            <td>{percent:.2f}%</td>
            <td>{missing_str}</td>
        </tr>
        """

    table_html = f"""
    <style>
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
        }}
        thead tr {{
            background-color: #2563eb;
            color: white;
        }}
        tbody tr:nth-child(even) {{
            background-color: #f1f5f9;
        }}
        tbody tr:hover {{
            background-color: #dbeafe;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #cbd5e1;
        }}
    </style>
    <table>
        <thead>
            <tr>
                <th>Palier</th>
                <th>Solde actuel / Seuil</th>
                <th>Progression</th>
                <th>Manquant</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    components.html(table_html, height=250, scrolling=False)

def main():
    st.title("Visualisation UTXO Wallet Bitcoin")
    st.markdown("""<style>section.main > div.block-container { padding-top: 1rem; }</style>""", unsafe_allow_html=True)

    # Sidebar wallets
    st.sidebar.header("Wallets")
    with st.sidebar.form("add_wallet_form"):
        new_name = st.text_input("Nom du wallet")
        new_address = st.text_input("Adresse Bitcoin")
        submitted = st.form_submit_button("Ajouter")
        if submitted:
            if new_name and new_address:
                if is_valid_btc_address(new_address):
                    st.session_state.wallets[new_name] = new_address
                    st.success(f"Wallet '{new_name}' ajouté.")
                else:
                    st.warning("Adresse Bitcoin invalide.")
            else:
                st.warning("Veuillez remplir nom et adresse.")

    wallet_names = list(st.session_state.wallets.keys())
    selected_wallet = st.sidebar.selectbox("Sélectionnez un wallet", wallet_names)
    wallet_address = st.session_state.wallets[selected_wallet]

    # Bouton suppression
    if st.sidebar.button("Supprimer ce wallet"):
        if selected_wallet in st.session_state.wallets:
            del st.session_state.wallets[selected_wallet]
            st.sidebar.success(f"Wallet '{selected_wallet}' supprimé.")
            st.experimental_rerun()

    st.markdown(f"### 🎯 Wallet sélectionné : **{selected_wallet}**")
    st.markdown(f"`{wallet_address}`")

    # Récupération données
    utxos = fetch_utxos(wallet_address)
    latest_block = fetch_latest_block_height()
    btc_to_eur = fetch_btc_to_eur()

    if not utxos:
        st.info("Pas d'UTXO trouvés pour ce wallet.")
        return

    balance_btc = sum(utxo.get("value", 0) for utxo in utxos) / SATOSHIS_PER_BTC

    # Onglets résumé et liste UTXO
    tab1, tab2 = st.tabs(["Home", "Liste UTXO"])

    with tab1:
        render_progress_table(balance_btc, btc_to_eur)

        congestion_data = fetch_congestion_data()
        if congestion_data:
            st.markdown("### État de congestion réseau (sats/vByte)")
            for b in congestion_data[:3]:
                st.write(f"Bloc {b.get('height', '?')} → {b.get('fee', 0):.1f}")
        else:
            st.warning("Impossible de récupérer la congestion réseau.")

        if btc_to_eur:
            st.markdown(f"Taux BTC → EUR : €{btc_to_eur:.2f}")
            st.markdown(f"Balance estimée : €{balance_btc * btc_to_eur:,.2f}")
        else:
            st.warning("Impossible de récupérer le taux BTC → EUR.")

    with tab2:
        utxos_sorted = sorted(
            utxos,
            key=lambda u: u.get("status", {}).get("block_height", 0),
            reverse=True
        )
        utxo_rows = []
        for utxo in utxos_sorted:
            value_sats = utxo.get("value", 0)
            value_btc = value_sats / SATOSHIS_PER_BTC
            block_height = utxo.get("status", {}).get("block_height", None)
            dust = value_sats < DUST_THRESHOLD

            if block_height and latest_block:
                blocks_old = latest_block - block_height
                age_days = blocks_old / BLOCKS_PER_DAY
                age_str = f"{age_days:.1f} jours"
            else:
                age_str = "Non confirmé"

            utxo_rows.append({
                "Txid": utxo.get("txid"),
                "Vout": utxo.get("vout"),
                "Valeur (BTC)": f"{value_btc:.8f}",
                "Âge": age_str,
                "Dust": "Oui" if dust else "Non",
                "Frais (BTC)": f"0.00000000"
            })

        st.dataframe(utxo_rows, use_container_width=True)

if __name__ == "__main__":
    main()
