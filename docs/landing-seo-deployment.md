# Landing-page SEO and link previews

The homepage and these six landing routes have separate search titles, descriptions,
canonical URLs, Open Graph metadata, large-image social cards and JSON-LD:

- `/recruit`
- `/board-fundraising-game`
- `/strategic-planning`
- `/board-recommitment`
- `/join-a-board`
- `/organize-board-fundraising-game`

The source is `frontend/src/content/landingSeo.json`. The committed 1200 by 630 PNG
cards are in `frontend/public/social/`. Updating those assets requires no image service
or paid generation. To redraw them locally, use `frontend/scripts/generate-share-images.py`
with Pillow and DejaVu Sans installed. Give a changed image a new filename in the manifest
when you want shared-link services to fetch a new asset.

## Deployment

Sync the approved GitHub `main` revision into the existing Emergent project. Preserve
the existing production database, environment variables and domain configuration.
No database migration is required by this SEO update.

Run the normal frontend build command, `yarn build` or `npm run build`. It now also
creates route-specific HTML at `build/<route>/index.html`, plus `robots.txt` and
`sitemap.xml`. Every generated page keeps the original application bundles and loads
the existing React application. React navigation updates the same metadata.

For static hosting, serve the generated landing HTML files before the general SPA
fallback. With Nginx, the usual `try_files $uri $uri/ /index.html` preserves these
files. Do not rewrite every landing request directly to the root `index.html`.
For Emergent environments running `yarn start`, the CRACO middleware serves the same
metadata in the initial HTML, including when the URL has a trailing slash or campaign
query parameters. There is no user-agent-specific rendering.

## Verification

From `frontend/`, run:

```sh
node scripts/verify-landing-seo.cjs
node scripts/verify-landing-seo.cjs https://nonprofitboardbuilder.com
```

The first command checks the built files. The second checks the deployed HTTP
responses and images without executing browser JavaScript. Run the second command
after deployment; a pre-deployment run still sees the previous release.

The checker verifies every page's unique initial title, description, canonical URL,
structured data, readable content and image dimensions, plus the sitemap and robots
file. Public landing pages are allowed under the wildcard crawler rules, including
Googlebot and OAI-SearchBot. Private application paths remain excluded from crawling;
authentication continues to provide access control.

After deployment, submit `/sitemap.xml` in the site's Google Search Console property
if it has not already been submitted. Existing social previews may retain cached
metadata until the sharing service refreshes its copy. A service's link-inspection
tool can request a fresh scrape after deployment. This code change does not submit
the sitemap or initiate search-engine indexing.

Metadata and preview cards describe the offers without prices or changing refund
terms. When an offer's positioning changes, update its manifest entry alongside the
landing page so the public description remains accurate.
