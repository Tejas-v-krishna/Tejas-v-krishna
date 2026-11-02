# Publish this profile

The README only appears on your GitHub profile when it lives in a **public** repository named exactly like your username: `Tejas-v-krishna/Tejas-v-krishna`.

## 1. Create the profile repository

1. Go to <https://github.com/new>.
2. Repository name: `Tejas-v-krishna`.
3. Set it to **Public**.
4. Do not add a README, `.gitignore`, or license (this folder already has them).
5. Create the repository.

## 2. Push this folder

From this folder:

```powershell
git init
git add .
git commit -m "feat: custom profile README"
git branch -M main
git remote add origin https://github.com/Tejas-v-krishna/Tejas-v-krishna.git
git push -u origin main
```

If the remote already exists:

```powershell
git remote set-url origin https://github.com/Tejas-v-krishna/Tejas-v-krishna.git
git push -u origin main
```

## 3. Let the stats update themselves

The workflow in `.github/workflows/profile-assets.yml` refreshes `assets/stats.svg` and `assets/activity.svg` every day.

1. Open the repository on GitHub.
2. Go to **Settings → Actions → General → Workflow permissions**.
3. Select **Read and write permissions** and save.
4. Go to **Actions → Update profile assets → Run workflow**.

The first run needs the assets to exist. They are already committed, so the workflow will simply keep them current.

To refresh them locally:

```powershell
$env:GITHUB_TOKEN = gh auth token
$env:GITHUB_LOGIN = "Tejas-v-krishna"
python scripts/update_stats.py
```

## 4. Finish the profile details

The README cannot set these through the API, so do them in GitHub's UI:

- **Profile photo** — upload `assets/avatar.png` if you want the matching dithered astronaut portrait. You can also use your own high-contrast photo.
- **Bio** — paste: `Full-stack developer & UI/UX designer. Building performant, design-driven products with React, TypeScript, and Node.js.`
  (The GitHub CLI token needs the `user` scope to change this via API. If you want to set it from the terminal, run `gh auth refresh -h github.com -s user` first.)
- **Location** — add your city/country if you want it shown.
- **Website** — link your portfolio.
- **Pinned repositories** — pin `usesawn`, `flowdesk`, `figma-design-system-plugin`, and your portfolio.
- **Theme** — use GitHub's dark theme for the intended look.

## 5. Customize the content

- Links and email: `README.md`.
- Bio, about copy, and featured projects: `README.md`.
- Tech stack: change the `i=` list in the Skill Icons URL in `README.md`.
- Hero images: `assets/source/eye.png`, `scripts/build_assets.py` (still) and `scripts/build_hero_gif.py` (blink).
- Stats card layout: `scripts/update_stats.py` (`render_stats`).
- Activity graph layout: `scripts/update_stats.py` (`render_activity`).

Rebuild the artwork after editing `build_assets.py` or `build_hero_gif.py`:

```powershell
python scripts/build_assets.py
python scripts/build_hero_gif.py
```

The scripts need Pillow and numpy:

```powershell
python -m pip install pillow numpy
```
