import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { currentBriefings } from '../data/briefings';

export async function GET(context: APIContext) {
  const base = import.meta.env.BASE_URL.replace(/\/?$/, '/');
  const posts = await currentBriefings();

  return rss({
    title: 'Aruba Threat Radar — Briefings',
    description:
      'Threat intelligence and incident analysis for Aruba, Bonaire and Curaçao.',
    site: context.site ?? 'https://radar.arubati.org',
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: post.data.published,
      link: `${base}blog/${post.id}/`,
      categories: post.data.tags,
    })),
    customData: '<language>en</language>',
  });
}
