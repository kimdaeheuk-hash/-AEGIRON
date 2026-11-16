'use client';
/**
 * 라이브 대시보드(/dashboard) 언어 — 2026-11-16, 캡틴 "영어·프랑스어 번역"(⑪).
 *
 * 대시보드는 로케일 경로 밖의 화면 하나다(이미 공유된 /dashboard 링크를 깨지 않으려고). 그래서 언어는
 * 주소의 ?lang=en|fr 로 고른다(없으면 한국어). 서버(page.tsx)가 읽어 Command 에 넘긴다.
 */
import { createContext, useContext } from 'react';

export type DashLang = 'ko' | 'en' | 'fr';

export const DASH_LANGS: DashLang[] = ['ko', 'en', 'fr'];

export const DashLangContext = createContext<DashLang>('ko');

export function useDashLang(): DashLang {
  return useContext(DashLangContext);
}

export function numLocale(lang: DashLang): string {
  return lang === 'ko' ? 'ko-KR' : lang === 'fr' ? 'fr-FR' : 'en-US';
}

/** 한 줄 번역 — t('한국어', 'English', 'Français'). 단계 화면 안 문구에 쓴다. */
export type Tr = (ko: string, en: string, fr: string) => string;

export function useT(): Tr {
  const lang = useDashLang();
  return (ko, en, fr) => (lang === 'en' ? en : lang === 'fr' ? fr : ko);
}
