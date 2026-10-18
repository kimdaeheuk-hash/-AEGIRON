// 홈페이지용 실가동 화면·공공 사진 후보를 받는다 (2026-10-18 캡틴 지시).
//
// ★ 왜 GitHub Actions 에서 도나 ★
// 개발 샌드박스는 조직 정책으로 외부(운영 사이트·공공 사진 저장소)에 못 나간다(프록시 403).
// 깃허브 러너는 나갈 수 있다. 여기서 받은 것은 **후보**다 — .github/media-capture/out/ 에
// 출처·라이선스와 함께 남기고, 사람이(또는 Claude 가) 눈으로 고른 것만
// epiweather-web/public/media/ 로 옮긴다.
//
// 정직성:
//   · 대시보드 캡처는 운영 사이트를 그대로 찍고, 찍은 시각을 manifest.json 에 남긴다. 지어낸 화면이 아니다.
//   · 사진은 퍼블릭 도메인·CC0·CC BY(-SA) 만 받고 저작자·출처·라이선스를 함께 적는다.
//     그 외 라이선스는 받지 않고 왜 건너뛰었는지 failures 에 남긴다.
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const OUT = path.resolve(process.argv[2] ?? 'out');
const SITE = process.env.SITE_URL ?? 'https://epiweather-web.vercel.app';
const API = process.env.API_URL ?? 'https://epiweather-api-production.up.railway.app';
const UA = 'AEGIRON-media-capture/1.0 (+https://github.com/kimdaeheuk-hash/-AEGIRON)';

const manifest = { captured_at: new Date().toISOString(), site: SITE, screens: [], api: [], photos: [], failures: [], network: [], console: [] };

async function save(rel, buf) {
  const file = path.join(OUT, rel);
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, buf);
  return rel;
}

// ── 1. 운영 API 스냅샷 (실제 값으로 그림을 그릴 때 쓴다) ─────────────────
// 2026-10-18 오후: 공개 예측 원장·경보 해부·홈 실시간 신호를 실데이터로 설계하려고 늘렸다.
for (const p of [
  '/api/status', '/api/dashboard', '/api/daily-brief?lang=ko', '/api/biodefense/readiness', '/api/risk-quantification',
  '/api/predictions', '/api/predictions/scorecard', '/api/lead-time-ledger?limit=50', '/api/alerts',
  '/api/risk-index', '/api/launch-readiness', '/api/extracted-signals?limit=30', '/api/unexplained-signals',
]) {
  try {
    const res = await fetch(API + p, { headers: { accept: 'application/json', 'user-agent': UA } });
    const body = await res.text();
    const rel = `api/${p.replace(/^\/api\//, '').replace(/[/?=&]/g, '_')}.json`;
    await save(rel, body);
    manifest.api.push({ path: p, status: res.status, file: rel });
  } catch (e) {
    manifest.failures.push({ what: `api ${p}`, error: String(e).slice(0, 300) });
  }
}

