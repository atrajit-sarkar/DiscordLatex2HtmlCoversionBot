# 🚀 AWS EC2 Deployment Guide for Watashino LaTeX Bot

> **Transform your Discord server with professional LaTeX rendering in the cloud**

This comprehensive guide will walk you through deploying Watashino LaTeX Bot on an AWS EC2 instance, ensuring reliable 24/7 operation with optimal performance and security.

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ **AWS Account** with billing configured
- ✅ **Discord Bot Token** from [Discord Developer Portal](https://discord.com/developers/applications)
- ✅ **Basic terminal/SSH knowledge**
- ✅ **Domain name** (optional, for custom webhook URLs)

---

## 🏗️ Part 1: AWS EC2 Setup

### Step 1: Launch EC2 Instance

1. **Navigate to EC2 Dashboard**
   ```
   AWS Console → Services → EC2 → Instances
   ```

2. **Click "Launch Instance"**

3. **Configure Instance Settings:**

   | Setting | Recommended Value | Notes |
   |---------|------------------|-------|
   | **Name** | `watashino-latex-bot` | Easy identification |
   | **OS** | Ubuntu Server 22.04 LTS | Stable, well-supported |
   | **Instance Type** | `t3.micro` (Free tier) or `t3.small` | Sufficient for bot operations |
   | **Key Pair** | Create new or use existing | Required for SSH access |
   | **Storage** | 20 GB gp3 SSD | Adequate for LaTeX packages |

4. **Security Group Configuration:**
   ```
   Inbound Rules:
   - SSH (22) from Your IP: 0.0.0.0/0 (or restrict to your IP)
   - HTTP (80) from Anywhere: 0.0.0.0/0 (optional, for web interface)
   - HTTPS (443) from Anywhere: 0.0.0.0/0 (optional, for web interface)
   ```

5. **Launch Instance** 🎉

### Step 2: Connect to Your Instance

```bash
# Replace with your actual key file and instance IP
ssh -i "your-key.pem" ubuntu@your-ec2-public-ip

# Example:
ssh -i "watashino-bot.pem" ubuntu@3.84.123.45
```

---

## ⚙️ Part 2: System Setup

### Step 1: Update System

```bash
# Update package lists and upgrade system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git unzip htop nano
```

### Step 2: Install Python 3.11+

```bash
# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version  # Should be 3.10+ (Ubuntu 22.04 default)
pip3 --version
```

### Step 3: Install LaTeX Distribution (with TeX4ht and dvisvgm)

```bash
# Install TeX Live (comprehensive LaTeX distribution)
sudo apt install -y texlive-full

# This installs ~4GB of LaTeX packages - be patient!
# Alternative minimal install (if storage is limited):
# sudo apt install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended

# Verify key LaTeX tools
pdflatex --version
htlatex --version       # TeX4ht driver (should exist)
make4ht --version       # Preferred TeX4ht wrapper (should exist)
dvisvgm --version       # For SVG/TikZ outputs in HTML
```

### Step 4: Install Ghostscript

```bash
# Install Ghostscript for PDF processing
sudo apt install -y ghostscript

# Verify installation
gs --version
```

---

## 🤖 Part 3: Bot Deployment

### Step 1: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone the bot repository
git clone https://github.com/your-username/InLaTeXbot.git
cd InLaTeXbot

# Alternative: Upload via SCP if using private repo
# scp -i "your-key.pem" -r ./InLaTeXbot ubuntu@your-ec2-ip:~/
```

### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Configure your `.env` file (minimum):**
```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_for_testing

# Optional: Enable message content for chat rendering
DISCORD_ENABLE_MESSAGE_CONTENT=true

# Optional: PDF margin customization (points)
LATEXBOT_PDF_MARGIN_PT=24

# Optional: Transparent PNG rendering
LATEXBOT_TRANSPARENT=false

# Optional: Prefer a specific TeX engine for PDF path
# LATEXBOT_TEX_ENGINE=lualatex

# Optional: Increase timeouts for long compiles (seconds)
# LATEXBOT_PDFLATEX_TIMEOUT=90
# LATEXBOT_HTML_TIMEOUT=180

# Optional (Windows): If TeX binaries aren’t on PATH, prepend them
# LATEXBIN_DIRS=C:\\texlive\\2024\\bin\\windows;C:\\Program Files\\MiKTeX\\miktex\\bin\\x64

# HTML Preview Server (optional)
# HTML_HOST=0.0.0.0
# HTML_PORT=8088
# HTML_BASE_URL=https://your-public-hostname-or-tunnel

# GitHub Pages Deployment (optional, for /deployhtml)
# GITHUB_PAT=ghp_your_pat_here
# GITHUB_OWNER=your-github-username-or-org
# GITHUB_REPO=your-repo
# GITHUB_BRANCH=gh-pages
# GITHUB_DIR_PREFIX=sites
# GITHUB_PAGES_BASE_URL=https://yourname.github.io/your-repo
```

### Step 4: Test Installation

```bash
# Start the bot
python main.py

# In Discord, run:
# /start      (welcome)
# /diagnose   (lists detected pdflatex/ghostscript/htlatex/make4ht/dvisvgm)
```

---

## 🔧 Part 4: Production Setup

### Step 1: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/watashino-latex-bot.service
```

**Service configuration:**
```ini
[Unit]
Description=Watashino LaTeX Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/InLaTeXbot
Environment=PATH=/home/ubuntu/InLaTeXbot/venv/bin
ExecStart=/home/ubuntu/InLaTeXbot/venv/bin/python main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=watashino-latex-bot

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable watashino-latex-bot

# Start the service
sudo systemctl start watashino-latex-bot

# Check status
sudo systemctl status watashino-latex-bot

# View logs
sudo journalctl -u watashino-latex-bot -f
```

### Step 3: Setup Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/watashino-latex-bot
```

**Log rotation config:**
```
/home/ubuntu/InLaTeXbot/log/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        sudo systemctl reload watashino-latex-bot
    endscript
}
```

---

## 🌐 Part 5: Web Interface Setup (Optional)

### Step 1: Install Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 2: Configure Nginx

```bash
# Create site configuration
sudo nano /etc/nginx/sites-available/watashino-latex-bot
```

**Nginx configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;  # Replace with your domain
    
    root /home/ubuntu/InLaTeXbot/docs;
    index index.html;
    
    location / {
        try_files $uri $uri/ =404;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
```

