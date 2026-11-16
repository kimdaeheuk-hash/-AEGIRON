/**
 * 나라 이름 — 화면 언어로 (2026-11-16, 캡틴 '번역들이 꼬인 거 같은데').
 *
 * 서버·클라이언트 양쪽에서 쓴다(대시보드는 클라이언트). 운영 API 를 부르는 코드는 두지 않는다.
 */
import type { Locale } from '@/i18n';
import { EN_ISO3, KO_ISO3 } from './isoGeo';
import { hasHangul, placeName } from './observationNames';

/** ISO3 → 한국어 이름(name_i18n 표를 거꾸로, 짧은 이름 우선). en/fr 은 그 한국어 이름을 지명 사전으로 옮긴다. */
const KO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(KO_ISO3)
    .sort((a, b) => a[0].length - b[0].length)
    .reverse()
    .map(([ko, iso]) => [iso, ko]),
);

/** ISO3 → ISO2 (isoGeo.ISO3_NUMERIC 의 249개, pycountry 로 생성). Intl.DisplayNames 는 ISO2 만 받는다. */
const ISO2: Record<string, string> = Object.fromEntries(
  'ABWAW AFGAF AGOAO AIAAI ALAAX ALBAL ANDAD AREAE ARGAR ARMAM ASMAS ATAAQ ATFTF ATGAG AUSAU AUTAT AZEAZ BDIBI BELBE BENBJ BESBQ BFABF BGDBD BGRBG BHRBH BHSBS BIHBA BLMBL BLRBY BLZBZ BMUBM BOLBO BRABR BRBBB BRNBN BTNBT BVTBV BWABW CAFCF CANCA CCKCC CHECH CHLCL CHNCN CIVCI CMRCM CODCD COGCG COKCK COLCO COMKM CPVCV CRICR CUBCU CUWCW CXRCX CYMKY CYPCY CZECZ DEUDE DJIDJ DMADM DNKDK DOMDO DZADZ ECUEC EGYEG ERIER ESHEH ESPES ESTEE ETHET FINFI FJIFJ FLKFK FRAFR FROFO FSMFM GABGA GBRGB GEOGE GGYGG GHAGH GIBGI GINGN GLPGP GMBGM GNBGW GNQGQ GRCGR GRDGD GRLGL GTMGT GUFGF GUMGU GUYGY HKGHK HMDHM HNDHN HRVHR HTIHT HUNHU IDNID IMNIM INDIN IOTIO IRLIE IRNIR IRQIQ ISLIS ISRIL ITAIT JAMJM JEYJE JORJO JPNJP KAZKZ KENKE KGZKG KHMKH KIRKI KNAKN KORKR KWTKW LAOLA LBNLB LBRLR LBYLY LCALC LIELI LKALK LSOLS LTULT LUXLU LVALV MACMO MAFMF MARMA MCOMC MDAMD MDGMG MDVMV MEXMX MHLMH MKDMK MLIML MLTMT MMRMM MNEME MNGMN MNPMP MOZMZ MRTMR MSRMS MTQMQ MUSMU MWIMW MYSMY MYTYT NAMNA NCLNC NERNE NFKNF NGANG NICNI NIUNU NLDNL NORNO NPLNP NRUNR NZLNZ OMNOM PAKPK PANPA PCNPN PERPE PHLPH PLWPW PNGPG POLPL PRIPR PRKKP PRTPT PRYPY PSEPS PYFPF QATQA REURE ROURO RUSRU RWARW SAUSA SDNSD SENSN SGPSG SGSGS SHNSH SJMSJ SLBSB SLESL SLVSV SMRSM SOMSO SPMPM SRBRS SSDSS STPST SURSR SVKSK SVNSI SWESE SWZSZ SXMSX SYCSC SYRSY TCATC TCDTD TGOTG THATH TJKTJ TKLTK TKMTM TLSTL TONTO TTOTT TUNTN TURTR TUVTV TWNTW TZATZ UGAUG UKRUA UMIUM URYUY USAUS UZBUZ VATVA VCTVC VENVE VGBVG VIRVI VNMVN VUTVU WLFWF WSMWS YEMYE ZAFZA ZMBZM ZWEZW'
    .split(' ')
    .map((p) => [p.slice(0, 3), p.slice(3)]),
);

const DISPLAY = new Map<Locale, Intl.DisplayNames | null>();
function displayNames(locale: Locale): Intl.DisplayNames | null {
  if (!DISPLAY.has(locale)) {
    try {
      DISPLAY.set(locale, new Intl.DisplayNames([locale], { type: 'region' }));
    } catch {
      DISPLAY.set(locale, null); // Intl.DisplayNames 미지원 — 부르는 쪽이 받은 이름을 쓴다
    }
  }
  return DISPLAY.get(locale) ?? null;
}

/**
 * 나라 표시 이름 — 화면 언어로. 우리 사전(한국어 표 + 지명 사전)이 먼저이고, 없으면 브라우저·런타임
 * 내장 Intl.DisplayNames. 둘 다 없으면 null(부르는 쪽이 받은 이름을 쓴다).
 */
export function countryLabel(iso3: string | null | undefined, locale: Locale): string | null {
  if (!iso3) return null;
  const code = iso3.toUpperCase();
  const ko = KO_NAME[code];
  if (ko) {
    const out = locale === 'ko' ? ko : placeName(ko, locale);
    if (out && (locale === 'ko' || !hasHangul(out))) return out;
  }
  const iso2 = ISO2[code];
  if (!iso2) return null;
  const name = displayNames(locale)?.of(iso2);
  return name && name !== iso2 ? name : null;
}

/** 영문 이름 비교 키 — 글자 외(’ ' - , 등)는 공백으로. 'côte d’ivoire' 와 "côte d'ivoire" 가 같은 키가 된다. */
const normEn = (t: string) =>
  t
    .toLowerCase()
    .replace(/[^a-z\u00c0-\u024f]+/g, ' ')
    .trim();
const EN_NORM: Record<string, string> = Object.fromEntries(Object.entries(EN_ISO3).map(([k, iso]) => [normEn(k), iso]));
const EN_KEYS = Object.keys(EN_NORM).sort((a, b) => b.length - a.length);

/** 영문 문장 안의 나라 하나(가장 긴 이름 우선 — 'democratic republic of the congo' 가 'congo' 보다 먼저). 못 찾으면 null. */
export function isoInEnglish(text: string | null | undefined): string | null {
  if (!text) return null;
  const low = ` ${normEn(text)} `;
  for (const k of EN_KEYS) {
    if (low.includes(` ${k} `)) return EN_NORM[k];
  }
  return null;
}

/** 영문 문장 안의 나라 전부(나온 순서, 겹치는 짧은 이름은 건너뜀). 'Burkina Faso, Côte d’Ivoire, and Ghana' → 3개. */
export function isosInEnglish(text: string | null | undefined): string[] {
  if (!text) return [];
  let low = ` ${normEn(text)} `;
  const found: { iso: string; at: number }[] = [];
  for (const k of EN_KEYS) {
    const at = low.indexOf(` ${k} `);
    if (at < 0) continue;
    if (!found.some((f) => f.iso === EN_NORM[k])) found.push({ iso: EN_NORM[k], at });
    // 같은 자리를 짧은 이름이 다시 잡지 않게 지운다('democratic republic of the congo' 뒤의 'congo')
    low = low.slice(0, at) + ' '.repeat(k.length + 1) + low.slice(at + k.length + 1);
  }
  return found.sort((a, b) => a.at - b.at).map((f) => f.iso);
}
