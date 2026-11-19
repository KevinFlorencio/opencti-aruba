import { getCollection } from 'astro:content';
import { isInYear } from './current-year.mjs';

export async function currentBriefings() {
  return (await getCollection('blog', (post) => isInYear(post.data.published)))
    .sort((a, b) => b.data.published.valueOf() - a.data.published.valueOf());
}