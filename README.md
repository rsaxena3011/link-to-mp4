# Link to MP4

**Paste a link. Save the video.** A free browser interface with a small local Python helper. Videos go straight to a folder on your computer.

Start with **Start-Windows.cmd** on Windows. You do not need to open the App folder.

## First-time setup

1. **Extract the whole ZIP** into a normal, writable folder, such as `Documents/LinkToMP4`. Do not run it inside the ZIP, in Program Files, or from a temporary preview.
2. Install **Python 3.10 or newer** if you do not already have it. Python 3.12 is a suitable choice. Official installers: <https://www.python.org/downloads/>. On Windows, select **Add Python to PATH** if the installer offers it, then close and reopen the launcher.
3. Run the launcher for your computer. The first start creates a private environment in this app folder and downloads yt-dlp, FFmpeg and, when needed, Deno. This needs internet and can take a few minutes. Keep the console window open.
4. Your browser opens automatically. Look for **Helper connected** in the top right. If it does not open, copy the full local address printed in the console, including the part after `#`.

**Windows 10/11, 64-bit:** double-click `Start-Windows.cmd`. If Windows uses a Store placeholder instead of an installed Python, install Python from the official link above. If an existing Python is too old, install a newer version. The app does not require administrator access.

**macOS:** install Python from python.org, then open `Start-Mac.command`. If it is not executable, open Terminal in this folder and run `sh Start-Mac.command`. If Python reports a certificate error, run the **Install Certificates.command** supplied with the python.org installation. Do not disable certificate verification.

**Linux:** install Python 3.10+, pip and venv through your distribution's package manager, then run `sh Start-Linux.sh` from this folder. Optional Tk support enables the folder dialog; a typed folder path also works. Some architectures may require a system FFmpeg installation if imageio-ffmpeg has no matching binary wheel.

The app uses an HTML interface, Python, and third-party media tools. There is no custom compiled app installer. Windows media dependencies do contain their own executables, installed privately during setup.

## Save a video

1. Paste the individual video's page link. For a batch, put one video link on each line, up to 50 at a time. Identical links within a batch are skipped.
2. Optionally select **Check first link** to see its title, duration and reported available heights.
3. Choose **Best available** or a maximum height, from 480p through 2160p. Best available is uncapped, including higher resolutions when a site offers them. A limit never creates a resolution the source does not have; streams with unknown height can still be selected.
4. Choose an MP4 output mode, then use the folder button or type a full local path in **Save to**. Example: `D:\Videos\Saved` on Windows. Changing the destination affects new jobs; queued jobs keep their chosen folder.
5. Select **Download MP4**. Leave the helper running. When the item says **Complete**, select **Show folder** to find the file.

Downloads are written directly to the selected drive. There is no second transfer through your browser. Files are not loaded into browser memory. Downloads are processed one at a time.

## Two MP4 output options

| Option | What happens | Best for |
| --- | --- | --- |
| **Preserve quality** (default) | Fetches the selected streams and copies them into MP4 without re-encoding. Stops if the codecs cannot be packed into MP4. | Keeping the quality available from the website. A modern player may be needed. |
| **Compatible MP4** | Keeps H.264/AAC streams when already suitable; otherwise converts to H.264 video and AAC audio. Conversion can change quality and takes longer. | Common editors and players. Known HDR sources requiring conversion are stopped; use Preserve quality for those. |

**Best available is not a guarantee of the original upload.** Platforms commonly recompress uploads, and not every available stream is the uploader's original file. MP4 is a container: its filename alone does not guarantee H.264 or compatibility with every player. The app keeps one video stream and, when present, one audio stream. It does not add subtitles, all alternate audio tracks, chapters or cover artwork. A silent source remains silent. It does not upscale; compatible conversion may add a one-pixel pad for codec compatibility.

## Queue controls

- **Pause queue:** the current video continues; the next items wait. **Resume queue** starts them again.
- **Cancel:** stops the selected job and removes that job's temporary files. **Retry** starts a fresh download from the beginning.
- **Use link:** restores the link and its quality options so you can change settings and add it again. To change a failed Preserve quality job to Compatible MP4, use this button, change the output, then add it again.
- **Clear finished:** removes completed, failed, cancelled and interrupted entries from history. Saved video files are kept.
- **Show folder:** opens the destination folder in your system file manager. It does not open or upload the video.
- **Help → Exit helper:** stops the app. Closing just the browser tab does not stop the helper. You can also press Ctrl+C in the helper console.

The app remembers up to 200 recent queue entries. Unfinished jobs are marked **Interrupted** after a restart; they do not silently restart. If your computer loses power, any job-specific temporary directory is cleaned on the next launch. Keep at least two to three times the final file size free during download and MP4 preparation; conversions can need more.

Existing files are never intentionally overwritten. A repeat filename becomes `Video (2).mp4`, `Video (3).mp4`, and so on. The app never deletes completed videos. To remove saved videos, use your file manager.

## Sites and limits

The yt-dlp engine includes integrations for YouTube, Instagram, Facebook, Vimeo, TikTok, Pinterest and many other sites. **An integration is not a guarantee that a particular link will work.** Private content, login walls, regional restrictions, rate limits, removed videos, bot checks, and website changes can prevent downloads. Use only videos you own or are allowed to download, consistent with the source site's rules.

This version handles individual, publicly accessible videos. It does not import browser cookies, sign in to sites, circumvent DRM, download live/upcoming streams, or expand whole playlists. Multi-video posts may need a link to an individual video. There is no cloud downloading service, proxy service or CAPTCHA solver.

