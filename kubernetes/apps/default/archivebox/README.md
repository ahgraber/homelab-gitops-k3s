# [ArchiveBox](https://archivebox.io/)

Open source self-hosted web archiving. Takes URLs/browser history/bookmarks/Pocket/Pinboard/etc., saves HTML, JS, PDFs, media, and more...

## Chrome Configuration

A machine Chrome/Chromium user profile can be configured to preserve cookies/sessions to log into sites behind authentication/paywall during archiving.
This may also be useful in reducing captcha checks.

1. In archivebox container, run:

   ```sh
   /usr/bin/chromium-browser \
   --user-data-dir=/data/personas/Default/chrome_profile \
   --profile-directory=Default \
   --disable-gpu \
   --disable-features=dbus \
   --disable-dev-shm-usage \
   --start-maximized \
   --no-sandbox \
   --disable-setuid-sandbox \
   --no-zygote \
   --disable-sync \
   --no-first-run
   ```

2. Port Forward into NoVNC container in archivebox pod, and use Chrome to access / log into sites

## References

- [The Future of ArchiveBox - HedgeDoc](https://docs.sweeting.me/s/archivebox-plugin-ecosystem-announcement)
