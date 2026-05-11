# AWS Lightsail Deployment

This guide deploys the Streamlit app on an Ubuntu Lightsail instance.

## 1. Create Lightsail Server

1. Open AWS Console.
2. Search for `Lightsail`.
3. Create instance.
4. Choose `Linux/Unix`.
5. Choose `Ubuntu`.
6. Start with the `$5/month` plan for MVP testing.
7. Name it `deep-research-ai`.
8. Create the instance.

## 2. Open Firewall Ports

In Lightsail Networking, allow:

- `SSH` port `22`
- `HTTP` port `80`
- `HTTPS` port `443`

Do not expose Streamlit port `8501` publicly if you use Nginx.

## 3. Connect With SSH

Use the browser SSH button inside Lightsail.

## 4. Install System Packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx
```

## 5. Clone Project

```bash
cd /home/ubuntu
git clone YOUR_GITHUB_REPO_URL deep_research
cd deep_research
```

## 6. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 7. Add Environment Variables

Create `.env` on the server:

```bash
nano .env
```

Paste your real keys:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
MISTRAL_API_KEY=your_mistral_key
TAVILY_API_KEY=your_tavily_key
APP_ENV=production
SESSION_SECRET_KEY=your_random_secret
NEWS_API_KEY=
GITHUB_TOKEN=
EXA_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_PERSON_ID=
```

Generate `SESSION_SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 8. Test Streamlit

```bash
source .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Stop with `Ctrl+C`.

## 9. Run App As Background Service

```bash
sudo cp deploy/deep-research.service /etc/systemd/system/deep-research.service
sudo systemctl daemon-reload
sudo systemctl enable deep-research
sudo systemctl start deep-research
sudo systemctl status deep-research
```

Check logs:

```bash
sudo journalctl -u deep-research -f
```

## 10. Put Nginx In Front

```bash
sudo cp deploy/nginx-deep-research.conf /etc/nginx/sites-available/deep-research
sudo ln -s /etc/nginx/sites-available/deep-research /etc/nginx/sites-enabled/deep-research
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Now open:

```text
http://YOUR_LIGHTSAIL_PUBLIC_IP
```

## 11. Later: Add Domain And HTTPS

After the app works on IP:

1. Point your domain A record to the Lightsail static IP.
2. Install Certbot.
3. Generate SSL certificate.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

## What Not To Commit

Never commit:

- `.env`
- `.venv/`
- `research.db`
- `anonymous_usage.sqlite3`
- `output/`
- `.session_secret`

