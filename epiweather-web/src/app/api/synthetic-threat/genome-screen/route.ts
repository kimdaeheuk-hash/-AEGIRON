import { proxyAuthed } from '@/lib/server-api';

export async function POST(req: Request): Promise<Response> {
  return proxyAuthed('/api/synthetic-threat/genome-screen', req);
}
