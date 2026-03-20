#!/bin/bash
# Kyron Medical — AWS EC2 Deployment Script
# Run this on a fresh Ubuntu 22.04+ EC2 instance (t2.micro free tier)
#
# USAGE:
#   1. Launch EC2 (Ubuntu 22.04, t2.micro, open ports 22/80/443)
#   2. SSH in: ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
#   3. Upload this script and run: bash deploy.sh

set -e

DOMAIN="${1:-$(curl -s http://checkip.amazonaws.com)}"
PROJECT_DIR="/home/ubuntu/kyron_clinic"
REPO_URL="https://github.com/YOUR_USERNAME/kyron-medical-patient-assistant.git"

echo "=== Kyron Medical Deployment ==="
echo "Domain/IP: $DOMAIN"

# --- System packages ---
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# --- Clone repo ---
if [ ! -d "$PROJECT_DIR" ]; then
    git clone "$REPO_URL" "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# --- Python environment ---
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# --- Create .env (EDIT THIS WITH YOUR REAL KEYS) ---
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
GEMINI_API_KEY=your_key_here
SECRET_KEY=CHANGE_ME_TO_A_RANDOM_STRING
DEBUG=False
ALLOWED_HOSTS=your-domain.com,your-ec2-ip
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
VAPI_API_KEY=your_vapi_key
VAPI_PHONE_NUMBER_ID=your_vapi_phone_id
VAPI_ASSISTANT_ID=your_vapi_assistant_id
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
ENVEOF
    echo ">>> IMPORTANT: Edit .env with your real API keys!"
    echo ">>>   nano $PROJECT_DIR/.env"
fi

# --- Django setup ---
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# --- Gunicorn systemd service ---
sudo tee /etc/systemd/system/kyron.service > /dev/null << EOF
[Unit]
Description=Kyron Medical Django App
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn kyron_medical.wsgi:application \\
    --bind 127.0.0.1:8000 \\
    --workers 3 \\
    --timeout 120
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable kyron
sudo systemctl restart kyron

# --- Nginx config ---
sudo tee /etc/nginx/sites-available/kyron > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/kyron /etc/nginx/sites-enabled/kyron
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "=== Deployment Complete ==="
echo "HTTP:  http://$DOMAIN"
echo ""
echo "To add HTTPS (if you have a domain name):"
echo "  sudo certbot --nginx -d $DOMAIN"
echo ""
echo "To check logs:"
echo "  sudo journalctl -u kyron -f"
echo ""
echo "To redeploy after code changes:"
echo "  cd $PROJECT_DIR && git pull && source venv/bin/activate"
echo "  pip install -r requirements.txt && python manage.py migrate"
echo "  python manage.py collectstatic --noinput"
echo "  sudo systemctl restart kyron"
