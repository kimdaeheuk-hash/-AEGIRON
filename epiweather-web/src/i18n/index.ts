import type { Dictionary } from './types';
import { ko } from './dict/ko';
import { en } from './dict/en';
import { fr } from './dict/fr';
import { type Locale, defaultLocale, isLocale } from './config';

/**
 * 사전 조회. 정적 임포트를 쓰는 이유: 번역이 빠지면 **빌드 때 타입 오류**로
 * 잡힌다. 동적 import로 늦게 불러오면 그 검사가 사라져 빈칸이 배포된다.
 */
const dictionaries: Record<Locale, Dictionary> = { ko, en, fr };

export function getDictionary(locale: string): Dictionary {
  return dictionaries[isLocale(locale) ? locale : defaultLocale];
}

export * from './config';
export type { Dictionary } from './types';
