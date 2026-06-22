import { create } from 'zustand';
import {
  PRESETS, ThreatKey, PresetKey, Levers,
  genPatientZero, computeGlobal, computeDomestic, simulate, currentRt,
  PatientZeroResult, GlobalResult, DomesticResult, SimResult,
} from './algorithms';

interface AppState {
  // 시나리오 파라미터
  origin: string;
  threat: ThreatKey;
  lev: Levers;
  stage: number;
  week: number;
  reg: string;
  zsel: PatientZeroResult['cells'][0] | null;
  civicOn: Record<string, boolean>;

  // 계산 결과
  pz: PatientZeroResult | null;
  glob: GlobalResult | null;
  dom: DomesticResult | null;
  def: SimResult | null;
  def0: SimResult | null;

  // 파생 값
  savedLives: number;
  rt: number;

  // 액션
  setOrigin: (v: string) => void;
  setThreat: (v: ThreatKey) => void;
  setPreset: (v: PresetKey) => void;
  setLev: (k: string, v: number) => void;
  setStage: (n: number) => void;
  setWeek: (n: number) => void;
  setReg: (id: string) => void;
  setZSel: (cell: PatientZeroResult['cells'][0]) => void;
  toggleCivic: (id: string) => void;
  recompute: (defOnly?: boolean) => void;
}

const initLev = { ...PRESETS.strong };

function doRecompute(state: AppState, defOnly: boolean): Partial<AppState> {
  const { origin, threat, lev } = state;
  let pz = state.pz;
  let glob = state.glob;
  let dom = state.dom;

  if (!defOnly) {
    pz = genPatientZero(42, origin);
    glob = computeGlobal(origin, threat);
    dom = computeDomestic(threat);
  }

  const def = simulate(lev, threat);
  const def0 = simulate(PRESETS.none as Levers, threat);
  const savedLives = Math.max(0, Math.round((def0?.deaths ?? 0) - (def?.deaths ?? 0)));
  const rt = currentRt(lev, threat);

  const zsel = defOnly ? state.zsel : (pz?.cands[0] ?? null);

  return { pz, glob, dom, def, def0, savedLives, rt, zsel };
}

export const useStore = create<AppState>((set, get) => ({
  origin: 'WUH',
  threat: 'novel',
  lev: initLev,
  stage: 0,
  week: 0,
  reg: 'IC',
  zsel: null,
  civicOn: { citi: true, sewer: true, otc: true, kit: true, lab: true },
  pz: null, glob: null, dom: null, def: null, def0: null,
  savedLives: 0, rt: 0,

  setOrigin: (v) => set((s) => ({ origin: v, ...doRecompute({ ...s, origin: v }, false) })),
  setThreat: (v) => set((s) => ({ threat: v, ...doRecompute({ ...s, threat: v }, false) })),
  setPreset: (v) => set((s) => {
    const lev = { ...PRESETS[v] };
    return { lev, ...doRecompute({ ...s, lev }, true) };
  }),
  setLev: (k, v) => set((s) => {
    const lev = { ...s.lev, [k]: v };
    return { lev, ...doRecompute({ ...s, lev }, true) };
  }),
  setStage: (n) => set({ stage: n }),
  setWeek: (n) => set({ week: n }),
  setReg: (id) => set({ reg: id }),
  setZSel: (cell) => set({ zsel: cell }),
  toggleCivic: (id) => set((s) => ({ civicOn: { ...s.civicOn, [id]: !s.civicOn[id] } })),
  recompute: (defOnly = false) => set((s) => doRecompute(s, defOnly)),
}));
