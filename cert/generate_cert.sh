#!/bin/bash

# Configuration générale du certificat
COUNTRY_NAME="FR"
STATE_OR_PROVINCE_NAME="Auvergne-Rhone-Alpes"
LOCALITY_NAME="Pont Eveque"
ORGANIZATION_NAME="ASCOLAB"
ORGANIZATIONAL_UNIT_NAME="Eiffage"
#COMMON_NAME="localhost"
EMAIL_ADDRESS="contact@ascolab.fr"
VALIDITY_DAYS=3650  # 10 ans

# Noms des fichiers
CERT_KEY="localhost.key"
CERT_PEM="localhost.crt"
OPENSSL_CONFIG="openssl.cnf"

# --- Récupération des informations dynamiques ---

# Récupérer le nom d'hôte du serveur
#SERVER_HOSTNAME=$(hostname)
SERVER_HOSTNAME=$(hostname | tr '[:upper:]' '[:lower:]')

COMMON_NAME="${SERVER_HOSTNAME}"

# Récupérer les adresses IP des interfaces réseau
# On utilise 'ip a' et on filtre pour exclure les adresses de loopback et les adresses IPv6
# On récupère les 10 premières adresses IP fixes trouvées
IP_ADDRESSES=($(ip -4 a | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1 | grep -v '127.0.0.1' | head -n 10))

# Vérifier si au moins une adresse IP a été trouvée
if [ ${#IP_ADDRESSES[@]} -eq 0 ]; then
  echo "Aucune adresse IP valide n'a été trouvée. Le script ne peut pas continuer."
  exit 1
fi

# Préparer la liste des noms alternatifs du sujet (Subject Alternative Names)
SAN_LIST="DNS.1:localhost,DNS.2:${SERVER_HOSTNAME}"

# Ajouter les adresses IP à la liste SAN
for i in "${!IP_ADDRESSES[@]}"; do
  # Les adresses IP doivent être numérotées séquentiellement
  SAN_LIST+=",IP.$((i+1)):${IP_ADDRESSES[$i]}"
done

echo "Génération du certificat pour les noms d'hôte et adresses IP suivants : "
echo "  - Nom d'hôte : localhost"
echo "  - Nom d'hôte du serveur : ${SERVER_HOSTNAME}"
for i in "${!IP_ADDRESSES[@]}"; do
  echo "  - Adresse IP $(($i+1)) : ${IP_ADDRESSES[$i]}"
done

# --- Génération du fichier de configuration OpenSSL ---

cat > "${OPENSSL_CONFIG}" <<EOF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = ${COUNTRY_NAME}
ST = ${STATE_OR_PROVINCE_NAME}
L = ${LOCALITY_NAME}
O = ${ORGANIZATION_NAME}
OU = ${ORGANIZATIONAL_UNIT_NAME}
CN = ${COMMON_NAME}
emailAddress = ${EMAIL_ADDRESS}

[ req_ext ]
basicConstraints = CA:TRUE
subjectAltName = ${SAN_LIST}
EOF

ls -la "${OPENSSL_CONFIG}"

# --- Génération de la clé et du certificat ---

# On utilise 'req -x509' pour générer une demande de certificat auto-signée
#openssl req -x509 \
#-newkey rsa:2048 \
#-keyout "${CERT_KEY}" \
#-out "${CERT_PEM}" \
#-days "${VALIDITY_DAYS}" \
#-nodes \
#-config "${OPENSSL_CONFIG}"

# On supprime le fichier de configuration temporaire
# rm "${OPENSSL_CONFIG}"


openssl req -x509 \
-newkey rsa:2048 \
-keyout "${CERT_KEY}" \
-out "${CERT_PEM}" \
-days "${VALIDITY_DAYS}" \
-nodes \
-subj "/C=${COUNTRY_NAME}/ST=${STATE_OR_PROVINCE_NAME}/L=${LOCALITY_NAME}/O=${ORGANIZATION_NAME}/OU=${ORGANIZATIONAL_UNIT_NAME}/CN=${COMMON_NAME}" \
-addext "basicConstraints = 'CA:TRUE'" \
-addext "subjectAltName = ${SAN_LIST}"



echo "Opération terminée !"
echo "Clé privée : ${CERT_KEY}"
echo "Certificat : ${CERT_PEM}"
echo "Ces fichiers sont maintenant prêts à être utilisés avec votre serveur web local."