### Step 3: Enable Site
## 🌐 Part 5b: Built‑in Preview Server (Optional)

The bot can host temporary previews of generated HTML sites via an internal server (aiohttp).

Configure with environment variables in `.env`:

```bash
# Bind address (127.0.0.1 for local only, 0.0.0.0 for remote access)

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/watashino-latex-bot /etc/nginx/sites-enabled/

```

Usage inside Discord:
- Run `/tex2html` → the reply includes a “Preview URL” if the host is running
- Manage previews: `/htmlpreviews`, `/htmlkill token:<token>`, `/htmlkillall`

Notes:
- If `HTML_HOST=127.0.0.1`, preview links only work from the same machine.
- Set `HTML_HOST=0.0.0.0` and a proper `HTML_BASE_URL` to access from elsewhere.

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Step 4: SSL Certificate (Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## 🔒 Part 6: Security & Optimization

### Step 1: Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS (if using web interface)
sudo ufw allow 80
sudo ufw allow 443

# Check status
sudo ufw status verbose
```

### Step 2: Automatic Updates

```bash
# Install unattended upgrades
sudo apt install -y unattended-upgrades

# Configure automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Step 3: Monitoring Setup

```bash
# Create monitoring script
nano ~/monitor-bot.sh
```

**Monitoring script:**
```bash
#!/bin/bash
# Bot health check script

BOT_SERVICE="watashino-latex-bot"
LOG_FILE="/home/ubuntu/bot-monitor.log"

# Check if service is running
if systemctl is-active --quiet $BOT_SERVICE; then
    echo "$(date): Bot is running ✅" >> $LOG_FILE
else
    echo "$(date): Bot is down ❌ - Restarting..." >> $LOG_FILE
    sudo systemctl restart $BOT_SERVICE
    echo "$(date): Bot restarted" >> $LOG_FILE
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$(date): Warning: Disk usage at ${DISK_USAGE}% 🚨" >> $LOG_FILE
fi
```

```bash
# Make executable
chmod +x ~/monitor-bot.sh

# Add to crontab (runs every 5 minutes)
crontab -e
# Add this line:
# */5 * * * * /home/ubuntu/monitor-bot.sh
```

---

## 📊 Part 7: Maintenance & Troubleshooting

### Essential Commands

```bash
# Service Management
sudo systemctl status watashino-latex-bot    # Check status
sudo systemctl restart watashino-latex-bot   # Restart bot
sudo systemctl stop watashino-latex-bot      # Stop bot
sudo systemctl start watashino-latex-bot     # Start bot

# View Logs
sudo journalctl -u watashino-latex-bot -f    # Live logs
sudo journalctl -u watashino-latex-bot --since "1 hour ago"  # Recent logs

# System Monitoring
htop                    # System resources
df -h                   # Disk usage
free -h                 # Memory usage
sudo ufw status         # Firewall status
```

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Bot Won't Start** | Service fails immediately | Check `.env` file, verify Discord token |
| **LaTeX Errors** | "pdflatex not found" | Reinstall texlive: `sudo apt install texlive-full` |
| **HTML tools missing** | `make4ht`/`htlatex`/`dvisvgm` not found | Install TeX4ht + dvisvgm (included in `texlive-full`), then check `/diagnose` |
| **GitHub deployment 404** | `/deployhtml` fails with 404 | Ensure `GITHUB_OWNER/REPO` are correct, PAT has `contents:write`, and `GITHUB_BRANCH` exists (e.g., create `gh-pages`) |
| **Memory Issues** | Bot crashes randomly | Upgrade to larger instance type |
| **Permission Errors** | File access denied | Fix ownership: `sudo chown -R ubuntu:ubuntu ~/InLaTeXbot` |
| **Network Issues** | Bot disconnects frequently | Check security groups, verify internet connectivity |

### Performance Optimization

```bash
# Clean up old logs
sudo find /home/ubuntu/InLaTeXbot/log -name "*.log" -mtime +7 -delete

# Clean up temporary files
sudo find /tmp -name "*latex*" -mtime +1 -delete

# Update dependencies
cd ~/InLaTeXbot
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

---

## 🎯 Part 8: Discord Bot Invitation

### Step 1: Configure Bot Permissions

In Discord Developer Portal:
1. Go to your bot's **OAuth2 → URL Generator**
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Send Messages
   - Use Slash Commands
   - Attach Files
   - Read Message History

### Step 2: Invite Bot to Server

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=274877991936&scope=bot%20applications.commands
```

### Step 3: Test Bot Functions

```
/start                              # Welcome message
/latex code:"$E = mc^2$"           # Test LaTeX rendering
/diagnose                          # Check dependencies
/settings                          # Configure bot settings
```

---

## � Part 9: GitHub Pages Deployment (Optional)

You can deploy generated HTML sites to GitHub Pages using the `/deployhtml` command.

1) Prepare repository and branch

