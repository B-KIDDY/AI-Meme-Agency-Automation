# 📸 How to Post Real Memes to Instagram

The system already supports **live** Instagram posting via the official Graph API.
Follow these steps once and it will post automatically every run.

---

## 1. Convert your Instagram account

- Go to Instagram → Settings → Account → Switch to **Professional Account**
- Choose **Business** (or Creator)
- Link it to a **Facebook Page** (create one if you don’t have it)

## 2. Create a Facebook App

1. Go to https://developers.facebook.com/
2. Create a new App → type **Business**
3. Add the product **Instagram Graph API**
4. Also add **Facebook Login** if asked

## 3. Get permissions & token

You need these permissions (App Review may be required for production):

- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`

**Easiest way to get a long-lived token for testing:**

1. Go to **Graph API Explorer** (https://developers.facebook.com/tools/explorer/)
2. Select your App
3. Add the permissions above
4. Generate a User Token → then exchange it for a **Page Access Token**
5. Exchange the short-lived token for a **long-lived** one (60 days) using:

```
GET https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=YOUR_APP_ID
  &client_secret=YOUR_APP_SECRET
  &fb_exchange_token=SHORT_LIVED_TOKEN
```

## 4. Find your Instagram Business Account ID

```
GET https://graph.facebook.com/v19.0/me/accounts?access_token=PAGE_TOKEN
```

Then for the page:

```
GET https://graph.facebook.com/v19.0/{page-id}?fields=instagram_business_account&access_token=PAGE_TOKEN
```

The `instagram_business_account.id` is what you need.

## 5. Public image hosting (mandatory)

Instagram **cannot** read files from your computer.  
You must give it a public HTTPS URL.

### Easiest option – Imgur (free)

1. Go to https://api.imgur.com/oauth2/addclient
2. Register an application → get **Client ID**
3. Put it in `.env`:

```
IMGUR_CLIENT_ID=xxxxxxxx
```

The system will automatically upload every meme to Imgur before posting.

### Alternative – your own server

Host the `generated_memes/` folder on any public HTTPS server and set:

```
PUBLIC_IMAGE_BASE_URL=https://yourdomain.com/memes
```

## 6. Configure the project

```bash
cp .env.example .env
```

Edit `.env`:

```
RUN_MODE=live
INSTAGRAM_ACCESS_TOKEN=EAAxxxx...          # long-lived page token
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841xxxxx  # IG business account ID
IMGUR_CLIENT_ID=your_imgur_client_id
```

## 7. Test

```bash
python main.py
```

You should see:

```
🚀 LIVE publishing meme #XX …
☁️  Uploaded to Imgur → https://i.imgur.com/xxxx.png
📦 Container created: xxxxx
✅ Published! Media ID: xxxxx
```

---

## Common errors

| Error | Solution |
|-------|----------|
| `(#10) Application does not have permission` | Request `instagram_content_publish` and wait for App Review |
| `Invalid image URL` | Make sure the URL is public HTTPS and the image is < 8 MB |
| `Media ID is not available` | Wait 5–10 seconds after creating the container (code already waits 2s) |
| Token expired | Generate a new long-lived token |

---

## Production tips

- Use a permanent image host (Cloudinary, AWS S3 + CloudFront, your VPS)
- Store the long-lived token securely
- Schedule posts with APScheduler or a cron job
- Monitor the `logs/publish_log.jsonl` file

Once configured, every daily pipeline run will automatically post the top memes to your Instagram.
