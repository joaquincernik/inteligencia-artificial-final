#!/bin/bash
# Genera eventos benignos para Wazuh. Requiere root. Revierte lo que crea.

if [ "$EUID" -ne 0 ]; then
  echo "Ejecutar como root: sudo $0"
  exit 1
fi

FAKEUSER="usuario_fantasma_wazuh"
pausa() { sleep 3; }

echo "Generando eventos de seguridad para Wazuh..."

# Discovery
uname -a > /dev/null; cat /etc/os-release > /dev/null; pausa
whoami > /dev/null; id > /dev/null; pausa
ps aux > /dev/null; pausa
find /etc -maxdepth 2 -name "*.conf" > /dev/null 2>&1; pausa
cat /etc/passwd > /dev/null; getent passwd > /dev/null; pausa
ss -tuln > /dev/null; pausa
ip addr > /dev/null; ip route > /dev/null; pausa
ip neigh > /dev/null; pausa
systemctl list-units --type=service > /dev/null 2>&1; pausa
(dpkg -l || rpm -qa) > /dev/null 2>&1; pausa
nc -vz localhost 1-1000 > /dev/null 2>&1; pausa

# Credential access
cat /etc/shadow > /dev/null 2>&1; pausa
grep -rIl "password" /etc 2>/dev/null | head -n 5 > /dev/null; pausa
find / -xdev \( -name "id_rsa" -o -name "id_ed25519" \) 2>/dev/null > /dev/null; pausa
for i in $(seq 1 10); do
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
      -o PreferredAuthentications=password usuario_inexistente@127.0.0.1 true > /dev/null 2>&1
done; pausa

# Cuentas
useradd "$FAKEUSER" 2>/dev/null; pausa
usermod -aG sudo "$FAKEUSER" 2>/dev/null || usermod -aG wheel "$FAKEUSER" 2>/dev/null; pausa
userdel -r "$FAKEUSER" 2>/dev/null; pausa

# Persistencia
echo "* * * * * root /bin/true" > /etc/cron.d/wazuh_test; sleep 5
rm -f /etc/cron.d/wazuh_test; pausa

cat > /etc/systemd/system/wazuh_test.service <<'EOF'
[Unit]
Description=Wazuh test service
[Service]
ExecStart=/bin/true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload 2>/dev/null; sleep 5
rm -f /etc/systemd/system/wazuh_test.service
systemctl daemon-reload 2>/dev/null; pausa

cp ~/.bashrc /tmp/.bashrc.bak 2>/dev/null
echo "# wazuh_test" >> ~/.bashrc; sleep 3
mv /tmp/.bashrc.bak ~/.bashrc 2>/dev/null; pausa

# Escalada / permisos
sudo -n -l > /dev/null 2>&1; sudo -n true > /dev/null 2>&1; pausa
touch /tmp/wazuh_test_file.txt
chmod 777 /tmp/wazuh_test_file.txt; pausa

# FIM
echo "test" > /etc/wazuh_test_fim.conf; sleep 5
echo "test2" >> /etc/wazuh_test_fim.conf; sleep 5
rm -f /etc/wazuh_test_fim.conf; pausa

# Ejecución / evasión
echo "d2hvYW1p" | base64 -d | bash > /dev/null; pausa
python3 -c "import base64;exec(base64.b64decode('cHJpbnQoMSk='))" > /dev/null 2>&1; pausa
echo "d2hvYW1p" > /tmp/wazuh_payload.b64
base64 -d /tmp/wazuh_payload.b64 > /dev/null; pausa
cp ~/.bash_history /tmp/.bash_history.bak 2>/dev/null
: > ~/.bash_history; history -c
mv /tmp/.bash_history.bak ~/.bash_history 2>/dev/null; pausa
rm -f /tmp/wazuh_payload.b64 /tmp/wazuh_test_file.txt; pausa

# Collection / C2
tar czf /tmp/wazuh_archive.tgz /etc/hostname > /dev/null 2>&1
rm -f /tmp/wazuh_archive.tgz; pausa
curl -s -o /tmp/wazuh_dl.html https://example.com > /dev/null 2>&1 || \
  wget -q -O /tmp/wazuh_dl.html https://example.com > /dev/null 2>&1
rm -f /tmp/wazuh_dl.html

echo "Eventos generados. Revisa el dashboard de Wazuh."
