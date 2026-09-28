"""Offline blog workflow checks. No production database, paid models or mail delivery."""
import copy
from datetime import datetime, timedelta
from io import BytesIO
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException
from PIL import Image
from pymongo.errors import DuplicateKeyError

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import blog_service as service
from blog_content import BLOG_CATEGORIES
from blog_media import cover_png, present_post


def matches(row, query):
    for key, expected in query.items():
        actual = row.get(key)
        if isinstance(expected, dict):
            if '$ne' in expected and actual == expected['$ne']: return False
            if '$in' in expected and actual not in expected['$in']: return False
        elif actual != expected: return False
    return True


class Cursor:
    def __init__(self, rows, projection=None):
        self.rows = copy.deepcopy(rows)
        self.projection = projection or {}
    def sort(self, key, order):
        self.rows.sort(key=lambda row: str(row.get(key, '')), reverse=order < 0)
        return self
    def skip(self, count):
        self.rows = self.rows[count:]
        return self
    async def to_list(self, count):
        rows = self.rows[:count]
        included = {key for key, value in self.projection.items() if value == 1}
        if included: return [{k: v for k, v in row.items() if k in included} for row in rows]
        return [{k: v for k, v in row.items() if self.projection.get(k, 1)} for row in rows]


class Collection:
    def __init__(self, unique=False):
        self.rows = []
        self.unique = unique
    def find(self, query, projection=None):
        return Cursor([row for row in self.rows if matches(row, query)], projection)
    async def find_one(self, query, projection=None):
        rows = await self.find(query, projection).to_list(1)
        return rows[0] if rows else None
    async def count_documents(self, query):
        return sum(matches(row, query) for row in self.rows)
    async def insert_one(self, row):
        if self.unique and any(p['category_key'] == row['category_key'] and p['scheduled_date'] == row['scheduled_date'] for p in self.rows):
            raise DuplicateKeyError('existing topic and date')
        self.rows.append(copy.deepcopy(row))
    async def update_one(self, query, update, upsert=False):
        row = next((row for row in self.rows if matches(row, query)), None)
        if row is None and upsert:
            row = copy.deepcopy(query); self.rows.append(row)
        if row is None: return types.SimpleNamespace(matched_count=0, modified_count=0)
        previous = copy.deepcopy(row)
        row.update(copy.deepcopy(update.get('$set', {})))
        return types.SimpleNamespace(matched_count=1, modified_count=int(previous != row))


async def auth(request, db):
    if request.headers.get('x-test-admin') != 'yes': raise HTTPException(401, 'Admin required')


def article(**kwargs):
    key = kwargs['category_key']
    return {'title': 'A useful next step for ' + key.replace('_', ' '),
            'excerpt': 'Understand what keeps this reader stuck and how a clear next step can help them move toward the board contribution they want.',
            'body': ' '.join(['Useful connected article content for the selected reader.'] * 45),
            'graphic_headline': 'Build With the People Around Your Board',
            'graphic_subtitle': 'Give the next step a clear purpose.'}


fake_auth = types.ModuleType('auth_service'); fake_auth.authenticate_admin = auth
fake_marketing = types.ModuleType('marketing_service'); fake_marketing.run_weekly_nurture = AsyncMock()
with patch.dict(sys.modules, {'auth_service': fake_auth, 'marketing_service': fake_marketing}):
    spec = importlib.util.spec_from_file_location('blog_test_routes', BACKEND / 'marketing_routes.py')
    routes = importlib.util.module_from_spec(spec); spec.loader.exec_module(routes)


