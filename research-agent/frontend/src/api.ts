export type Source = { id: number; title: string; url: string };
export type ResearchResult = {
  topic: string;
  queries: string[];
  report: string;
  bibliography: Source[];
};

export async function research(topic: string): Promise<ResearchResult> {
  const res = await fetch("/api/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Research failed. Try again.");
  }
  return res.json();
}
