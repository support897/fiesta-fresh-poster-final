🧹 Fiesta Fresh — Cloud Poster Setup Guide
Your script posts to Facebook groups every week — without your laptop

What you're setting up
A cheap cloud computer (~$7 AUD/month) that:

Runs 24/7 without your laptop
Posts to your Facebook groups automatically every week
Follows a rotating daily schedule (different groups each day)
Requires zero attention once set up


PART 1 — Fill in config.json FIRST
Before touching any server, open config.json and fill in:
1. Your Facebook login:
json"email": "your@email.com",
"password": "yourpassword"
2. Your 7 post templates (replace the placeholder text with your real posts):

Each template should say the same thing but with slightly different wording
This prevents Facebook from flagging identical posts

3. Your group URLs (replace GROUP_URL_1 etc with real URLs):
https://www.facebook.com/groups/goldharbour
https://www.facebook.com/groups/miamilocals
...etc
To find a group URL: open the group in Facebook → copy the URL from your browser bar.

PART 2 — Get a cloud server (Hetzner — cheapest option)
Step 1 — Create account
Go to hetzner.com → Sign up (takes 2 minutes)
Step 2 — Create a server

Click "Cloud" → "New Project" → name it "Fiesta Fresh"
Click "Add Server"
Choose:

Location: Singapore (closest to Australia)
Image: Ubuntu 24.04
Type: CX22 (2 CPU, 4GB RAM — about $7 AUD/month)
SSH Key: skip for now, use password


Click "Create & Buy Now"
Hetzner emails you the server's IP address and root password

Step 3 — Connect to your server
On Mac: Open Terminal → type:
ssh root@YOUR_SERVER_IP
Enter the password from the email.
On Windows: Download PuTTY (putty.org) → enter your IP → connect → enter password.

PART 3 — Set up the server (copy-paste these commands)
Once connected, paste these one by one:
Install Python:
bashapt update && apt upgrade -y
apt install python3 python3-pip -y
Install Playwright and dependencies:
bashpip3 install playwright pytz
playwright install chromium
playwright install-deps chromium
Create a folder for your script:
bashmkdir fiesta_poster
cd fiesta_poster

PART 4 — Upload your files to the server
You need to upload 2 files:

fb_poster_cloud.py
config.json (with your real data filled in)

Easiest way — use a free tool called FileZilla:

Download FileZilla (filezilla-project.org)
Open FileZilla → File → Site Manager → New Site
Protocol: SFTP
Host: YOUR_SERVER_IP
User: root
Password: your server password
Connect → drag your files into the fiesta_poster folder


PART 5 — Test it first (dry run)
Make sure config.json has "dry_run": true, then run:
bashcd fiesta_poster
python3 fb_poster_cloud.py
You'll see it log exactly which groups it would post to, without actually posting.
When you're happy → open config.json on your computer, change "dry_run": false, re-upload it.

PART 6 — Run it permanently in the background
This command runs the script forever, even after you close your terminal:
bashnohup python3 fb_poster_cloud.py > output.log 2>&1 &
To check it's running:
bashps aux | grep fb_poster
To view the live log:
bashtail -f fiesta_poster.log
To stop it:
bashpkill -f fb_poster_cloud.py

What happens weekly
DayActionMondayPosts to groups 1-7TuesdayPosts to groups 8-14WednesdayPosts to groups 15-21ThursdayPosts to groups 22-28FridayPosts to groups 29-35SaturdayPosts to groups 36-42SundayPosts to groups 43-50
Every group gets one post per week. The script waits 5-10 minutes between each post to look human.

Costs summary
ItemCostHetzner CX22 server~$7 AUD/monthYour time to set up~1 hour (once)Ongoing maintenanceZero

Common issues
"Login failed"
→ Check email/password in config.json. If you have 2FA on Facebook, disable it temporarily or approve the first login manually.
"Could not find post composer"
→ Some groups have posting restrictions or require admin approval. The script logs which groups failed.
Script stopped running
→ SSH into your server and restart with the nohup command above.
Want to add more groups later?
→ Just edit config.json on your computer, re-upload it via FileZilla, restart the script.