class BlogWorkstation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = types.SimpleNamespace(blog_posts=Collection(unique=True), marketing_settings=Collection())
        self.writer = AsyncMock(side_effect=article)
        self.writer_patch = patch.object(service, 'claude_blog', self.writer); self.writer_patch.start()
        self.env_patch = patch.dict(os.environ, {'BLOG_AUTOMATION_ENABLED': 'false', 'BLOG_TIMEZONE': 'America/New_York'}); self.env_patch.start()
        app = FastAPI(); app.include_router(routes.create_marketing_router(self.db))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'x-test-admin': 'yes'})
    async def asyncTearDown(self):
        await self.client.aclose(); self.writer_patch.stop(); self.env_patch.stop()
    async def generate(self, category='recruitment', day='2026-09-28'):
        response = await self.client.post('/api/blog/generate', json={'category': category, 'scheduled_date': day})
        self.assertEqual(response.status_code, 202, response.text)
        return await self.db.blog_posts.find_one({'blog_post_id': response.json()['post']['blog_post_id']})

    async def test_five_topics_days_destinations_and_briefs(self):
        response = await self.client.get('/api/admin/blog/topics')
        self.assertEqual(response.status_code, 200, response.text)
        schedule = response.json()['schedule']
        self.assertEqual([row['publish_day'] for row in schedule], ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        self.assertEqual([row['cta_url'] for row in schedule], ['/recruit', '/board-fundraising-game', '/strategic-planning', '/board-recommitment', '/join-a-board'])
        for item in schedule:
            self.assertGreaterEqual(len(item['topics']), 6)
            for angle in item['topics']:
                self.assertTrue(all(angle[key] for key in ['pain_point', 'limiting_belief', 'desired_outcome']))
        self.assertIn('prospective applicant', schedule[-1]['audience'])

    async def test_generate_all_categories_review_publish_and_public_images(self):
        for key, config in BLOG_CATEGORIES.items():
            post = await self.generate(key)
            self.assertEqual(post['publication_status'], 'Pending Review')
            self.assertEqual(post['content_brief']['audience'], config['audience'])
            self.assertEqual((await self.client.get('/api/blog/posts/' + post['slug'])).status_code, 404)
            self.assertEqual((await self.client.get('/api/blog/images/' + post['slug'] + '.png')).status_code, 404)
            preview = await self.client.get('/api/admin/blog/posts/' + post['blog_post_id'] + '/image')
            self.assertEqual(Image.open(BytesIO(preview.content)).size, (1200, 630))
            self.assertIn('no-store', preview.headers['cache-control'])
            approved = await self.client.post('/api/admin/blog/posts/' + post['blog_post_id'] + '/approve')
            self.assertEqual(approved.status_code, 200, approved.text)
            public = await self.client.get('/api/blog/posts/' + post['slug'])
            self.assertEqual(public.json()['cta_url'], config['cta_url'])
            self.assertNotIn('content_brief', public.json())
            self.assertNotIn('generation_token', public.json())
            image = await self.client.get('/api/blog/images/' + post['slug'] + '.png')
            self.assertEqual(image.headers['content-type'], 'image/png')
            self.assertEqual(Image.open(BytesIO(image.content)).size, (1200, 630))
            cached = await self.client.get('/api/blog/images/' + post['slug'] + '.png', headers={'if-none-match': image.headers['etag']})
            self.assertEqual(cached.status_code, 304)
        self.assertEqual(self.writer.await_count, 5)
        sitemap = await self.client.get('/api/blog/sitemap.xml')
        for post in self.db.blog_posts.rows: self.assertIn('/blog/' + post['slug'], sitemap.text)

    async def test_duplicate_click_reuses_draft_and_next_angle_advances(self):
        first = await self.generate()
        again = await self.client.post('/api/blog/generate', json={'category': 'recruitment', 'scheduled_date': '2026-09-28'})
        self.assertTrue(again.json()['reused'])
        self.assertEqual(self.writer.await_count, 1)
        upcoming = await service.next_topic_for(self.db, 'recruitment')
        self.assertNotEqual(first['topic_id'], upcoming['topic_id'])

    async def test_auth_validation_and_private_drafts(self):
        post = await self.generate()
        self.client.headers.clear()
        for path in ['/api/admin/blog/topics', '/api/admin/blog/posts', '/api/admin/blog/posts/' + post['blog_post_id'] + '/image']:
            self.assertEqual((await self.client.get(path)).status_code, 401)
        self.assertEqual((await self.client.post('/api/blog/generate', json={'category': 'recruitment'})).status_code, 401)
        self.assertEqual((await self.client.get('/api/blog/posts')).json()['posts'], [])
        self.assertNotIn(post['slug'], (await self.client.get('/api/blog/sitemap.xml')).text)
        self.client.headers['x-test-admin'] = 'yes'
        for payload in [{'category': 'weekly'}, {'category': 'recruitment', 'scheduled_date': 'bad-date'}]:
            self.assertEqual((await self.client.post('/api/blog/generate', json=payload)).status_code, 422)
        self.assertEqual((await self.client.post('/api/blog/generate', json={'category': 'recruitment', 'publish_now': True})).status_code, 400)
        self.assertEqual((await self.client.post('/api/blog/generate', json={'category': 'recruitment', 'topic_id': 'unknown'})).status_code, 400)

    async def test_edit_updates_cover_preserves_published_url_and_retries_stale_generation(self):
        post = await self.generate()
        await self.client.post('/api/admin/blog/posts/' + post['blog_post_id'] + '/approve')
        old_image = (await self.client.get('/api/blog/posts/' + post['slug'])).json()['image_url']
        edited = await self.client.patch('/api/admin/blog/posts/' + post['blog_post_id'], json={**{key: post[key] for key in ['title', 'excerpt', 'body', 'graphic_headline', 'graphic_subtitle']}, 'title': 'A sharper edited title', 'graphic_headline': 'A Sharper Graphic'})
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()['post']['slug'], post['slug'])
        self.assertNotEqual(edited.json()['post']['image_url'], old_image)
        self.assertEqual((await self.client.post('/api/admin/blog/posts/' + post['blog_post_id'] + '/regenerate')).status_code, 409)
        interrupted, _ = await service.reserve_blog_post(self.db, 'strategic_planning', '2026-09-30')
        self.assertIsNone(await service.claim_regeneration(self.db, interrupted))
        old = (service.now_tz() - timedelta(minutes=10)).isoformat()
        await self.db.blog_posts.update_one({'blog_post_id': interrupted['blog_post_id']}, {'$set': {'generation_started_at': old}})
        stale = await self.db.blog_posts.find_one({'blog_post_id': interrupted['blog_post_id']})
        retry = await service.claim_regeneration(self.db, stale)
        self.assertNotEqual(retry['generation_token'], interrupted['generation_token'])
        await service.generate_reserved_blog_post(self.db, interrupted)
        self.assertEqual((await self.db.blog_posts.find_one({'blog_post_id': interrupted['blog_post_id']}))['publication_status'], 'Generating')
        await service.generate_reserved_blog_post(self.db, retry)
        self.assertEqual((await self.db.blog_posts.find_one({'blog_post_id': interrupted['blog_post_id']}))['publication_status'], 'Pending Review')

    async def test_automatic_weekdays_prepare_one_draft_without_publishing(self):
        await service.run_blog_schedule(self.db)
        self.assertEqual(self.writer.await_count, 0)
        response = await self.client.put('/api/admin/blog/settings', json={'enabled': True, 'time': '08:00', 'timezone': 'Europe/London'})
        self.assertEqual(response.status_code, 200)
        for day, category in enumerate(BLOG_CATEGORIES, start=28):
            instant = datetime(2026, 9, day, 9, tzinfo=ZoneInfo('Europe/London')) if day <= 30 else datetime(2026, 10, day - 30, 9, tzinfo=ZoneInfo('Europe/London'))
            with patch.object(service, 'datetime') as clock:
                clock.now.return_value = instant
                await service.run_blog_schedule(self.db); await service.run_blog_schedule(self.db)
            self.assertTrue(any(p['category_key'] == category for p in self.db.blog_posts.rows))
        self.assertEqual(self.writer.await_count, 5)
        self.assertTrue(all(p['publication_status'] == 'Pending Review' for p in self.db.blog_posts.rows))
        with patch.object(service, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 4, 9, tzinfo=ZoneInfo('Europe/London'))
            await service.run_blog_schedule(self.db)
        self.assertEqual(self.writer.await_count, 5)
        self.assertEqual((await self.client.put('/api/admin/blog/settings', json={'enabled': True, 'time': '26:00', 'timezone': 'Invalid'})).status_code, 422)

    async def test_failed_generation_is_bounded_and_legacy_posts_keep_content(self):
        self.writer.side_effect = None; self.writer.return_value = {'body': 'incomplete'}
        post = await self.generate()
        self.assertEqual(post['publication_status'], 'Failed')
        self.assertEqual(self.writer.await_count, 2)
        legacy = {'blog_post_id': 'legacy', 'category_key': 'reactivation', 'category': 'Board Reactivation', 'title': 'The original article title', 'body': 'The original body', 'slug': 'legacy', 'publication_status': 'Published', 'cta_url': '/reactivate'}
        presented = present_post(legacy, public=True)
        self.assertEqual(presented['body'], legacy['body'])
        self.assertEqual(presented['cta_url'], '/board-recommitment')
        self.assertEqual(Image.open(BytesIO(cover_png(legacy))).size, (1200, 630))


if __name__ == '__main__': unittest.main()
