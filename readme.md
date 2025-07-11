Local Web Application with Flask, Gunicorn, and Custom DNS
This project demonstrates how to host a Flask web application on a local network PC (Linux or Windows) using Gunicorn (on Linux) or Waitress (on Windows) for production serving and Dnsmasq (on Linux) or Acrylic DNS Proxy (on Windows) for custom local domain resolution. This allows devices on your home network to access your app using a friendly domain name like apps.dhruv instead of an IP address.

Features ✨
Custom Local Domain: Access http://apps.dhruv:5000 from any device on your local network.

Production-Ready Server: Uses Gunicorn (Linux) or Waitress (Windows) for reliable and performant serving.

Virtual Environment: Isolates Python dependencies for clean development.

Systemd Service / NSSM: (Optional, but recommended for persistent hosting) Ensures the Flask app starts automatically on boot and runs in the background.

Prerequisites 📋
A Linux PC (e.g., Chromebook's Linux container, Raspberry Pi, Ubuntu machine) OR a Windows PC.

Your Flask application code (e.g., app.py).

Basic understanding of the command line for your OS.

Access to your home Wi-Fi router settings (for viewing PC's IP and configuring client DNS).

Setup Steps 🚀
Follow the instructions relevant to your operating system.

1. Initial Setup & Dependencies
On Linux (Ubuntu/Debian-based, including Crostini)
Update System & Install Essentials:

Bash

sudo apt update
sudo apt upgrade -y
sudo apt install python3 python3-pip dnsmasq git -y
On Windows
Install Python: Download and install Python 3.x from python.org. During installation, make sure to check "Add Python to PATH".

Install Git: Download and install Git from git-scm.com. This will also provide Git Bash, a useful terminal.

Open a Command Prompt or PowerShell (or Git Bash).

Common Steps (Linux & Windows)
Clone Your Flask App (or copy files):

Bash

# Example for cloning from Git. Adjust path as needed.
# Linux:
git clone your_repo_url /home/dhruv/webapp/appsox
cd /home/dhruv/webapp/appsox
# Windows (e.g., in PowerShell or CMD):
git clone your_repo_url C:\Users\YourUser\webapp\appsox
cd C:\Users\YourUser\webapp\appsox
Make sure you navigate to the directory containing your app.py file.

Create & Activate Virtual Environment:

Bash

# Linux:
python3 -m venv venv
source venv/bin/activate
# Windows (in CMD):
py -m venv venv
.\venv\Scripts\activate.bat
# Windows (in PowerShell):
py -m venv venv
.\venv\Scripts\Activate.ps1
Your terminal prompt should now show (venv) at the beginning.

Install Python Dependencies:

Bash

pip install flask
# Linux:
pip install gunicorn
# Windows:
pip install waitress
# Install any other dependencies your app requires (e.g., from a requirements.txt)
# pip install -r requirements.txt
2. Configure Local DNS Server
This allows apps.dhruv to resolve to your PC's IP address.

Get Your PC's Local IP Address:
This is the IP address of your hosting PC on your local network.

Bash

# Linux:
ip a
# Windows (in CMD or PowerShell):
ipconfig
Look for the IPv4 Address under your active network adapter (e.g., Wi-Fi or Ethernet). Let's assume it's 192.168.1.100 for this example. This IP is crucial.

On Linux (Dnsmasq)
Create dnsmasq Custom Configuration:

Bash

sudo nano /etc/dnsmasq.d/mywebapp.conf
Add this single line, replacing YOUR_PC_IP with the actual IP address of your Linux PC:

address=/apps.dhruv/YOUR_PC_IP
Save and exit (Ctrl + O, Enter, Ctrl + X).

Configure dnsmasq for Upstream DNS (Crucial for Internet Access):

Bash

sudo nano /etc/dnsmasq.conf
Ensure these lines are present and uncommented (remove # if it's there):

no-resolv  # Prevents dnsmasq from using /etc/resolv.conf for its upstream servers
server=8.8.8.8 # Google Public DNS (Primary)
server=8.8.4.4 # Google Public DNS (Secondary for redundancy)
Save and exit.

Configure Systemd-Networkd (for Chromebook Linux/Crostini only):

Bash

sudo nano /etc/systemd/network/10-eth0.network
Ensure the [Network] section includes these DNS lines:

Ini, TOML

[Match]
Name=eth0

[Network]
DHCP=yes
DNS=127.0.0.1  # Points to your local dnsmasq
DNS=8.8.8.8    # Points to a public DNS for internet
Save and exit.

Restart Network Services:

Bash

sudo systemctl restart systemd-networkd.service # On Crostini only
sudo systemctl restart dnsmasq.service
Check dnsmasq status: sudo systemctl status dnsmasq.service. It should be active (running).

On Windows (Acrylic DNS Proxy)
Download Acrylic DNS Proxy:
Go to acrylic.codeplex.com (Acrylic's original site is archived; search for "Acrylic DNS Proxy" to find a reliable download source like Softpedia or similar).

Install Acrylic: Follow the installer's instructions. It typically installs to C:\Program Files (x86)\Acrylic DNS Proxy.

Configure Acrylic Custom Host:

Navigate to the Acrylic installation directory.

Open AcrylicHosts.txt in Notepad as Administrator.

Right-click notepad.exe in Start Menu > More > Run as administrator.

File > Open... and browse to C:\Program Files (x86)\Acrylic DNS Proxy\AcrylicHosts.txt.

Add the following line, replacing YOUR_PC_IP with your actual Windows PC's IP address:

YOUR_PC_IP apps.dhruv
Example: 192.168.1.100 apps.dhruv

Save and close the file.

Configure Acrylic DNS Settings:

Open AcrylicConfiguration.ini in Notepad as Administrator.

Find the [GlobalSection] section.

Ensure PrimaryServerAddress and SecondaryServerAddress are set to public DNS servers (e.g., Google DNS):

Ini, TOML

PrimaryServerAddress=8.8.8.8
SecondaryServerAddress=8.8.4.4
Save and close the file.

Restart Acrylic Service:

Open Services (search for "Services" in the Start Menu).

Find "Acrylic DNS Proxy Service".

Right-click it and select Restart.

Ensure its status is "Running".

Configure Windows Network Adapter to Use Acrylic:

Go to Control Panel > Network and Sharing Center > Change adapter settings.

Right-click your active network adapter (e.g., Wi-Fi, Ethernet) and choose Properties.

Select "Internet Protocol Version 4 (TCP/IPv4)" and click Properties.

Select "Use the following DNS server addresses".

Set Preferred DNS server to 127.0.0.1. This makes your Windows PC use Acrylic as its DNS server.

Set Alternate DNS server to 8.8.8.8 (optional, Acrylic can handle upstream, but for redundancy).

Click OK on both windows.

Disable and Re-enable your network adapter (right-click adapter > Disable, then right-click > Enable) to apply changes.

3. Run Your Flask App
On Linux (Gunicorn)
Navigate to Your App Directory:

Bash

cd /home/dhruv/webapp/appsox
Ensure Virtual Environment is Active:

Bash

source venv/bin/activate
Confirm (venv) is in your prompt.

Start Gunicorn:

Bash

gunicorn --bind 0.0.0.0:5000 app:app
Replace app:app if your Flask application instance is named differently.

On Windows (Waitress)
Navigate to Your App Directory:

DOS

cd C:\Users\YourUser\webapp\appsox
Ensure Virtual Environment is Active:

DOS

.\venv\Scripts\activate.bat  # Or .\venv\Scripts\Activate.ps1 for PowerShell
Confirm (venv) is in your prompt.

Start Waitress:

DOS

waitress-serve --host=0.0.0.0 --port=5000 app:app
Replace app:app if your Flask application instance is named differently.

4. (Optional) Run Flask App as a Service
For reliable, automatic startup and background running.

On Linux (Systemd Service)
Create a Service File:

Bash

sudo nano /etc/systemd/system/mywebapp.service
Paste the following, adjusting paths to your appsox directory and User/Group as needed.

Ini, TOML

[Unit]
Description=Gunicorn instance to serve mywebapp
After=network.target

[Service]
User=dhruv # Your Linux username
Group=www-data # Or your username's group, e.g., dhruv
WorkingDirectory=/home/dhruv/webapp/appsox # Path to your appsox directory
ExecStart=/home/dhruv/webapp/appsox/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
Save and exit.

Enable and Start the Service:

Bash

sudo systemctl daemon-reload
sudo systemctl enable mywebapp.service
sudo systemctl start mywebapp.service
Check Service Status:

Bash

sudo systemctl status mywebapp.service
It should be active (running).

On Windows (NSSM - Non-Sucking Service Manager)
NSSM is a popular tool to run any executable as a Windows service.

Download NSSM:
Download the latest stable release from nssm.cc. Extract it to a permanent location (e.g., C:\nssm).

Install the Service:
Open an elevated Command Prompt (Run as Administrator).

DOS

cd C:\nssm\win64  # Or win32 depending on your system
nssm install MyWebAppService
A GUI window will pop up:

Path: Browse to your venv\Scripts\waitress-serve.exe (e.g., C:\Users\YourUser\webapp\appsox\venv\Scripts\waitress-serve.exe).

Arguments: --host=0.0.0.0 --port=5000 app:app (adjust app:app as needed).

Details Tab: (Optional) Set Display name (e.g., "My Web App Flask Server").

Dependencies Tab: (Optional) Add "Acrylic DNS Proxy Service" if you want it to start after Acrylic.

Click "Install Service".

Start the Service:

DOS

net start MyWebAppService
You can also manage it from the Windows Services console.

5. Configure Client Devices 📱
For other devices on your local network (e.g., your phone, another laptop) to use your custom domain:

Get Your PC's IP Address (again): Confirm the IP address of the Linux/Windows PC hosting your app (e.g., 100.115.92.203 or 192.168.1.100).

On the Client Device:

Go to Wi-Fi settings.

Tap on your connected Wi-Fi network.

Find IP Settings or DNS settings and change it to Static or Manual.

Set DNS 1 to your Linux/Windows PC's IP address (e.g., 192.168.1.100).

Set DNS 2 to a public DNS server like 8.8.8.8 or 1.1.1.1 (as a fallback for regular internet Browse).

Save the settings.

Toggle Wi-Fi off and then on to apply the changes.

Access Your Application 🎉
Now, from the client device you configured, open a web browser and navigate to:

http://apps.dhruv:5000

You should see your Flask application!
