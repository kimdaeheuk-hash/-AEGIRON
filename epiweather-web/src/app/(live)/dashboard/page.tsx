import Console from '@/components/Console';
import { getDictionary, type Locale } from '@/i18n';
import { getBaikal } from '@/lib/baikal';
import { getPolarTrend } from '@/lib/polarTrend';
import { getVariantGrowth, getVariantLedger } from '@/lib/variantLedger';

type Props = { searchParams: Promise<{ lang?: string | string[] }> };

/** ?lang=en|fr 이면 그 언어로. 없으면 한국어. 변이 원장·극지 추이는 15분, BAIKAL 은 5분 캐시. */
export default async function DashboardPage({ searchParams }: Props) {
  const raw = (await searchParams).lang;
  const v = Array.isArray(raw) ? raw[0] : raw;
  const locale: Locale = v === 'en' || v === 'fr' ? v : 'ko';
  const [polar, variants, growth, baikal] = await Promise.all([
    getPolarTrend(locale),
    getVariantLedger(locale, getDictionary(locale).variant.transitions),
    getVariantGrowth(locale),
    getBaikal(locale),
  ]);
  return <Console locale={locale} polar={polar} variants={variants} growth={growth} baikal={baikal} />;
}