// ── 2. 운영 화면 캡처 ────────────────────────────────────────────────
const STAGES = ['합성위협 탐지', '발원지 추적', '민간 신호', '글로벌 유입', '국내 확산', '도착 예측', '방어 대응', 'AI 추론', '전략 비축', '실시간 대시보드'];
const browser = await chromium.launch();
try {
  for (const [tag, viewport] of [['desk', { width: 1440, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 2 });
    // ★ 진단(2026-10-18) ★ 첫 수집에서 9단계(실시간 대시보드)가 60초 넘게 "서버 연결 중"에
    // 머물렀다. 대시보드가 **어느 호스트**를 부르고 응답이 얼마나 걸리는지 남긴다.
    if (tag === 'desk') {
      const started = new Map();
      page.on('request', (r) => { if (/\/api\//.test(r.url())) started.set(r, Date.now()); });
      page.on('requestfinished', async (r) => {
        if (!started.has(r)) return;
        const res = await r.response().catch(() => null);
        manifest.network.push({ url: r.url(), method: r.method(), status: res?.status() ?? null, ms: Date.now() - started.get(r) });
      });
      page.on('requestfailed', (r) => {
        if (!started.has(r)) return;
        manifest.network.push({ url: r.url(), method: r.method(), failed: r.failure()?.errorText ?? 'failed', ms: Date.now() - started.get(r) });
      });
      page.on('console', (m) => { if (m.type() === 'error') manifest.console.push(m.text().slice(0, 300)); });
    }
    try {
      await page.goto(`${SITE}/dashboard`, { waitUntil: 'networkidle', timeout: 90_000 });
      await page.waitForTimeout(5000);
      for (const [i, name] of STAGES.entries()) {
        if (tag === 'mobile' && ![3, 5, 6, 8, 9].includes(i)) continue;
        try {
          await page.locator('button', { hasText: name }).first().click({ timeout: 10_000 });
          await page.waitForLoadState('networkidle', { timeout: 60_000 }).catch(() => {});
          await page.waitForTimeout(6000);
          if (i === 9) {
            // 실시간 단계는 로딩 문구가 사라질 때까지 최대 90초 더 기다린다. 끝내 안 사라지면 그 사실을 남긴다.
            const loaded = await page.getByText('서버 연결 중').waitFor({ state: 'detached', timeout: 90_000 }).then(() => true, () => false);
            if (!loaded) manifest.failures.push({ what: `stage 9 ${tag}`, error: 'still loading after 90s+ (서버 연결 중)' });
          }
          const rel = `screens/${tag}-stage${i}.jpg`;
          await save(rel, await page.screenshot({ fullPage: false, type: 'jpeg', quality: 80 }));
          manifest.screens.push({ stage: i, name, viewport: tag, file: rel, url: `${SITE}/dashboard`, at: new Date().toISOString() });
        } catch (e) {
          manifest.failures.push({ what: `stage ${i} ${tag}`, error: String(e).slice(0, 300) });
        }
      }
    } finally {
      await page.close();
    }
  }
  // 공개 사이트 홈(세 언어) — 비교·공유 미리보기용
  for (const loc of ['ko', 'en', 'fr']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
    try {
      await page.goto(`${SITE}/${loc}`, { waitUntil: 'networkidle', timeout: 90_000 });
      await save(`screens/site-home-${loc}.jpg`, await page.screenshot({ type: 'jpeg', quality: 80 }));
    } catch (e) {
      manifest.failures.push({ what: `home ${loc}`, error: String(e).slice(0, 300) });
    } finally {
      await page.close();
    }
  }
} finally {
  await browser.close();
}

// ── 3. 공공 사진 후보 (퍼블릭 도메인 · CC0 · CC BY(-SA) 만) ───────────
// 첫 수집(2026-10-18)에서 후보 40장이 100MB 를 넘었다. 다시 받을 때만 CAPTURE_PHOTOS=1 로 켠다.
// 2차(2026-10-18 오후): 네오 오션스 site/fetch_assets.py 방식을 따른다 — 주제(슬롯)마다
// 검색어 두세 개로 후보를 모으고, JPEG · 원본 폭 1400px 이상 · 허용 라이선스만 슬롯당 take 장 받는다.
// 파일 이름이 슬롯 이름이라(lab-1.jpg) 고를 때 무엇인지 바로 보인다.
const WANT_PHOTOS = process.env.CAPTURE_PHOTOS === '1';
const SLOTS = !WANT_PHOTOS ? {} : {
  lab: { take: 3, queries: ['biosafety level 4 laboratory', 'CDC laboratory scientist biosafety cabinet', 'virology laboratory researcher'] },
  sequencing: { take: 3, queries: ['DNA sequencing laboratory sequencer', 'genome sequencing machine laboratory', 'pathogen genomics laboratory'] },
  virus: { take: 3, queries: ['SARS-CoV-2 electron micrograph NIAID colorized', 'influenza virus electron micrograph CDC', 'Mpox virus electron micrograph NIAID'] },
  field: { take: 3, queries: ['Ebola outbreak response health workers', 'epidemiologist field investigation outbreak', 'disease surveillance health workers Africa'] },
  airport: { take: 2, queries: ['airport terminal passengers departure hall', 'Incheon International Airport terminal'] },
  flights: { take: 2, queries: ['world airline routes map', 'air traffic world map flight paths'] },
  earth: { take: 3, queries: ['Earth at night Black Marble NASA', 'Blue Marble Earth NASA', 'Earth from International Space Station'] },
  satellite: { take: 2, queries: ['Earth observation satellite in orbit', 'Sentinel-2 satellite ESA'] },
  wastewater: { take: 2, queries: ['wastewater treatment plant aerial', 'wastewater sampling'] },
  poultry: { take: 2, queries: ['poultry farm chickens barn', 'avian influenza poultry surveillance'] },
  mosquito: { take: 2, queries: ['Aedes aegypti mosquito CDC', 'Anopheles mosquito CDC'] },
  forest: { take: 2, queries: ['Amazon deforestation aerial', 'tropical rainforest aerial'] },
  arctic: { take: 2, queries: ['Arctic permafrost thaw', 'glacier aerial'] },
  datacenter: { take: 2, queries: ['data center server room', 'supercomputer server racks'] },
  operations: { take: 2, queries: ['emergency operations center screens', 'CDC Emergency Operations Center'] },
  hospital: { take: 2, queries: ['hospital intensive care unit', 'hospital corridor medical staff'] },
  vaccine: { take: 2, queries: ['vaccine vials production line', 'vaccine vials'] },
  port: { take: 2, queries: ['container port aerial', 'container terminal cranes'] },
};
const ALLOWED = /^(public domain|pd|cc0|cc[- ]?by([- ]?sa)?[- ]?\d)/i;
const strip = (s) => String(s ?? '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
for (const [slot, spec] of Object.entries(SLOTS)) {
  const found = [];
  const seen = new Set();
  for (const q of spec.queries) {
    try {
      const url = new URL('https://commons.wikimedia.org/w/api.php');
      Object.entries({
        action: 'query', format: 'json', generator: 'search', gsrsearch: `filetype:bitmap ${q}`,
        gsrnamespace: '6', gsrlimit: '12', prop: 'imageinfo', iiprop: 'url|extmetadata|size|mime', iiurlwidth: '1600',
      }).forEach(([k, v]) => url.searchParams.set(k, v));
      const data = await (await fetch(url, { headers: { 'user-agent': UA } })).json();
      const pages = Object.values(data?.query?.pages ?? {}).sort((x, y) => (x.index ?? 0) - (y.index ?? 0));
      for (const pg of pages) {
        const ii = pg.imageinfo?.[0];
        if (!ii || seen.has(pg.title)) continue;
        const md = ii.extmetadata ?? {};
        const license = strip(md.LicenseShortName?.value);
        if (ii.mime !== 'image/jpeg' || (ii.width ?? 0) < 1400 || !ALLOWED.test(license)) continue;
        seen.add(pg.title);
        found.push({ pg, ii, md, license, q });
      }
    } catch (e) {
      manifest.failures.push({ what: `query ${q}`, error: String(e).slice(0, 300) });
    }
    await new Promise((r) => setTimeout(r, 800));
  }
  for (const [i, c] of found.slice(0, spec.take).entries()) {
    try {
      const res = await fetch(c.ii.thumburl ?? c.ii.url, { headers: { 'user-agent': UA } });
      if (!res.ok) { manifest.failures.push({ what: c.pg.title, error: `HTTP ${res.status}` }); continue; }
      const rel = `photos/${slot}-${i + 1}.jpg`;
      await save(rel, Buffer.from(await res.arrayBuffer()));
      manifest.photos.push({
        file: rel, slot, query: c.q, title: c.pg.title, page: c.ii.descriptionurl,
        license: c.license, license_url: strip(c.md.LicenseUrl?.value),
        artist: strip(c.md.Artist?.value).slice(0, 160), credit: strip(c.md.Credit?.value).slice(0, 200),
        description: strip(c.md.ImageDescription?.value).slice(0, 400),
        width: c.ii.thumbwidth ?? c.ii.width, height: c.ii.thumbheight ?? c.ii.height,
      });
    } catch (e) {
      manifest.failures.push({ what: c.pg.title, error: String(e).slice(0, 300) });
    }
  }
}

// ── 4. 소개 영상 메타데이터 — 유튜브가 영상 위에 띄우는 제목·채널명이 무엇인지 확인 ──
// 캡틴 지시(2026-10-18): "유튜브 동영상 화면에 내 이름 빼". 임베드 상단 막대에 채널명이 뜨므로
// 실제로 무엇이 뜨는지(oEmbed 의 title · author_name)와 썸네일을 받아 둔다.
try {
  const vid = '2Uzl-5JgLjs';
  const oe = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${vid}&format=json`, { headers: { 'user-agent': UA } });
  await save('api/youtube_oembed.json', JSON.stringify({ status: oe.status, body: oe.ok ? await oe.json() : await oe.text() }, null, 2));
  for (const name of ['maxresdefault', 'hqdefault']) {
    const th = await fetch(`https://i.ytimg.com/vi/${vid}/${name}.jpg`, { headers: { 'user-agent': UA } });
    if (th.ok) { await save(`api/youtube_${name}.jpg`, Buffer.from(await th.arrayBuffer())); break; }
  }
} catch (e) {
  manifest.failures.push({ what: 'youtube oembed', error: String(e).slice(0, 300) });
}

await save('manifest.json', JSON.stringify(manifest, null, 2));
console.log(`screens ${manifest.screens.length} · api ${manifest.api.length} · photos ${manifest.photos.length} · failures ${manifest.failures.length}`);
