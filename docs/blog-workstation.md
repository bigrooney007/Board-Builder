# Blog generator in the original admin

Open `/admin?tab=blog`, or choose **Blog Post Generator** in `/admin`.

| Day | Topic | Call to action |
| --- | --- | --- |
| Monday | Board Recruitment | `/recruit` |
| Tuesday | Board Fundraising | `/board-fundraising-game` |
| Wednesday | Strategic Planning | `/strategic-planning` |
| Thursday | Board Recommitment | `/board-recommitment` |
| Friday | Joining Nonprofit Boards | `/join-a-board` |

Choose an article angle and its planned date, then **Generate Blog Post + Graphic**.
Each angle has a specific pain point, limiting belief and desired outcome. The fifth
topic speaks to prospective board members and invites them to the Board Applicant
Network. The four service topics speak to nonprofit leaders.

The draft retains its writing brief. Preview the article and cover, edit their wording,
and use **Publish Article**. Every published article has its own image, description,
shareable URL and correct service button. Published URLs stay stable after edits.
The date organizes the editorial calendar; Publish Article makes it public immediately.

The original posts remain in the same `blog_posts` collection. Older articles keep their
content and URLs. Their recruitment, fundraising and recommitment buttons resolve to
the current landing routes. Articles without a cover receive a cover using their own title.

## Automatic weekday drafts

The admin's **Automatic weekday drafts** panel controls whether the backend prepares
the day's article at the saved time and timezone. It only runs Monday through Friday.
All automatic posts wait for review. The existing environment switch is honored until
an admin saves these settings. A topic and date can have only one post, including across
multiple workers; repeated Generate clicks open that post instead of paying for another.

Generation runs in a background task, with a four-minute limit and at most one corrective
model attempt. A failed or interrupted draft can be regenerated in the admin after five
minutes. This uses the existing Anthropic/Emergent AI configuration. Share text is generated
only when its own button is clicked. No article is emailed to subscribers by this feature.

## Graphics and previews

Each draft includes a short headline and supporting line specific to its argument.
The local Pillow renderer turns them into a 1200x630 PNG in the current brand palette.
The same graphic appears above the article and in Open Graph and Twitter metadata.
The bundled font and license make rendering reproducible without an image service.
The public image endpoint serves only published articles. Draft images require admin
authentication. Editing graphic wording changes the image URL's version automatically.

Initial HTML includes article metadata, BlogPosting structured data and the full readable
article, for all visitors and crawlers. `/api/blog/sitemap.xml` updates from published
posts, and robots.txt advertises it. A new article needs no frontend rebuild.

## Deploy into the existing Emergent project

Sync the approved GitHub revision, preserving the production database, environment
and domain. No database migration or new service account is required.

Run the normal backend compilation and frontend build. The current `yarn start`
configuration already installs the dynamic blog HTML handler. It uses
`BLOG_API_ORIGIN`, then `REACT_APP_BACKEND_URL`, then `http://127.0.0.1:8001`
to read public content. Set BLOG_API_ORIGIN only if the server needs a different
internal backend origin. This is a server-only URL and must not include `/api`.

If the host serves the compiled build instead of using `yarn start`, run `yarn serve`
after building. Keep the existing reverse-proxy routing for `/api` to FastAPI and
forward frontend requests to this server. A static-only SPA fallback cannot supply
fresh metadata for posts published after a build. The production frontend server
supports dynamic blog HTML and the seven existing prerendered landing routes.

After deployment and publishing a draft:

```sh
cd frontend
node scripts/verify-blog-seo.cjs https://nonprofitboardbuilder.com
node scripts/verify-landing-seo.cjs https://nonprofitboardbuilder.com
```

The blog checker reads HTTP responses without executing client JavaScript and checks
one published article in each available category. It checks image dimensions and
the category's call to action. Sharing services may need to refresh an older cached
preview after a published article is edited.

Offline checks: `backend/tests/test_blog_workstation.py`,
`frontend/src/admin/BlogAdminSection.test.jsx` and `frontend/src/seo/BlogMetadata.test.jsx`.
Tests mock the model and delivery boundaries and do not alter live content.