```bash
# In your repo, ensure a Pages-enabled branch exists (e.g., gh-pages)
# If not present, create it and push at least one commit, then enable Pages
```

2) Create a Personal Access Token (classic or fine-grained)

- Public repo: `public_repo` and `contents:write`
- Private repo: `repo` (or `contents:write` with access to the repo)

3) Configure `.env`

```bash
GITHUB_PAT=ghp_your_pat
GITHUB_OWNER=your-github-username-or-org
GITHUB_REPO=your-repo
GITHUB_BRANCH=gh-pages         # or main (if Pages is configured from main)
# Optional: upload under a subfolder
GITHUB_DIR_PREFIX=sites
# Optional: override computed URL (custom domain or different base)
# GITHUB_PAGES_BASE_URL=https://yourname.github.io/your-repo
```

4) Test and deploy

- Run `/tex2html` in Discord to generate a site
- Run `/deployhtml` (or `/deployhtml slug:my-folder`)
- The bot replies with a Pages URL

Troubleshooting:
- If you see 404 errors, ensure the branch exists and the token has access. The bot now includes GitHub’s error body for clarity.

---

## �📈 Part 10: Scaling & Advanced Features

### Auto Scaling Setup

For high-traffic servers, consider:

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

### Load Balancer Configuration

For multiple bot instances:
1. Create Application Load Balancer
2. Deploy bot on multiple EC2 instances
3. Use shared Redis for session management

