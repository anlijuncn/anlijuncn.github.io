# Lijun An's Academic Homepage

This repository hosts the source code for [www.anlijun.cn](https://www.anlijun.cn), the personal academic homepage of Lijun An.

## What Is Included

- Academic homepage built with Jekyll.
- Google Scholar citation crawler in [google_scholar_crawler](./google_scholar_crawler).
- GitHub Actions workflow that updates Google Scholar citation JSON on the `google-scholar-stats` branch.

## Google Scholar Citations

The homepage reads citation data from:

- `https://raw.githubusercontent.com/anlijuncn/anlijuncn.github.io/google-scholar-stats/gs_data.json`

The crawler also writes `gs_data_shieldsio.json` for Shields.io compatibility, but the homepage citation badge now reads `gs_data.json` directly to avoid stale image caching.

The workflow runs when GitHub Pages builds the site, every Monday at `08:00 UTC`, and when manually triggered from GitHub Actions.

For a local manual update:

```bash
GOOGLE_SCHOLAR_ID=La_luGsAAAAJ python google_scholar_crawler/main.py
```

The fallback citation value is stored in [_pages/about.md](./_pages/about.md). The browser-side script replaces it only when the remote JSON has an `updated` timestamp at least as new as the fallback timestamp.

## Local Development

Install the Ruby/Jekyll dependencies, then run the site locally. Use a Ruby environment with working native-extension headers if macOS system Ruby fails to build gems.

```bash
bundle install
bundle exec jekyll serve
```

Open [http://127.0.0.1:4000](http://127.0.0.1:4000).

## Maintenance Notes

- Main page content lives in [_pages/about.md](./_pages/about.md).
- Sidebar navigation lives in [_data/navigation.yml](./_data/navigation.yml): `sections` scroll to a section of the home page, `pages` link to other pages.
- Styles live in [assets/css/main.css](./assets/css/main.css) (plain CSS; colors are custom properties at the top, with a `[data-theme="dark"]` variant).
- Day/night switching, sidebar section highlighting and the News ticker live in [assets/js/site.js](./assets/js/site.js).
- News items are the `<li>` entries inside the `news-ticker` block of [_pages/about.md](./_pages/about.md), newest first.
- The 小六壬 page is self-contained in [liuren](./liuren).
- Google Scholar fetching logic lives in [google_scholar_crawler/main.py](./google_scholar_crawler/main.py).
- Citation display logic lives in [_includes/fetch_google_scholar_stats.html](./_includes/fetch_google_scholar_stats.html).

## Acknowledgements

- The current layout is inspired by [Tingying He's homepage](https://tingying-he.github.io/).
- The site was originally based on [RayeRen/acad-homepage.github.io](https://github.com/RayeRen/acad-homepage.github.io), influenced by [mmistakes/minimal-mistakes](https://github.com/mmistakes/minimal-mistakes) and [academicpages/academicpages.github.io](https://github.com/academicpages/academicpages.github.io).
