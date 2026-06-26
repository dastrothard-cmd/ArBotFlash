TREE ID TRAINER — HOSTED INSTALLABLE EDITION

WHAT THIS PACKAGE DOES
- Runs from a secure web address.
- Installs on Android from Chrome like an app.
- Flashcards and games keep working offline.
- Direct microphone permission works when hosted.
- The AI address is built in and hidden.
- No advanced connection box appears in the app.

WHAT STILL HAS TO HAPPEN
This ZIP is ready to publish, but it is not online yet. Publishing requires:
1. A Vercel hosting account.
2. An OpenAI API key added privately to the Vercel project as OPENAI_API_KEY.

The API key is never placed inside the webpage.

AFTER IT IS PUBLISHED
1. Open the web address in Chrome on Android.
2. Tap Install when the app offers it.
3. Allow microphone permission the first time you tap the microphone.
4. The learning tools work offline; AI commands need internet.

PROJECT CONTENTS
- public/index.html          Main app
- public/app.webmanifest    Android installation details
- public/service-worker.js  Offline support and updates
- public/icons/             App icons
- api/ai.js                 Private AI connection
- vercel.json               Hosting configuration
