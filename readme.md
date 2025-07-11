Here's a `README.md` for your Flask application and DNS setup, suitable for sharing or as a personal reference.

-----

# Local Web Application with Flask, Gunicorn, and Dnsmasq

This project demonstrates how to host a Flask web application on a local network PC (e.g., a Chromebook's Linux container, Raspberry Pi, or any Linux machine) using **Gunicorn** for production serving and **Dnsmasq** for custom local domain resolution. This allows devices on your home network to access your app using a friendly domain name like `apps.dhruv` instead of an IP address.

## Features ✨

  * **Custom Local Domain:** Access `http://apps.dhruv:5000` from any device on your local network.
  * **Production-Ready Server:** Uses Gunicorn for reliable and performant serving of the Flask application.
  * **Virtual Environment:** Isolates Python dependencies for clean development.
  * **Systemd Service:** (Optional, but recommended for persistent hosting) Ensures the Flask app starts automatically on boot and runs in the background.

## Prerequisites 📋

  * A Linux PC (e.g., Chromebook's Linux container, Raspberry Pi, Ubuntu machine).
  * **Your Flask application code** (e.g., `app.py`).
  * Basic understanding of the Linux command line.
  * Access to your home Wi-Fi router settings (for viewing PC's IP and configuring client DNS).

\<hr/\>

## Setup Steps 🚀

Follow these steps on your Linux PC.

### 1\. Initial Setup & Dependencies

1.  **Update System & Install Essentials:**

    ```bash
    sudo apt update
    sudo apt upgrade -y
    sudo apt install python3 python3-pip dnsmasq git -y
    ```

2.  **Clone Your Flask App (or copy files):**

    ```bash
    # Example for cloning from Git
    git clone your_repo_url /home/dhruv/webapp/appsox
    cd /home/dhruv/webapp/appsox
    ```

    Make sure you navigate to the directory containing your `app.py` file.

3.  **Create & Activate Virtual Environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

    Your terminal prompt should now show `(venv)` at the beginning.

4.  **Install Python Dependencies:**

    ```bash
    pip install flask gunicorn
    # Install any other dependencies your app requires
    # pip install -r requirements.txt
    ```

\<hr/\>

### 2\. Configure Dnsmasq (Local DNS Server)

This allows `apps.dhruv` to resolve to your PC's IP address.

1.  **Get Your PC's Local IP Address:**

    ```bash
    ip a
    ```

    Look for the `inet` address under your primary network interface (e.g., `eth0` in Crostini, `wlan0` or `eth0` on a Pi). Let's assume it's `100.115.92.203` (Chromebook Linux) or `192.168.1.100` (typical LAN IP) for this example. This IP is crucial.

2.  **Create `dnsmasq` Custom Configuration:**

    ```bash
    sudo nano /etc/dnsmasq.d/mywebapp.conf
    ```

    Add this single line, replacing `YOUR_PC_IP` with the IP address you found in the previous step:

    ```
    address=/apps.dhruv/YOUR_PC_IP
    ```

    Save and exit (`Ctrl + O`, `Enter`, `Ctrl + X`).

3.  **Configure `dnsmasq` for Upstream DNS (Crucial for Internet Access):**
    This tells `dnsmasq` where to forward requests for domains it doesn't handle.

    ```bash
    sudo nano /etc/dnsmasq.conf
    ```

    Ensure these lines are present and uncommented (remove `#` if it's there):

    ```
    no-resolv  # Prevents dnsmasq from using /etc/resolv.conf for its upstream servers
    server=8.8.8.8 # Google Public DNS (Primary)
    server=8.8.4.4 # Google Public DNS (Secondary for redundancy)
    ```

    Save and exit.

4.  **Configure Systemd-Networkd (for Chromebook Linux/Crostini):**
    If on a Chromebook Linux container, ensure your `eth0` is configured to use both local and public DNS.

    ```bash
    sudo nano /etc/systemd/network/10-eth0.network
    ```

    Ensure the `[Network]` section includes these DNS lines:

    ```ini
    [Match]
    Name=eth0

    [Network]
    DHCP=yes
    DNS=127.0.0.1  # Points to your local dnsmasq
    DNS=8.8.8.8    # Points to a public DNS for internet
    ```

    Save and exit.

5.  **Restart Network Services:**

    ```bash
    sudo systemctl restart systemd-networkd.service # On Crostini
    sudo systemctl restart dnsmasq.service
    ```

    Check `dnsmasq` status:

    ```bash
    sudo systemctl status dnsmasq.service
    ```

    It should show `active (running)`.

\<hr/\>

### 3\. Run Your Flask App with Gunicorn

This makes your app accessible on the network.

1.  **Navigate to Your App Directory:**
    Ensure you are in the directory containing `app.py`:

    ```bash
    cd /home/dhruv/webapp/appsox
    ```

2.  **Ensure Virtual Environment is Active:**

    ```bash
    source venv/bin/activate
    ```

    Confirm `(venv)` is in your prompt.

3.  **Start Gunicorn:**

    ```bash
    gunicorn --bind 0.0.0.0:5000 app:app
    ```

      * Replace `app:app` if your Flask application instance is named differently (e.g., `app:create_app()` if it's a factory function, or `my_app:application` if your file is `my_app.py` and instance is `application`).

    Your app should now be listening. Keep this terminal open, or proceed to the next step to run it as a service.

\<hr/\>

### 4\. (Optional) Run Flask App as a Systemd Service

For reliable, automatic startup and background running.

1.  **Create a Service File:**

    ```bash
    sudo nano /etc/systemd/system/mywebapp.service
    ```

    Paste the following, **adjusting paths** to your `appsox` directory and `User`/`Group` as needed.

    ```ini
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
    ```

    Save and exit.

2.  **Enable and Start the Service:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable mywebapp.service
    sudo systemctl start mywebapp.service
    ```

3.  **Check Service Status:**

    ```bash
    sudo systemctl status mywebapp.service
    ```

    It should be `active (running)`.

\<hr/\>

## 5\. Configure Client Devices 📱

For other devices on your local network (e.g., your phone, another laptop) to use your custom domain:

1.  **Get Your PC's IP Address (again):** Confirm the IP address of the Linux PC hosting your app (e.g., `100.115.92.203` or `192.168.1.100`).

2.  **On the Client Device:**

      * Go to **Wi-Fi settings**.
      * Tap on your **connected Wi-Fi network**.
      * Find **IP Settings** or **DNS settings** and change it to **Static** or **Manual**.
      * Set **DNS 1** to your Linux PC's IP address (e.g., `100.115.92.203`).
      * Set **DNS 2** to a public DNS server like `8.8.8.8` or `1.1.1.1` (as a fallback for regular internet Browse).
      * **Save** the settings.
      * **Toggle Wi-Fi off and then on** to apply the changes.

\<hr/\>

## Access Your Application 🎉

Now, from the client device you configured, open a web browser and navigate to:

`http://apps.dhruv:5000`

You should see your Flask application\!