### Backup Strategy

```bash
# Create backup script
nano ~/backup-bot.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration and logs
tar -czf "$BACKUP_DIR/bot-backup-$DATE.tar.gz" \
    ~/InLaTeXbot/.env \
    ~/InLaTeXbot/resources/ \
    ~/InLaTeXbot/log/

# Keep only last 7 backups
find $BACKUP_DIR -name "bot-backup-*.tar.gz" -mtime +7 -delete

echo "Backup completed: bot-backup-$DATE.tar.gz"
```

---

## 🎉 Congratulations!

Your Watashino LaTeX Bot is now running 24/7 on AWS EC2! 🚀

### Quick Reference Card

| Action | Command |
|--------|---------|
| **Check Bot Status** | `sudo systemctl status watashino-latex-bot` |
| **View Live Logs** | `sudo journalctl -u watashino-latex-bot -f` |
| **Restart Bot** | `sudo systemctl restart watashino-latex-bot` |
| **Update Bot** | `cd ~/InLaTeXbot && git pull && sudo systemctl restart watashino-latex-bot` |
| **Check Resources** | `htop` |
| **Monitor Disk** | `df -h` |

### Support & Resources

- 📖 **Documentation**: Check `README.md` for detailed bot usage
- 🌐 **Web Interface**: Visit your domain to see the beautiful docs
- 💬 **Discord**: Test with `/start` and `/diagnose` commands
- 🔧 **Troubleshooting**: Review logs with `journalctl` commands above

---

## 💻 Windows (PowerShell) Quickstart

1) Install prerequisites

- Python 3.11+
- TeX Live or MiKTeX
    - TeX Live typical bin: `C:\texlive\2024\bin\windows`
    - MiKTeX typical bin: `C:\Program Files\MiKTeX\miktex\bin\x64`
- Ghostscript
    - `gswin64c.exe` on PATH

2) Clone and install

```powershell
pip install -r requirements.txt
```

3) Configure `.env`

```powershell
# Minimal
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_test_guild_id

# Ensure TeX tools are found (prepend paths)
LATEXBIN_DIRS=C:\\texlive\\2024\\bin\\windows;C:\\Program Files\\MiKTeX\\miktex\\bin\\x64

# Optional: preview hosting
# HTML_HOST=127.0.0.1
# HTML_PORT=8088
```

4) Run the bot

```powershell
python .\main.py
```

5) In Discord, use `/diagnose` to confirm detection of `pdflatex`, `gs`, `htlatex`/`make4ht`, and `dvisvgm`.

> **💡 Pro Tip**: Bookmark this guide and keep your EC2 instance information handy. Consider setting up CloudWatch alerts for advanced monitoring!

**Happy LaTeX rendering! 🎨✨**