Try the video's own page link instead of a search results page, profile, collection or feed. Direct public MP4/WebM links can also work. Local network links are not accepted through the interface.

## Updates and troubleshooting

**A site stopped working:** finish or cancel queued items, then choose **Help → Update download engine**. This upgrades the download tools and retries a missing JavaScript-runtime setup. Site support can change at any time.

**The helper cannot start:** open a terminal in this folder and run one of these:

```text
Windows:  Start-Windows.cmd --update
macOS:    sh Start-Mac.command --update
Linux:    sh Start-Linux.sh --update
```

**Helper offline:** use the Start launcher, not `App/index.html`. Keep its console open. If the helper is already running, open the complete address printed in that console. Port 8765 must be available. Close another instance before starting again. The connection address contains a local session token; do not share it.

**YouTube runtime missing:** use Update download engine, or install Deno 2.3+ from <https://docs.deno.com/runtime/getting_started/installation/> and restart. An existing Node.js 22+ installation is also recognized. Setup downloads a missing Deno from its official GitHub release and verifies the release SHA-256 checksum. If the network blocks the download, other supported sites may still work.

**Folder picker unavailable:** paste the full folder path in Save to. On Linux, installing your distribution's Tk package may enable the picker. On a headless machine, use the typed path.

**File will not play in an older player/editor:** use a current player, or select Use link and download again as Compatible MP4. A container change does not change the codecs inside it.

**No space / permission denied / path too long:** choose a writable folder with a shorter path and enough free space, then retry. Temporary files are created on the destination drive.

**Moved the app after setup:** close the helper, remove this app's `.runtime` folder, and run Start again to rebuild the private environment in the new location. Your downloaded videos are in the destination you chose.

**Network or certificate errors:** check your connection and system clock; update Python's certificate setup if needed. A company network may block package downloads or video platforms. Do not disable security tools or certificate checking.

## Privacy and uninstalling

- The helper listens only on `127.0.0.1:8765`. It uses a random session token and checks browser origin/host headers. It is designed for one user on one computer, not public hosting or a shared server.
- Queue links, titles, file paths, settings and error summaries are stored locally in `.data/state.json`. This can include private query parameters in links you paste. Clearing finished entries removes them from that history; it is not secure disk erasure.
- The video sites receive the network requests needed to fetch content. Setup and updates contact PyPI and official Deno release servers. No app analytics or upload endpoint is included.
- To uninstall: stop the helper, then remove the extracted app folder, including `.runtime` and `.data`. Your downloaded videos stay in their chosen folder. Python, or any Deno/Node installation you installed separately, remains installed.

## Package contents

| File/folder | Purpose |
| --- | --- |
| `Start-Windows.cmd` | Windows launcher and first-time setup |
| `Start-Mac.command` | macOS launcher |
| `Start-Linux.sh` | Linux launcher |
| `App/` | `app.py` local helper and `index.html` browser interface |
| `Images/` | Horizontal, vertical and square banners, product image, and image-generation prompts |
| `README.md` | This setup and user guide |
| `Listing-Copy.txt` | Free-product listing, feature copy, FAQ and launch captions |
| `LICENSE.txt` | App license and third-party notices |
| `.gitignore` | Keeps runtime files and personal queue history out of Git |

There is no npm install, build step, API key, paid subscription or app account. Source code is editable. After startup, private runtime/data folders are generated automatically and are not part of the distribution ZIP.

## Sharing this free project

Use the original `LinkToMP4-Complete-Package.zip` as the downloadable product. Set the listing price to **free**. Listing copy and artwork are included. For GitHub, put the contents of this `LinkToMP4` folder at the repository root; use the README as the project description and the ZIP as a release attachment. GitHub Pages alone cannot run the Python helper.

Do not publish your generated `.runtime`, `.data`, downloaded videos, or local session address. The supplied `.gitignore` covers the runtime and queue history. Platform upload rules and cover crops can change; preview the chosen image before publishing. Nothing has been published on your behalf.

## Validation notes for version 1.0.0

Validated in Linux with Python 3.12, yt-dlp 2026.8.19, imageio-ffmpeg 0.6.0 and Node 24. Tests use generated media owned by this project. Real downloads from a local HTTP fixture, separate audio/video merging, MP4 remuxing, H.264/AAC conversion, file collision handling, queue APIs, restart recovery, session/origin checks and UI logic were exercised. Preserve-quality output was checked with video-packet hashes.

A clean first-start installation and authenticated helper startup/shutdown also passed. There were 18 backend/media checks and 6 interface logic checks. The HTML layout and help controls were inspected in Chrome, including a narrow layout with clearly labeled sample queue data. Browser-to-helper integration was covered by API and UI checks separately; the managed browser preview could not run the Python environment. Live downloads from the six named social platforms, native Windows/macOS setup and native folder dialogs have not been verified in this environment. Site availability is determined when a real link is tried; no universal-support claim is made.

## Components and references

- yt-dlp: <https://github.com/yt-dlp/yt-dlp>
- Extractor list: <https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md>
- JavaScript runtime setup: <https://github.com/yt-dlp/yt-dlp/wiki/EJS>
- FFmpeg: <https://ffmpeg.org/>
- imageio-ffmpeg: <https://github.com/imageio/imageio-ffmpeg>
- Deno: <https://deno.com/>

Third-party tools retain their own licenses. See LICENSE.txt. This project is independent and is not affiliated with the video platforms.
