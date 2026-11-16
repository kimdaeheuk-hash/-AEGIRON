import Command from '@/components/Command';

type Props = { searchParams: Promise<{ lang?: string | string[] }> };

/** ?lang=en|fr 이면 대시보드 틀·실측 패널을 그 언어로(2026-11-16). 없으면 한국어. */
export default async function DashboardPage({ searchParams }: Props) {
  const raw = (await searchParams).lang;
  const v = Array.isArray(raw) ? raw[0] : raw;
  return <Command initialLang={v === 'en' || v === 'fr' ? v : 'ko'} />;
}
