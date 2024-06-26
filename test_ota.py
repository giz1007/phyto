from ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD

#firmware_url = "https://raw.githubusercontent.com/pierreyvesbaloche/kevinmca_ota/main/"
firmware_url = "https://raw.githubusercontent.com/giz1007/phyto_box/main/"

ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "test_ota.py")

ota_updater.download_and_install_update_if_available()