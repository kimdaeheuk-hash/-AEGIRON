import { proxyAuthed } from '@/lib/server-api';

export async function DELETE(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;
  if (!/^\d+$/.test(id)) {
    return Response.json({ error: 'invalid id' }, { status: 422 });
  }
  return proxyAuthed(`/api/biodefense/stockpile/${id}`, req);
}
