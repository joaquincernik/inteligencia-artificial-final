#!/bin/bash
echo "Generando eventos de seguridad para Wazuh..."

# T1082: Descubrimiento de sistema
uname -a > /dev/null
cat /etc/os-release > /dev/null

# T1087: Descubrimiento de cuentas (requiere root)
cat /etc/shadow > /dev/null 2>&1

# T1049: Descubrimiento de red
ss -tuln > /dev/null

# T1222: Modificación de permisos
touch /tmp/wazuh_test_file.txt
chmod 777 /tmp/wazuh_test_file.txt

# T1136: Creación de cuentas locales temporales
useradd usuario_fantasma_wazuh 2>/dev/null
userdel usuario_fantasma_wazuh 2>/dev/null

# T1059: Ejecución en intérprete de comandos ofuscado (Base64)
echo "d2hvYW1p" | base64 -d | bash > /dev/null

# T1070: Borrado de huellas
history -c

# T1046: Escaneo rápido de red local
nc -vz localhost 1-1000 2>&1 > /dev/null

echo "Eventos generados. Revisa el dashboard de Wazuh."