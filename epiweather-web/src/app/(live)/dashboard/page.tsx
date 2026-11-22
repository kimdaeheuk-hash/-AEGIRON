import Console from '@/components/Console';
import type { Locale } from '@/i18n';
import { getPolarTrend } from '@/lib/polarTrend';

type Props = { searchParams: Promise<{ lang?: string | string[] }> };

/** ?lang=en|fr 이면 그 언어로. 없으면 한국어. 극지 추이는 lib/polarTrend 의 15분 캐시를 쓴다. */
export default async function DashboardPage({ searchParams }: Props) {
  const raw = (await searchParams).lang;
  const v = Array.isArray(raw) ? raw[0] : raw;
  const locale: Locale = v === 'en' || v === 'fr' ? v : 'ko';
  return <Console locale={locale} polar={await getPolarTrend(locale)} />;
}
